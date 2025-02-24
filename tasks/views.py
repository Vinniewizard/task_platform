import random
import time
import datetime
import logging
from django.utils import timezone

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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import Withdrawal  # Ensure correct model import
from django.utils.timezone import now, timedelta
from django.db import transaction
import uuid


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
    print(f"Withdrawals found: {withdrawals}")  # Debugging

    if withdrawals.exists():
        withdrawal = random.choice(withdrawals)
        print(f"Randomly selected withdrawal: {withdrawal}")  # Debugging

        withdrawal_method = withdrawal.withdrawal_method.lower()
        user_profile = withdrawal.user  # Fix: Withdrawal.user is already UserProfile

        if not user_profile:
            print("User profile not found!")  # Debugging
            return JsonResponse({"error": "User profile not found for withdrawal."})

        phone_number = getattr(user_profile, "phone_number", "")
        wallet_address = getattr(user_profile, "wallet_address", "")

        if withdrawal_method in ["mpesa", "airtel_money"]:
            masked_info = mask_phone_number(phone_number) if phone_number else "Unknown"
        else:
            masked_info = mask_address(wallet_address) if wallet_address else "Unknown"

        message = f"💸 {masked_info} just withdrew ${withdrawal.amount} via {withdrawal_method.capitalize()}! 🚀"

        return JsonResponse({
            "name": user_profile.user.username,  # Fix: Access username via UserProfile
            "amount": f"${withdrawal.amount}",
            "method": withdrawal_method.capitalize(),
            "masked_info": masked_info,
            "message": message,
        })

    print("No withdrawals found.")  # Debugging
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
    If a referral code is used, the referrer earns a commission.
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():  # Ensures database integrity
                    user = form.save(commit=False)
                    user.username = form.cleaned_data["phone_number"]
                    user.save()

                    # Create or update UserProfile
                    user_profile, created = UserProfile.objects.get_or_create(user=user)
                    user_profile.phone_number = form.cleaned_data["phone_number"]
                    
                    # Handle Referral Code
                    referral_code = request.POST.get("referral_code")
                    if referral_code:
                        try:
                            referrer = UserProfile.objects.get(referral_code=referral_code)
                            user_profile.referred_by = referrer
                            user_profile.save()

                            # ✅ Add commission based on referrer's plan
                            if referrer.plan:
                                referrer.balance += referrer.plan.invitation_commission
                                referrer.save()
                                messages.success(request, f"You have earned ${referrer.plan.invitation_commission} for inviting {user.username}!")
                            else:
                                messages.warning(request, "Referrer does not have an active plan. No commission awarded.")

                        except UserProfile.DoesNotExist:
                            messages.error(request, "Invalid referral code.")

                    user_profile.save()

                    # Send OTP for verification
                    otp = send_otp(form.cleaned_data["phone_number"])
                    request.session["otp"] = otp
                    request.session["phone_number"] = form.cleaned_data["phone_number"]

                    messages.success(request, "Registration successful. OTP sent.")
                    return redirect("verify_otp")

            except Exception as e:
                messages.error(request, f"🔥 Registration error: {e}")

        else:
            messages.error(request, f"❌ Form Errors: {form.errors}")

    else:
        form = RegistrationForm()

    return render(request, "tasks/register.html", {"form": form})
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

@login_required
def mine(request):
    try:
        user_profile = request.user.userprofile
        # Use local time for today's date
        today = timezone.localtime(timezone.now()).date()
        
        # Reset daily counter if it's a new day
        if user_profile.last_mine_date != today:
            user_profile.mines_today = 0
            user_profile.last_mine_date = today
            user_profile.save()  # Save the reset values

        # Check if daily limit is reached
        if user_profile.plan and user_profile.mines_today >= user_profile.plan.daily_mines:
            return JsonResponse({'status': 'error', 'message': 'Daily mining limit reached.'})
        
        simulate_delay(10)  # Simulate task delay
        
        # Increment counter and update balance
        reward = user_profile.plan.reward_per_mine
        user_profile.balance += reward
        user_profile.mines_today += 1
        user_profile.save()  # Save changes to the database
        
        return JsonResponse({
            'status': 'success',
            'balance': float(user_profile.balance),
            'reward': reward,
            'mines_done': user_profile.mines_today
        })
    except Exception as e:
        logger.error(f"[MINE] Error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error during mining: {str(e)}'})

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
    Processes a deposit request and ensures the M-Pesa reference number is unique.
    """
    if request.method == 'POST':
        payment_method = request.POST.get("payment_method")
        phone_number = request.POST.get("phone_number")
        amount_str = request.POST.get("amount")
        reference = request.POST.get("reference", "").strip()

        # Validate amount
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, "Please enter a valid deposit amount.")
            return redirect('deposit')

        # Check if the reference number is unique
        if DepositRequest.objects.filter(reference=reference).exists():
            messages.error(request, "This reference number has already been used. Please use a valid one.")
            return redirect('deposit')

        # Create deposit request
        DepositRequest.objects.create(
            user=request.user.userprofile,
            amount=amount,
            payment_method=payment_method,
            reference=reference,
            status='pending'
        )

        messages.success(request, "Deposit request submitted successfully! Await admin approval.")
        return redirect('home')

    return render(request, 'tasks/deposit.html')
@login_required
def withdrawal(request):
    """
    Processes a withdrawal request with a minimum amount of $2.
    """
    user_profile = request.user.userprofile  # Get the user's profile

    if request.method == 'POST':
        try:
            amount_str = request.POST.get("amount", "").strip()  # Ensure no empty values
            print(f"Raw input amount: '{amount_str}'")  # Debugging output

            if not amount_str:
                messages.error(request, "Please enter a withdrawal amount.")
                return redirect('withdrawal')

            try:
                amount = Decimal(amount_str)
                print(f"Converted Decimal amount: {amount}")  # Debugging output
            except (InvalidOperation, ValueError):
                messages.error(request, "Invalid amount entered. Please enter a numeric value.")
                return redirect('withdrawal')

            # Ensure the withdrawal amount is at least $2.00
            if amount < Decimal('2.00'):
                messages.error(request, f"Minimum withdrawal is $2. You entered: ${amount}")
                return redirect('withdrawal')

            # Check if user has enough balance
            if amount > user_profile.balance:
                messages.error(request, "Insufficient balance for this withdrawal.")
                return redirect('withdrawal')

            # Create withdrawal request
            WithdrawalRequest.objects.create(
                user=user_profile,
                amount=amount,
                status='pending'
            )

            # Deduct amount from user balance
            user_profile.balance -= amount
            user_profile.save()

            messages.success(request, "Withdrawal request submitted successfully. Await admin approval.")
            return redirect('home')

        except Exception as e:
            messages.error(request, f"Error during withdrawal request: {str(e)}")
            return redirect('home')

    return render(request, 'tasks/withdrawal.html', {'balance': user_profile.balance})

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

    base_url = request.build_absolute_uri("/")
    invite_url = f"{base_url}tasks/register/?referral_code={user_profile.referral_code}"

    return render(request, "tasks/invite.html", {"invite_url": invite_url})
@login_required
def contact_support(request):
    return render(request, 'tasks/contact_support.html')

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

# You can define your exchange rates here or fetch them from an API
EXCHANGE_RATES = {
    'KSH': 130.00,  # Example: 1 USD = 130 KSH
    'EUR': 0.92,    # Example: 1 USD = 0.92 EUR
    'GBP': 0.80,    # Example: 1 USD = 0.80 GBP
    # Add more currencies if needed
}

def currency_converter(request):
    converted_value = None
    currency = None
    if request.method == 'POST':
        try:
            amount_usd = float(request.POST.get('usd_amount'))
            currency = request.POST.get('currency')

            # Convert the USD value based on selected currency
            if currency and currency in EXCHANGE_RATES:
                converted_value = round(amount_usd * EXCHANGE_RATES[currency], 2)

            context = {
                'amount_usd': amount_usd,
                'converted_value': converted_value,
                'currency': currency,
                'currencies': EXCHANGE_RATES
            }
        except ValueError:
            context = {'error': "Invalid input. Please enter a valid number."}

        return render(request, 'tasks/currency_converter.html', context)

    # Preload the currencies when the page is loaded (for the dropdown)
    context = {
        'currencies': EXCHANGE_RATES
    }
    return render(request, 'tasks/currency_converter.html', context)

def income_summary(request):
    user_profile = UserProfile.objects.get(user=request.user)
    user_plan = user_profile.plan  # Get the user's plan

    # Total balance
    total_income = user_profile.balance

    # Get current date
    today = now().date()
    week_start = today - timedelta(days=today.weekday())  # Start of the week
    month_start = today.replace(day=1)  # Start of the month

    # Calculate income
    today_income = Income.objects.filter(user=request.user, timestamp__date=today).aggregate(total=Sum("amount"))["total"] or 0
    week_income = Income.objects.filter(user=request.user, timestamp__gte=week_start).aggregate(total=Sum("amount"))["total"] or 0
    month_income = Income.objects.filter(user=request.user, timestamp__gte=month_start).aggregate(total=Sum("amount"))["total"] or 0

    # Referral commission from the user's plan
    referral_commission = user_plan.invitation_commission if user_plan else 0

    # Generate invite link
    base_url = request.build_absolute_uri('/')
    invite_url = f"{base_url}tasks/register/?referral_code={user_profile.referral_code}"

    # Fetch earnings data for the last 7 days
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [day.strftime("%b %d") for day in last_7_days]
    earnings_data = []
    
    for day in last_7_days:
        total_earning = Income.objects.filter(user=request.user, timestamp__date=day).aggregate(total=Sum("amount"))["total"] or 0
        earnings_data.append(total_earning)

    context = {
        "total_income": total_income,
        "today_income": today_income,
        "week_income": week_income,
        "month_income": month_income,
        "invite_url": invite_url,
        "referral_code": user_profile.referral_code,
        "referral_commission": referral_commission,
        "user_plan": user_plan,  # Pass the plan details to the template
        "labels": labels,  # Pass labels for graph
        "earnings_data": earnings_data,  # Pass earnings data for graph
    }

    return render(request, "tasks/income_summary.html", context)
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