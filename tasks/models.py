from django.db import models
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()

class Plan(models.Model):
    name = models.CharField(max_length=100)  # e.g., "Trainee", "Plan 1000", etc.
    activation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    daily_mines = models.IntegerField(default=0)
    reward_per_mine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    daily_ads = models.IntegerField(default=0)
    reward_per_ad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    membership_duration = models.IntegerField(default=0)  # in days
    invitation_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    referral_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    wallet_address = models.CharField(max_length=255, null=True, blank=True)  # Add wallet address field
    # Fields for mining limits:
    mines_today = models.IntegerField(default=0)
    last_mine_date = models.DateField(null=True, blank=True)
    # Fields for ads:
    ads_activated = models.BooleanField(default=False)
    ads_watched_today = models.IntegerField(default=0)
    last_ad_date = models.DateField(null=True, blank=True)
    # Field to store the date the plan was activated (for membership expiration)
    plan_activation_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class Task(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.name}"

class Transaction(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.amount} ({self.status})"

class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    WITHDRAWAL_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('airtel_money', 'Airtel Money'),
        ('btc', 'BTC'),
        ('usdt', 'USDT'),
        ('binance', 'Binance'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    withdrawal_method = models.CharField(max_length=20, choices=WITHDRAWAL_METHODS, default='mpesa')
    created_at = models.DateTimeField(auto_now_add=True)

class DepositRequest(models.Model):
    PAYMENT_METHOD_CHOICES = [
         ('binance', 'Binance'),
         ('mpesa', 'Safaricom M-Pesa'),
         ('airtel', 'Airtel Money'),
    ]
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=100, blank=True, null=True)  # optional transaction id
    status = models.CharField(max_length=20, default='pending')  # pending, approved, rejected
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
         return f"{self.user.user.username} - {self.amount} via {self.get_payment_method_display()}"
    
class CommissionTransaction(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='commission_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commission of {self.amount} for {self.user.user.username} on {self.created_at:%Y-%m-%d %H:%M:%S}"
class Deposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_pin_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class VirtualApp(models.Model):
    name = models.CharField(max_length=255)
    download_link = models.URLField()
    reward = models.DecimalField(max_digits=10, decimal_places=2)  # Reward for downloading
    created_at = models.DateTimeField(auto_now_add=True)

class Ad(models.Model):
    title = models.CharField(max_length=255)
    video_url = models.URLField()
    reward = models.DecimalField(max_digits=10, decimal_places=2)  # Reward for watching
    duration = models.IntegerField()  # Duration in seconds
    created_at = models.DateTimeField(auto_now_add=True)