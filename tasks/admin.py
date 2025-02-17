from django.contrib import admin

# Register your models here.

from .models import UserProfile, Task, Transaction, Plan
from .models import Withdrawal

from .models import DepositRequest
from .models import WithdrawalRequest

@admin.action(description="Approve selected deposits")
def approve_deposits(modeladmin, request, queryset):
    for deposit in queryset:
        if deposit.status == 'pending':
            deposit.status = 'approved'
            # Add the deposit amount to the user's balance
            deposit.user.balance += deposit.amount
            deposit.user.save()
            deposit.save()

@admin.action(description="Reject selected deposits")
def reject_deposits(modeladmin, request, queryset):
    queryset.update(status='rejected')

class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'payment_method', 'status', 'created_at']
    actions = [approve_deposits, reject_deposits]

admin.site.register(DepositRequest, DepositRequestAdmin)

@admin.action(description="Approve selected withdrawal requests")
def approve_withdrawals(modeladmin, request, queryset):
    for withdrawal in queryset:
        if withdrawal.status == 'pending':
            # Deduct the amount from the user's balance
            user_profile = withdrawal.user
            if user_profile.balance >= withdrawal.amount:
                user_profile.balance -= withdrawal.amount
                user_profile.save()
                withdrawal.status = 'approved'
                withdrawal.save()
            else:
                # Optionally, you can skip or mark as failed if insufficient funds
                withdrawal.status = 'rejected'
                withdrawal.save()

@admin.action(description="Reject selected withdrawal requests")
def reject_withdrawals(modeladmin, request, queryset):
    queryset.update(status='rejected')

class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'created_at']
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

admin.site.register(UserProfile)
admin.site.register(Task)
admin.site.register(Transaction)
admin.site.register(Plan)
