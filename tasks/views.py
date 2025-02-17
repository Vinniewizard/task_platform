import random
import time
import datetime
import logging
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User

from .forms import RegistrationForm
from .models import UserProfile, Task, Withdrawal, Plan, DepositRequest, WithdrawalRequest
from random import choice

# Configure logging
logger = logging.getLogger(__name__)

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
    withdrawals = Withdrawal.objects.all()
    if withdrawals.exists():
        withdrawal = choice(withdrawals)  
        withdrawal_method = withdrawal.withdrawal_method
        user_profile = getattr(withdrawal.user, "userprofile", None)
        if not user_profile:
            return JsonResponse({"error": "User profile not found for withdrawal."})
        if withdrawal_method.lower() in ["mpesa", "airtel_money"]:
            masked_info = mask_phone_number(user_profile.phone_number)
        else:  
            masked_info = mask_address(user_profile.wallet_address)
        message = f"💸 {masked_info} just withdrew ${withdrawal.amount} via {withdrawal_method.capitalize()}! 🚀"
        return JsonResponse({
            "name": withdrawal.user.username,
            "amount": f"${withdrawal.amount}",
            "method": withdrawal_method.capitalize(),
            "masked_info": masked_info,
            "message": message
        })
    return JsonResponse({"error": "No withdrawals yet."})

def simulate_delay(seconds=10):
    """
    Simulates a delay (e.g., for a downloading demo).
    WARNING: In production, avoid blocking calls like time.sleep().
    """
    time.sleep(seconds)

def send_otp(phone_number):
    """
    Simulate sending an OTP. In production, integrate with an SMS API.
    """
    otp = random.randint(100000, 999999)
    logger.info(f"Sending OTP {otp} to {phone_number}")
    return otp

# ------------------------
# Authentication / Registration Views
# ------------------------
def register(request):
    """
    Registers a new user using their phone number.
    If a referral_code is provided via GET, it is stored in session.
    After registration, an OTP is generated and stored in the session,
    and the user is redirected to the OTP verification view.
    """
    # Store referral code if provided in GET parameters.
    if 'referral_code' in request.GET:
        request.session['referral_code'] = request.GET['referral_code']
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # Save user using the custom form.
            user = form.save(commit=False)
            user.username = form.cleaned_data["phone_number"]
            user.save()
            # The post_save signal should create the UserProfile.
            user_profile = user.userprofile
            user_profile.phone_number = form.cleaned_data["phone_number"]
            user_profile.save()
            
            # Generate OTP and store in session.
            otp = send_otp(form.cleaned_data["phone_number"])
            request.session['otp'] = otp
            request.session['phone_number'] = form.cleaned_data["phone_number"]
            
            logger.info(f"User {user.username} registered; OTP sent.")
            return redirect('verify_otp')
    else:
        form = RegistrationForm()
    return render(request, 'tasks/register.html', {'form': form})

def login_view(request):
    """
    Authenticates and logs in the user.
    """
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
    On POST, if the OTP matches, logs in the user.
    Also, if a referral code exists, credits the inviter with a commission of KSh 100.
    """
    if request.method == "POST":
        otp_entered = request.POST.get('otp')
        otp_sent = request.session.get('otp')
        if str(otp_entered) == str(otp_sent):
            phone_number = request.session.get('phone_number')
            user = User.objects.get(username=phone_number)
            login(request, user)
            logger.info(f"User {user.username} OTP verified and logged in.")
            # Process referral commission
            referral_code = request.session.get('referral_code')
            if referral_code:
                try:
                    inviter = UserProfile.objects.get(referral_code=referral_code)
                    if inviter.user != user:
                        inviter.balance += 100  # Fixed commission per referral
                        inviter.save()
                        logger.info(f"Credited inviter {inviter.user.username} with KSh 100 for referral.")
                except UserProfile.DoesNotExist:
                    logger.warning("Referral code invalid.")
                request.session.pop('referral_code', None)
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
@login_required
def home(request):
    return render(request, 'tasks/home.html', {'user': request.user})

@login_required
def task_page(request):
    return render(request, 'tasks/task_page.html')

# ------------------------
# Game Logic / Task Views
# ------------------------
@login_required
def mine(request):
    """
    Processes a mining task:
      - Checks for membership expiration if applicable.
      - Resets daily mine count if needed.
      - Enforces daily mine limit based on user's plan.
      - Simulates a delay and credits reward_per_mine.
    """
    try:
        user_profile = request.user.userprofile
        today = datetime.date.today()
        
        if user_profile.plan and user_profile.plan.membership_duration > 0 and user_profile.plan_activation_date:
            expiry_date = user_profile.plan_activation_date + datetime.timedelta(days=user_profile.plan.membership_duration)
            if today > expiry_date:
                return JsonResponse({'status': 'error', 'message': 'Your membership has expired.'})
        
        if user_profile.last_mine_date != today:
            user_profile.mines_today = 0
            user_profile.last_mine_date = today
            user_profile.save()
        
        if not user_profile.plan:
            return JsonResponse({'status': 'error', 'message': 'No plan assigned. Please choose a plan.'})
        
        if user_profile.mines_today >= user_profile.plan.daily_mines:
            return JsonResponse({'status': 'error', 'message': 'Daily mining limit reached.'})
        
        simulate_delay(10)
        
        reward = user_profile.plan.reward_per_mine
        logger.info(f"[MINE] Balance before: {user_profile.balance}")
        user_profile.balance += reward
        user_profile.mines_today += 1
        user_profile.save()
        logger.info(f"[MINE] Balance after: {user_profile.balance}")
        
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
    Activates ads for the user:
      - Deducts a fee of KSh 200.
      - Resets the daily ad counter.
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
    """
    Processes ad watching:
      - Checks membership expiration.
      - Resets ad counter if needed.
      - Enforces daily ad watch limit.
      - Simulates a delay and credits reward_per_ad.
    """
    try:
        user_profile = request.user.userprofile
        today = datetime.date.today()
        
        if user_profile.plan and user_profile.plan.membership_duration > 0 and user_profile.plan_activation_date:
            expiry_date = user_profile.plan_activation_date + datetime.timedelta(days=user_profile.plan.membership_duration)
            if today > expiry_date:
                return JsonResponse({'status': 'error', 'message': 'Your membership has expired.'})
        
        if user_profile.last_ad_date != today:
            user_profile.ads_watched_today = 0
            user_profile.last_ad_date = today
            user_profile.save()
        
        if not user_profile.plan:
            return JsonResponse({'status': 'error', 'message': 'No plan assigned. Please choose a plan.'})
        
        if not user_profile.ads_activated:
            return JsonResponse({'status': 'error', 'message': 'Ads not activated. Please activate ads.'})
        
        if user_profile.ads_watched_today >= user_profile.plan.daily_ads:
            return JsonResponse({'status': 'error', 'message': 'Daily ad watch limit reached.'})
        
        simulate_delay(10)
        
        reward = user_profile.plan.reward_per_ad
        logger.info(f"[WATCH_AD] Balance before: {user_profile.balance}")
        user_profile.balance += reward
        user_profile.ads_watched_today += 1
        user_profile.save()
        logger.info(f"[WATCH_AD] Balance after: {user_profile.balance}")
        
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
    Processes a task:
      - Finds the first uncompleted task.
      - Simulates a delay.
      - Marks the task as completed.
      - Credits the user with reward_per_mine.
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
    """
    Performs a generic task (adds a fixed amount, KSh 100, to the balance).
    """
    if request.method == 'POST':
        try:
            user_profile = request.user.userprofile
            user_profile.balance += 100
            user_profile.save()
            logger.info(f"[PERFORM_TASK] Balance after performing task: {user_profile.balance}")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"Error performing task: {str(e)}")
            logger.error(f"[PERFORM_TASK] Error: {str(e)}")
            return redirect('home')
    return render(request, 'tasks/perform_task.html')

# ------------------------
# Financial Views
# ------------------------
@login_required
def deposit(request):
    """
    Processes a deposit by creating a DepositRequest record.
    Displays amounts in dollars.
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
    Processes a withdrawal request by creating a WithdrawalRequest record.
    Enforces a minimum withdrawal of $500.
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
            logger.error(f"[WITHDRAWAL] Error: {str(e)}")
            return redirect('home')
    
    return render(request, 'tasks/withdrawal.html')

def request_withdrawal(request):
    """
    Allows the user to request a withdrawal (alternative view).
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
    Renders a page for the user to choose and activate (or upgrade) a plan.
    Prevents reactivation of the same plan (e.g., upgrading to 'trainee' if already on 'trainee').
    Resets daily counters on upgrade.
    Credits referral commission (if applicable) only when upgrading to a plan other than 'trainee'.
    """
    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            messages.error(request, "Invalid plan selected.")
            return redirect("choose_plan")
        
        user_profile = request.user.userprofile

        # Prevent reactivation of the same plan.
        if user_profile.plan and user_profile.plan.id == plan.id:
            messages.error(request, "You are already on this plan. Please select a different plan to upgrade.")
            return redirect("choose_plan")
        
        if user_profile.balance < plan.activation_fee:
            messages.error(request, "Insufficient balance to activate this plan.")
            return redirect("choose_plan")
        
        # Deduct activation fee.
        user_profile.balance -= plan.activation_fee
        
        # If upgrading (existing plan), reset daily counters.
        if user_profile.plan:
            user_profile.mines_today = 0
            user_profile.last_mine_date = None
            user_profile.ads_watched_today = 0
            user_profile.last_ad_date = None
        
        # Set new plan and record activation date.
        user_profile.plan = plan
        user_profile.plan_activation_date = datetime.date.today()
        user_profile.save()
        
        # Process referral commission if present and if plan is not 'trainee'
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
    """
    Generates and displays a referral link for the user.
    """
    user_profile = request.user.userprofile
    if not user_profile.referral_code:
        user_profile.referral_code = f"{request.user.username}{random.randint(1000, 9999)}"
        user_profile.save()
    base_url = request.build_absolute_uri('/')  # e.g., http://127.0.0.1:8000/
    invite_url = f"{base_url}tasks/register/?referral_code={user_profile.referral_code}"
    return render(request, 'tasks/invite.html', {'invite_url': invite_url})

@login_required
def contact_support(request):
    return render(request, 'tasks/contact_support.html')

@login_required
def logout_view(request):
    """
    Logs out the user and redirects to the home page.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')

def currency_converter(request):
    """
    A simple view to convert an amount from KSh to USD.
    Assumes a conversion rate of 1 USD = 100 KSh.
    """
    result = None
    error = None
    ksh_amount = None
    conversion_rate = Decimal('100')
    if request.method == "POST":
        ksh_str = request.POST.get("ksh")
        try:
            ksh_amount = Decimal(ksh_str)
            result = ksh_amount / conversion_rate
        except (InvalidOperation, TypeError):
            error = "Please enter a valid amount in KSh."
    return render(request, "tasks/currency_converter.html", {
        "result": result,
        "error": error,
        "ksh_amount": ksh_amount,
    })
