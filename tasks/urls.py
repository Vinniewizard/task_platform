from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    home, register, login_view, verify_otp, task_page,
    mine, activate_ads, watch_ad, start_task, perform_task,
    deposit, withdrawal, request_withdrawal, choose_plan,
    invite, contact_support, logout_view, currency_converter,
    income_summary, get_random_withdrawal,
)
from .views import reset_tasks_view  # Ensure this import is correc
from . import views
from .views import spin_view, spin_wheel_view
from .views import user_settings_view


#hello

urlpatterns = [
    path('home/', home, name='home'),
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('verify_otp/', verify_otp, name='verify_otp'),
    path('task_page/', task_page, name='task_page'),
    path('mine/', mine, name='mine'),
    path('activate_ads/', activate_ads, name='activate_ads'),
    path('watch_ad/', watch_ad, name='watch_ad'),
    path('start_task/', start_task, name='start_task'),
    path('perform_task/', perform_task, name='perform_task'),
    path('income-summary/', income_summary, name='income_summary'),
    path('deposit/', deposit, name='deposit'),
    path('withdrawal/', withdrawal, name='withdrawal'),
    path("currency-converter/", currency_converter, name="currency_converter"),
    path("currency-converter/", currency_converter, name="currency_converter"),
    path('request_withdrawal/', request_withdrawal, name='request_withdrawal'),
    path('choose_plan/', choose_plan, name='choose_plan'),
    path('invite/', invite, name='invite'),
    path('contact_support/', contact_support, name='contact_support'),
    path('logout/', logout_view, name='logout'),
    path("reset_tasks/", reset_tasks_view, name="reset_tasks"),
    path('tasks/reset-user-profile/<int:pk>/', views.reset_user_profile, name='reset_user_profile'),
    path('tasks/reset-user-profile/plan/<int:plan_id>/', views.reset_user_profile, name='reset_user_profile_plan'),
    path('spin/', spin_view, name='spin_view'),
    path('spin-wheel/', spin_wheel_view, name='spin_wheel_view'),
    path("settings/", user_settings_view, name="user_settings"),
    path('dashboard/', views.dashboard, name='dashboard'),
       
    path('get_random_withdrawal/', get_random_withdrawal, name='get_random_withdrawal'),
    # Password reset paths: new password reset option
    path("password-reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset-complete/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
