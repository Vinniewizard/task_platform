from django.urls import path
from .views import initiate_stk_push, mpesa_callback


urlpatterns = [
    path("stk_push/", initiate_stk_push, name="stk_push"),
    path("callback/", mpesa_callback, name="mpesa_callback"),
]
