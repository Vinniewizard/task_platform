import requests
import base64
import json
import logging
from django.http import JsonResponse
from django.conf import settings
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from .mpesa_utils import get_mpesa_access_token
from transactions.models import Deposit  # Import Deposit model

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 📌 Function to validate and format phone number
def format_phone_number(phone_number):
    if phone_number.startswith("+254") and len(phone_number) == 13:
        return phone_number[1:]  # Remove the '+' sign
    elif phone_number.startswith("254") and len(phone_number) == 12:
        return phone_number
    elif phone_number.startswith("07") and len(phone_number) == 10:
        return "254" + phone_number[1:]
    elif phone_number.startswith("01") and len(phone_number) == 10:
        return "254" + phone_number[1:]
    else:
        return None  # Invalid format

# 📌 **M-Pesa Callback View**
@csrf_exempt
def mpesa_callback(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        logging.info(f"M-Pesa Callback Data: {data}")  # Debugging

        # Extract required fields
        stk_callback = data.get("Body", {}).get("stkCallback", {})
        result_code = stk_callback.get("ResultCode")
        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")

        if result_code == 0:  # ✅ Transaction successful
            callback_items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            amount = next((item["Value"] for item in callback_items if item["Name"] == "Amount"), None)
            phone_number = next((item["Value"] for item in callback_items if item["Name"] == "PhoneNumber"), None)

            if not phone_number:
                logging.error("🚨 Missing Phone Number in Callback")
                return JsonResponse({"error": "Phone number missing in callback"}, status=400)

            # Find and update the latest deposit for this phone number
            deposit = Deposit.objects.filter(phone_number=phone_number).last()
            if deposit:
                deposit.mpesa_pin_verified = True
                deposit.save()
                return JsonResponse({"message": "✅ Deposit successful!"})
            else:
                return JsonResponse({"error": "❌ No matching deposit found"}, status=404)

        else:
            logging.warning(f"⚠️ M-Pesa Transaction Failed: ResultCode {result_code}")
            return JsonResponse({"error": "Transaction failed!"}, status=400)

    except json.JSONDecodeError:
        logging.error("❌ Invalid JSON in M-Pesa Callback")
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except KeyError as e:
        logging.error(f"❌ Missing Key in M-Pesa Callback: {e}")
        return JsonResponse({"error": f"Missing key: {e}"}, status=400)
    except Exception as e:
        logging.error(f"❌ Error processing M-Pesa callback: {str(e)}")
        return JsonResponse({"error": f"Error processing callback: {str(e)}"}, status=500)

# 📌 **STK Push Initiation View**
@csrf_exempt
def initiate_stk_push(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        # Load and parse JSON request
        data = json.loads(request.body.decode("utf-8"))
        logging.info(f"📨 Received STK Push request: {data}")

        phone_number = data.get("phone_number")
        amount = data.get("amount")

        # Validate inputs
        if not phone_number or not amount:
            return JsonResponse({"error": "Phone number and amount are required"}, status=400)

        phone_number = format_phone_number(phone_number)
        if not phone_number:
            return JsonResponse({"error": "Invalid phone number format"}, status=400)

        amount = int(amount)  # Ensure amount is integer

        # Get MPesa access token
        access_token = get_mpesa_access_token()
        if not access_token:
            logging.error("❌ Failed to obtain MPesa access token")
            return JsonResponse({"error": "Failed to obtain MPesa access token"}, status=500)

        # Generate M-Pesa Password
        shortcode = settings.MPESA_CONFIG["BUSINESS_SHORTCODE"]
        passkey = settings.MPESA_CONFIG["PASSKEY"]
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode("utf-8")

        # STK Push Payload
        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,  # The user paying
            "PartyB": shortcode,  # The free shortcode
            "PhoneNumber": phone_number,  # User's phone number
            "CallBackURL": settings.MPESA_CONFIG["CALLBACK_URL"],
            "AccountReference": phone_number,  # Using phone number as account number
            "TransactionDesc": "Deposit to account"
        }

        stk_push_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        # Send STK Push Request
        response = requests.post(stk_push_url, json=payload, headers=headers)
        response_data = response.json()

        logging.info(f"📨 Safaricom API Response: {response.status_code}, {response_data}")

        if response.status_code == 200 and "ResponseCode" in response_data:
            # Save deposit in the database
            Deposit.objects.create(user=request.user, amount=amount, phone_number=phone_number)

            return JsonResponse({
                "message": "STK Push request sent. Enter your M-Pesa PIN.",
                "response": response_data
            }, status=200)
        else:
            error_message = response_data.get("errorMessage", "Unknown error")
            logging.error(f"❌ STK Push Error: {error_message}")
            return JsonResponse({"error": "Failed to initiate STK Push", "details": error_message}, status=500)

    except json.JSONDecodeError:
        logging.error("❌ Invalid JSON format in STK Push request")
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        logging.error(f"⚠️ Unexpected error: {str(e)}")
        return JsonResponse({"error": "An unexpected error occurred", "details": str(e)}, status=500)