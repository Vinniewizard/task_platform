import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth

def get_mpesa_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    consumer_key = settings.MPESA_CONFIG["CONSUMER_KEY"]
    consumer_secret = settings.MPESA_CONFIG["CONSUMER_SECRET"]

    response = requests.get(url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
    access_token = response.json().get("access_token")
    return access_token
