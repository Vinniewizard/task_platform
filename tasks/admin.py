from django.contrib import admin
from .models import UserProfile, Task, Transaction, Plan, CommissionTransaction
from .models import Withdrawal, DepositRequest, WithdrawalRequest
from django.utils import timezone

@admin.action(description="Approve selected deposits")
def approve_deposits(modeladmin, request, queryset):
    approved_count = 0

    for deposit in queryset:
        if deposit.status.lower() == 'pending':  # Only process pending deposits
            deposit.status = 'approved'
            deposit.save()  # Triggers the balance update
            approved_count += 1

    messages.success(request, f"{approved_count} deposits approved successfully.")

@admin.action(description="Reject selected deposits")
def reject_deposits(modeladmin, request, queryset):
    rejected_count = 0

    for deposit in queryset:
        if deposit.status.lower() == 'pending':  # Only process pending deposits
            deposit.status = 'rejected'
            deposit.save()  # Ensures rejected deposits don't affect balance
            rejected_count += 1

    messages.success(request, f"{rejected_count} deposits rejected successfully.")

class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['user__user__username', 'reference']
    actions = [approve_deposits, reject_deposits]

admin.site.register(DepositRequest, DepositRequestAdmin)

@admin.action(description="Approve selected withdrawal requests")
def approve_withdrawals(modeladmin, request, queryset):
    approved_count = 0

    for withdrawal in queryset:
        if withdrawal.status.lower() == 'pending':  # Only process pending withdrawals
            withdrawal.status = 'approved'
            withdrawal.save()
            approved_count += 1

    messages.success(request, f"{approved_count} withdrawals approved successfully.")

@admin.action(description="Reject selected withdrawal requests")
def reject_withdrawals(modeladmin, request, queryset):
    rejected_count = 0

    for withdrawal in queryset:
        if withdrawal.status.lower() == 'pending':  # Only process pending withdrawals
            withdrawal.status = 'rejected'
            withdrawal.user.balance += withdrawal.amount  # Refund user
            withdrawal.user.save()
            withdrawal.save()
            rejected_count += 1

    messages.success(request, f"{rejected_count} withdrawals rejected successfully.")

class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'withdrawal_method', 'status', 'created_at']
    list_filter = ['status', 'withdrawal_method']
    search_fields = ['user__user__username']
    actions = [approve_withdrawals, reject_withdrawals]

admin.site.register(WithdrawalRequest, WithdrawalRequestAdmin)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    actions = ['approve_withdrawals', 'reject_withdrawals']

    def approve_withdrawals(self, request, queryset):
        queryset.update(status='approved')
    approve_withdrawals.short_description = "Approve selected withdrawals"

    def reject_withdrawals(self, request, queryset):
        queryset.update(status='rejected')
    reject_withdrawals.short_description = "Reject selected withdrawals"

admin.site.register(Withdrawal, WithdrawalAdmin)
admin.site.register(CommissionTransaction)
admin.site.register(Task)
admin.site.register(Transaction)
admin.site.register(Plan)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'balance', 'referral_count', 'today_income', 'week_income', 'month_income', 'total_commission')

    def referral_count(self, obj):
        return obj.referral_count
    referral_count.short_description = "Referrals"

    def today_income(self, obj):
        return obj.daily_income
    today_income.short_description = "Today's Income"

    def week_income(self, obj):
        return obj.weekly_income
    week_income.short_description = "Weekly Income"

    def month_income(self, obj):
        return obj.monthly_income
    month_income.short_description = "Monthly Income"

admin.site.register(UserProfile, UserProfileAdmin)
