import uuid
from django.db import models
from django.conf import settings
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils.timezone import timezone
from datetime import timedelta
from django.db.models import Sum
from datetime import date
from django.utils import timezone


# ---------------------------
# CONSTANTS
# ---------------------------
PERIOD_CHOICES = [
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
]

WITHDRAWAL_METHODS = [
    ('mpesa', 'M-Pesa'),
    ('airtel_money', 'Airtel Money'),
    ('btc', 'Bitcoin'),
    ('tether', 'Tether'),
    ('binance', 'Binance'),
]

STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

PAYMENT_METHOD_CHOICES = [
    ('binance', 'Binance'),
    ('mpesa', 'Safaricom M-Pesa'),
    ('airtel', 'Airtel Money'),
]

# ---------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    referral_count = models.IntegerField(default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tasks_completed_today = models.IntegerField(default=0)  # Track daily completed tasks

    # ✅ Referral System Fields
    referral_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")

    wallet_address = models.CharField(max_length=255, null=True, blank=True)

    # ✅ Plan Subscription
    plan = models.ForeignKey("Plan", on_delete=models.SET_NULL, null=True, blank=True)

    # ✅ Daily task counters
    mines_today = models.IntegerField(default=0)
    last_mine_date = models.DateField(null=True, blank=True)
    ads_activated = models.BooleanField(default=False)
    ads_watched_today = models.IntegerField(default=0)
    last_ad_date = models.DateField(null=True, blank=True)
    plan_activation_date = models.DateField(null=True, blank=True)

    # ✅ Earnings & Commissions
    total_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # ✅ New fields for income tracking
    daily_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    weekly_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def save(self, *args, **kwargs):
        # Generate referral code if not exists
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4().hex[:8])  # Generate unique referral code
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

    def update_income(self, reward, task_date):
        """ Update daily, weekly, and monthly income based on task completion date """
        today = timezone.now().date()
        start_of_week = today - timezone.timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        # Update Daily Income
        if task_date == today:
            self.daily_income += reward

        # Update Weekly Income
        if task_date >= start_of_week:
            self.weekly_income += reward

        # Update Monthly Income
        if task_date >= start_of_month:
            self.monthly_income += reward

        # Update Total Commission
        self.total_commission += reward

        self.save()  # Save the updated values

class Plan(models.Model):
    name = models.CharField(max_length=100)
    activation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    daily_mines = models.IntegerField(default=0)
    reward_per_mine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    daily_ads = models.IntegerField(default=0)
    reward_per_ad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    membership_duration = models.IntegerField(default=0)  # in days
    invitation_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name


# ---------------------------
# TASKS & TRANSACTIONS
# ---------------------------
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("completed", "Completed")])
    completed_at = models.DateTimeField(auto_now_add=True)

    def complete_task(self):
        if self.status == 'completed':
            user_profile = self.user.userprofile
            
            # Update total balance
            user_profile.balance += self.reward
            
            # Calculate daily, weekly, and monthly income
            today = timezone.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            start_of_month = today.replace(day=1)

            # Daily Income
            if self.completed_at.date() == today:
                user_profile.daily_income += self.reward
            
            # Weekly Income
            if self.completed_at.date() >= start_of_week:
                user_profile.weekly_income += self.reward
            
            # Monthly Income
            if self.completed_at.date() >= start_of_month:
                user_profile.monthly_income += self.reward

            # Update total commission (optional, if needed)
            user_profile.total_commission += self.reward

            # Save the profile after updates
            user_profile.save()

            # Log the income
            Income.objects.create(
                user=self.user,
                amount=self.reward,
                source="Task Reward"
            )

class Transaction(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.amount}"


class CommissionTransaction(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.amount}"


# ---------------------------
# WITHDRAWALS & DEPOSITS
# ---------------------------
class WithdrawalRequest(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="withdrawal_requests")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    withdrawal_method = models.CharField(max_length=20, choices=WITHDRAWAL_METHODS, default='mpesa')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        Handles balance deduction and refund logic.
        - Deduct balance when a new request is made.
        - Refund balance if a rejected withdrawal is changed to approved.
        """
        if self.pk:  # Check if this is an update operation
            original = WithdrawalRequest.objects.get(pk=self.pk)

            if original.status == 'pending' and self.status == 'approved':
                # Withdrawal approved → Balance remains deducted (no changes needed)
                pass
            elif original.status == 'pending' and self.status == 'rejected':
                # Withdrawal rejected → Refund the user
                self.user.balance += self.amount
                self.user.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.user.username} - ${self.amount} ({self.status})"

    class Meta:
        verbose_name_plural = "Withdrawal Requests"

class Withdrawal(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    withdrawal_method = models.CharField(max_length=20, choices=WITHDRAWAL_METHODS, default='mpesa')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} - ${self.amount} ({self.status})"

    class Meta:
        verbose_name_plural = "Withdrawals"


class DepositRequest(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        """
        Automatically update user balance when the deposit is approved.
        Prevents multiple credits if status changes again.
        """
        if self.pk:  # Check if this is an update operation
            original = DepositRequest.objects.get(pk=self.pk)

            if original.status != 'approved' and self.status == 'approved':
                # Deposit was just approved → Add money to user balance
                self.user.balance += self.amount
                self.user.save()
            elif original.status == 'approved' and self.status != 'approved':
                # Deposit was previously approved but now changed → Revert balance
                self.user.balance -= self.amount
                self.user.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.user.username} - {self.amount} via {self.get_payment_method_display()}"

class Deposit(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="deposits")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_pin_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.amount} (Verified: {self.mpesa_pin_verified})"
# ---------------------------
# EARNINGS
# ---------------------------
class EarningsRecord(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='earnings_records')
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    total_income = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_deposits = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_withdrawals = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.period_type.capitalize()} {self.period_start} to {self.period_end}"


# ---------------------------
# ADS & VIRTUAL APPS
# ---------------------------
class VirtualApp(models.Model):
    name = models.CharField(max_length=255)
    download_link = models.URLField()
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class Ad(models.Model):
    title = models.CharField(max_length=255)
    video_url = models.URLField()
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField()  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)


class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=100, default="Task Reward")
    timestamp = models.DateTimeField(auto_now_add=True)  # This should be present
