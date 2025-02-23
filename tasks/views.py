import random
import time
import datetime
import logging

from decimal import Decimal, InvalidOperation

from django.db.models import Sum
from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .forms import RegistrationForm
from .models import (
    DepositRequest,
    WithdrawalRequest,
    Withdrawal,
    Transaction,
    UserProfile,
    Task,
    Plan,
)
from celery import shared_task
from django.utils import timezone
from tasks.models import UserProfile
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.utils.timezone import now
from datetime import timedelta
from .models import Income  # Ensure this model exists
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import models
from django.utils.timezone import now
from datetime import timedelta
from .models import Income



@shared_task
def reset_daily_counters():
    today = timezone.localtime(timezone.now()).date()
    profiles = UserProfile.objects.all()
    for profile in profiles:
        profile.mines_today = 0
        profile.ads_watched_today = 0
        profile.last_mine_date = today
        profile.last_ad_date = today
        profile.save()

# Configure logging
logger = logging.getLogger(__name__)

import logging
logger = logging.getLogger(__name__)

today = timezone.localtime(timezone.now()).date()
logger.info(f"Today is {today} and last_mine_date is {UserProfile.last_mine_date}")

# ------------------------
# Helper Functions
# ------------------------
def mask_phone_number(phone):
    """Mask phone number to show only first 3 and last 2 digits."""
    if phone and len(phone) >= 5:
        return phone[:3] + "****" + phone[-2:]
    return phone  

def mask_address(address):
    """Mask address to show only first 5 and last 3 characters."""
    if address and len(address) >= 8:
        return address[:5] + "****" + address[-3:]
    return address  

def get_random_withdrawal(request):
    """Return a random withdrawal with masked user info."""
    withdrawals = Withdrawal.objects.all()
    if withdrawals.exists():
        withdrawal = random.choice(withdrawals)
        withdrawal_method = withdrawal.withdrawal_method
        user_profile = getattr(withdrawal.user, "userprofile", None)
        if not user_profile:
            return JsonResponse({"error": "User profile not found for withdrawal."})
        
        masked_info = (
            mask_phone_number(user_profile.phone_number)
            if withdrawal_method.lower() in ["mpesa", "airtel_money"]
            else mask_address(user_profile.wallet_address)
        )
        
        message = (
            f"💸 {masked_info} just withdrew ${withdrawal.amount} "
            f"via {withdrawal_method.capitalize()}! 🚀"
        )
        return JsonResponse({
            "name": withdrawal.user.username,
            "amount": f"${withdrawal.amount}",
            "method": withdrawal_method.capitalize(),
            "masked_info": masked_info,
            "message": message,
        })
    return JsonResponse({"error": "No withdrawals yet."})

def simulate_delay(seconds=10):
    """
    Simulate a delay (e.g., for a demo).
    WARNING: Avoid blocking calls like time.sleep() in production.
    """
    time.sleep(seconds)

def send_otp(phone_number):
    """Simulate sending an OTP. Replace with an SMS API in production."""
    otp = random.randint(100000, 999999)
    logger.info(f"Sending OTP {otp} to {phone_number}")
    return otp

# ------------------------
# Authentication / Registration Views
# ------------------------
def register(request):
    """
    Registers a new user using their phone number.
    Saves the phone number and sends an OTP.
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data["phone_number"]
            user.save()
            # Update UserProfile (typically created via signals)
            user_profile = user.userprofile
            user_profile.phone_number = form.cleaned_data["phone_number"]
            user_profile.save()
            
            otp = send_otp(form.cleaned_data["phone_number"])
            request.session['otp'] = otp
            request.session['phone_number'] = form.cleaned_data["phone_number"]
            
            logger.info(f"User {user.username} registered; OTP sent.")
            return redirect('verify_otp')
    else:
        form = RegistrationForm()
    return render(request, 'tasks/register.html', {'form': form})

def login_view(request):
    """Handles user login."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"User {user.username} logged in.")
            return HttpResponseRedirect('/tasks/home/')
        else:
            logger.warning("Invalid login attempt.")
    else:
        form = AuthenticationForm()
    return render(request, 'tasks/login.html', {'form': form})

def verify_otp(request):
    """
    Verifies the OTP entered by the user.
    On success, logs in the user and redirects them.
    """
    if request.method == "POST":
        otp_entered = request.POST.get('otp')
        otp_sent = request.session.get('otp')
        if str(otp_entered) == str(otp_sent):
            phone_number = request.session.get('phone_number')
            user = User.objects.get(username=phone_number)
            login(request, user)
            # Clear OTP data from session
            request.session.pop('otp', None)
            request.session.pop('phone_number', None)
            return redirect('choose_plan')
        else:
            error = "Invalid OTP. Please try again."
            return render(request, 'verify_otp.html', {'error': error, 'otp_code': request.session.get('otp')})
    else:
        return render(request, 'verify_otp.html', {'otp_code': request.session.get('otp')})

# ------------------------
# Dashboard / Home Views
# ------------------------
def home(request):
    return render(request, 'tasks/home.html', {'user': request.user})

@login_required
def task_page(request):
    return render(request, 'tasks/task_page.html')

# ------------------------
# Game Logic / Task Views
# ------------------------
from django.utils import timezone

@api_view(['GET'])
def mine(request):
    user = request.user  # Get the logged-in user

    if not user.is_authenticated:
        return Response({'error': 'User not authenticated'}, status=401)

    try:
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        today = timezone.localtime(timezone.now()).date()
        last_mine_date = user_profile.last_mine_date

        logger.info(f"Today is {today} and last_mine_date is {last_mine_date}")

        if last_mine_date == today:
            return Response({'message': 'You have already mined today. Come back tomorrow!'}, status=400)

        # Update last_mine_date
        user_profile.last_mine_date = today
        user_profile.save()

        return Response({'message': 'Mining successful!'}, status=200)

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return Response({'error': 'Something went wrong!'}, status=500)

@login_required
def activate_ads(request):
    """
    Activates ads for the user by deducting a fee and resetting ad counters.
    """
    try:
        user_profile = request.user.userprofile
        if user_profile.balance < 200:
            return JsonResponse({'status': 'error', 'message': 'Insufficient balance to activate ads.'})
        
        user_profile.balance -= 200
        user_profile.ads_activated = True
        user_profile.ads_watched_today = 0
        user_profile.last_ad_date = datetime.date.today()
        user_profile.save()
        
        logger.info(f"[ADS] Ads activated; new balance: {user_profile.balance}")
        return JsonResponse({'status': 'success', 'balance': float(user_profile.balance), 'message': 'Ads activated.'})
    except Exception as e:
        logger.error(f"[ADS] Error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error activating ads: {str(e)}'})

@login_required
def watch_ad(request):
    try:
        user_profile = request.user.userprofile
        today = datetime.date.today()
        if user_profile.last_ad_date != today:
            user_profile.ads_watched_today = 0
            user_profile.last_ad_date = today
        
        if user_profile.plan and user_profile.ads_watched_today >= user_profile.plan.daily_ads:
            return JsonResponse({'status': 'error', 'message': 'Daily ad watch limit reached.'})
        
        simulate_delay(10)
        reward = user_profile.plan.reward_per_ad
        user_profile.balance += reward
        user_profile.ads_watched_today += 1
        user_profile.save()
        return JsonResponse({
            'status': 'success',
            'balance': float(user_profile.balance),
            'reward': reward,
            'ads_watched': user_profile.ads_watched_today
        })
    except Exception as e:
        logger.error(f"[WATCH_AD] Error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error during watching ad: {str(e)}'})

@login_required
def start_task(request):
    """
    Processes a task by marking it completed and crediting the user.
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        task = Task.objects.filter(user=user_profile, completed=False).first()
        if task:
            simulate_delay(3)
            task.completed = True
            task.save()
            if user_profile.plan:
                user_profile.balance += user_profile.plan.reward_per_mine
                user_profile.save()
                logger.info(f"[START_TASK] Balance updated to: {user_profile.balance}")
            return JsonResponse({'status': 'success', 'balance': float(user_profile.balance)})
        return JsonResponse({'status': 'no_tasks'})
    except Exception as e:
        logger.error(f"[START_TASK] Error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error during task execution: {str(e)}'})

@login_required
def perform_task(request):
    """Renders the task performance page with user details."""
    user_profile = request.user.userprofile
    context = {
        'balance': user_profile.balance,
        'daily_mines': user_profile.plan.daily_mines if user_profile.plan else 0,
        'mines_done': user_profile.mines_today,
        'daily_ads': user_profile.plan.daily_ads if user_profile.plan else 0,
        'ads_watched': user_profile.ads_watched_today,
        'user': request.user,
    }
    return render(request, 'tasks/perform_task.html', context)

# ------------------------
# Financial Views
# ------------------------
@login_required
def deposit(request):
    """
    Processes a deposit request by creating a DepositRequest record.
    """
    if request.method == 'POST':
        amount_str = request.POST.get("amount")
        payment_method = request.POST.get("payment_method")
        reference = request.POST.get("reference", "")
        try:
            amount = Decimal(amount_str)
        except (InvalidOperation, TypeError):
            messages.error(request, "Please enter a valid amount.")
            return redirect('deposit')
        
        if amount <= 0:
            messages.error(request, "Please enter an amount greater than zero.")
            return redirect('deposit')
        
        DepositRequest.objects.create(
            user=request.user.userprofile,
            amount=amount,
            payment_method=payment_method,
            reference=reference,
            status='pending'
        )
        messages.success(request, "Deposit request submitted successfully. Await admin approval.")
        return redirect('home')
    
    return render(request, 'tasks/deposit.html')

@login_required
def withdrawal(request):
    """
    Processes a withdrawal request with a minimum amount of $500.
    """
    if request.method == 'POST':
        try:
            amount_str = request.POST.get("amount")
            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, TypeError):
                messages.error(request, "Please enter a valid withdrawal amount.")
                return redirect('withdrawal')
            
            if amount < Decimal('500'):
                messages.error(request, "Minimum withdrawal is $500.")
                return redirect('withdrawal')
            
            user_profile = request.user.userprofile
            WithdrawalRequest.objects.create(
                user=user_profile,
                amount=amount,
                status='pending'
            )
            messages.success(request, "Withdrawal request submitted successfully. Await admin approval.")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"Error during withdrawal request: {str(e)}")
            return redirect('home')
    
    return render(request, 'tasks/withdrawal.html')

def request_withdrawal(request):
    """
    Allows the user to request a withdrawal directly.
    """
    if request.method == "POST":
        try:
            amount = float(request.POST.get("amount"))
            if request.user.userprofile.balance < amount:
                messages.error(request, "Insufficient balance.")
                return redirect("user_dashboard")
            Withdrawal.objects.create(user=request.user, amount=amount, status="pending")
            messages.success(request, "Withdrawal request submitted. Awaiting admin approval.")
            return redirect("user_dashboard")
        except Exception as e:
            messages.error(request, f"Error requesting withdrawal: {str(e)}")
            logger.error(f"[REQUEST_WITHDRAWAL] Error: {str(e)}")
            return redirect("user_dashboard")
    return render(request, "tasks/withdrawal_request.html")

# ------------------------
# Plan Activation / Choice
# ------------------------
@login_required
def choose_plan(request):
    """
    Renders a page for the user to choose and activate/upgrade a plan.
    """
    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            messages.error(request, "Invalid plan selected.")
            return redirect("choose_plan")
        
        user_profile = request.user.userprofile
        if user_profile.plan and user_profile.plan.id == plan.id:
            messages.error(request, "You are already on this plan. Please select a different plan to upgrade.")
            return redirect("choose_plan")
        if user_profile.balance < plan.activation_fee:
            messages.error(request, "Insufficient balance to activate this plan.")
            return redirect("choose_plan")
        
        user_profile.balance -= plan.activation_fee
        if user_profile.plan:
            user_profile.mines_today = 0
            user_profile.last_mine_date = None
            user_profile.ads_watched_today = 0
            user_profile.last_ad_date = None
        
        user_profile.plan = plan
        user_profile.plan_activation_date = datetime.date.today()
        user_profile.save()
        
        referral_code = request.session.get("referral_code", None)
        if referral_code:
            try:
                inviter = UserProfile.objects.get(referral_code=referral_code)
                if plan.name.strip().lower() != "trainee":
                    inviter.balance += plan.invitation_commission
                    inviter.save()
                    logger.info(f"Commission of {plan.invitation_commission} awarded to inviter {inviter.user.username}")
                else:
                    logger.info("No commission awarded because the new plan is 'trainee'")
            except UserProfile.DoesNotExist:
                logger.warning("Referral code invalid; no inviter found.")
            request.session.pop("referral_code", None)
        
        messages.success(request, "Plan activated/upgraded successfully! Your daily limits have been reset.")
        return redirect("home")
    else:
        plans = Plan.objects.all()
        user_balance = request.user.userprofile.balance
        return render(request, "tasks/choose_plan.html", {"plans": plans, "balance": user_balance})

# ------------------------
# Other Views
# ------------------------
@login_required
def invite(request):
    """Generates an invitation link for the user."""
    user_profile = request.user.userprofile
    if not user_profile.referral_code:
        user_profile.referral_code = f"{request.user.username}{random.randint(1000, 9999)}"
        user_profile.save()
    base_url = request.build_absolute_uri('/')
    invite_url = f"{base_url}tasks/register/?referral_code={user_profile.referral_code}"
    return render(request, 'tasks/invite.html', {'invite_url': invite_url})

@login_required
def contact_support(request):
    return render(request, 'tasks/contact_support.html')

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

def currency_converter(request):
    """
    A simple view to convert USD to another currency.
    Assumes a conversion rate of 1 unit = 100 USD.
    """
    result = None
    error = None
    USD_amount = None
    conversion_rate = Decimal('100')
    if request.method == "POST":
        USD_str = request.POST.get("USD")
        try:
            USD_amount = Decimal(USD_str)
            result = USD_amount / conversion_rate
        except (InvalidOperation, TypeError):
            error = "Please enter a valid amount in USD."
    return render(request, "tasks/currency_converter.html", {
        "result": result,
        "error": error,
        "USD_amount": USD_amount,
    })

def income_summary(request):
    today = now().date()
    one_week_ago = today - timedelta(days=7)
    one_month_ago = today - timedelta(days=30)

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        print("UserProfile does not exist for this user.")
        return render(request, 'income_summary.html', {
            "total_earnings": 0,
            "today_income": 0,
            "week_income": 0,
            "month_income": 0,
        })

    total_earnings = Income.objects.filter(user=user_profile).aggregate(total=Sum('amount'))['total'] or 0
    today_income = Income.objects.filter(user=user_profile, timestamp__date=today).aggregate(total=Sum('amount'))['total'] or 0
    week_income = Income.objects.filter(user=user_profile, timestamp__date__gte=one_week_ago).aggregate(total=Sum('amount'))['total'] or 0
    month_income = Income.objects.filter(user=user_profile, timestamp__date__gte=one_month_ago).aggregate(total=Sum('amount'))['total'] or 0

    # Debugging prints
    print(f"User: {request.user.username}")
    print(f"Total Earnings: {total_earnings}")
    print(f"Today's Income: {today_income}")
    print(f"This Week's Income: {week_income}")
    print(f"This Month's Income: {month_income}")

    context = {
        "total_earnings": total_earnings,
        "today_income": today_income,
        "week_income": week_income,
        "month_income": month_income,
    }
    return render(request, 'income_summary.html', context)

@staff_member_required
def admin_dashboard(request):
    # Get today's date
    today = timezone.now().date()
    
    # Aggregate all transactions made today
    today_transactions = Transaction.objects.filter(timestamp__date=today)
    total_earnings = today_transactions.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Count active users
    # Option 1: Count all users with is_active=True
    active_users_count = User.objects.filter(is_active=True).count()

    # Option 2: Count users who have logged in within the last 24 hours
    # active_users_count = User.objects.filter(last_login__gte=timezone.now()-timezone.timedelta(days=1)).count()

    context = {
        "total_earnings": total_earnings,
        "active_users_count": active_users_count,
        "today": today,
    }
    return render(request, "admin_dashboard.html", context)

@csrf_exempt  # Disable CSRF for testing; remove this in production if using authentication
def reset_tasks_view(request):
    if request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE tasks SET status = 'pending' WHERE status != 'pending';")
                cursor.execute("UPDATE user_profiles SET last_reset = NOW();")

            return JsonResponse({"message": "Tasks reset successfully!"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Invalid request method"}, status=400)