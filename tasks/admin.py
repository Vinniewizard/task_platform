from django.contrib import admin, messages
from django.utils import timezone
from .models import (
    UserProfile, Task, Transaction, Plan, CommissionTransaction,
    Withdrawal, DepositRequest, WithdrawalRequest
)
from django.urls import reverse
from django.utils.html import format_html

# ---------------------------------
# ✅ Approve & Reject Deposits
# ---------------------------------
@admin.action(description="Approve selected deposits")
def approve_deposits(modeladmin, request, queryset):
    approved_count = 0
    for deposit in queryset:
        if deposit.status == 'pending':  
            deposit.status = 'approved'
            deposit.save()
            deposit.user.balance += deposit.amount  # ✅ Credit balance
            deposit.user.save()
            approved_count += 1
    messages.success(request, f"{approved_count} deposits approved successfully.")

@admin.action(description="Reject selected deposits")
def reject_deposits(modeladmin, request, queryset):
    rejected_count = 0
    for deposit in queryset:
        if deposit.status == 'pending':  
            deposit.status = 'rejected'
            deposit.save()
            rejected_count += 1
    messages.success(request, f"{rejected_count} deposits rejected successfully.")

@admin.register(DepositRequest)
class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['user__user__username', 'reference']
    actions = [approve_deposits, reject_deposits]


# ---------------------------------
# ✅ Approve & Reject Withdrawals
# ---------------------------------
@admin.action(description="Approve selected withdrawals")
def approve_withdrawals(modeladmin, request, queryset):
    approved_count = 0
    for withdrawal in queryset:
        if withdrawal.status == 'pending':  
            withdrawal.status = 'approved'
            withdrawal.save()
            approved_count += 1
    messages.success(request, f"{approved_count} withdrawals approved successfully.")

@admin.action(description="Reject selected withdrawals")
def reject_withdrawals(modeladmin, request, queryset):
    rejected_count = 0
    for withdrawal in queryset:
        if withdrawal.status == 'pending':  
            withdrawal.status = 'rejected'
            withdrawal.user.balance += withdrawal.amount  # ✅ Refund balance
            withdrawal.user.save()
            withdrawal.save()
            rejected_count += 1
    messages.success(request, f"{rejected_count} withdrawals rejected successfully.")

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'withdrawal_method', 'status', 'created_at']
    list_filter = ['status', 'withdrawal_method']
    search_fields = ['user__user__username']
    actions = [approve_withdrawals, reject_withdrawals]

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    actions = [approve_withdrawals, reject_withdrawals]


# ---------------------------------
# ✅ User Profile Admin (With Referral Count & Earnings)
# ---------------------------------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'phone_number', 'balance', 'plan',
        'get_referral_count', 'get_today_income', 
        'get_week_income', 'get_month_income', 'total_commission', 
        'reset_button', 'reset_plan_button'
    )
    list_filter = ('plan',)
    search_fields = ('user__username', 'phone_number')

    def reset_button(self, obj):
        url = reverse('reset_user_profile', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" style="color:white; background-color:red; padding:5px 10px; text-decoration:none; font-weight:bold; border-radius:4px;">Reset Profile</a>',
            url
        )
    reset_button.short_description = "Reset Profile"
    def reset_plan_button(self, obj):
     if obj.plan:  # Check if obj.plan is not None
        url = reverse('reset_user_profile_plan', args=[obj.plan.id])
        return format_html('<a href="{}">Reset Plan</a>', url)
        return "No Plan Assigned"  # Return a default message if no plan is assigned

    reset_plan_button.short_description = "Reset Plan"
    
    def get_referral_count(self, obj):
        return obj.referred_users.count()
    get_referral_count.short_description = "Referrals"

    def get_today_income(self, obj):
        return obj.daily_income
    get_today_income.short_description = "Today's Income"

    def get_week_income(self, obj):
        return obj.weekly_income
    get_week_income.short_description = "Weekly Income"

    def get_month_income(self, obj):
        return obj.monthly_income
    get_month_income.short_description = "Monthly Income"

# ---------------------------------
# ✅ Register Other Models
# ---------------------------------
admin.site.register(CommissionTransaction)
admin.site.register(Task)
admin.site.register(Transaction)
admin.site.register(Plan)
