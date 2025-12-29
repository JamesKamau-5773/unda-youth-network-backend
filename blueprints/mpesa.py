import base64
from datetime import datetime
import requests
from flask import Blueprint, request, jsonify
from flask_login import login_required
from models import db, Champion, User
from decorators import supervisor_required
import os

mpesa_bp = Blueprint('mpesa', __name__, url_prefix='/api/mpesa')

# M-Pesa Configuration from environment variables
CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET')
SHORTCODE = os.environ.get('MPESA_SHORTCODE')
PASSKEY = os.environ.get('MPESA_PASSKEY')
ENVIRONMENT = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')  # 'sandbox' or 'production'

# Base URLs based on environment
BASE_URL = {
    'sandbox': 'https://sandbox.safaricom.co.ke',
    'production': 'https://api.safaricom.co.ke'
}


def get_access_token():
    """Get OAuth access token from M-Pesa API."""
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        raise ValueError("M-Pesa credentials not configured. Set MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET.")
    
    api_url = f"{BASE_URL[ENVIRONMENT]}/oauth/v1/generate?grant_type=client_credentials"
    
    try:
        response = requests.get(api_url, auth=(CONSUMER_KEY, CONSUMER_SECRET), timeout=30)
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get M-Pesa access token: {str(e)}")


@mpesa_bp.route('/checkout', methods=['POST'])
@login_required
def initiate_stk_push():
    """Initiate M-Pesa STK Push for payment."""
    data = request.json
    
    # Validate required fields
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    phone_number = data.get('phoneNumber')
    amount = data.get('amount')
    
    if not phone_number or not amount:
        return jsonify({
            'success': False,
            'message': 'phoneNumber and amount are required'
        }), 400
    
    # Validate phone number format (254XXXXXXXXX)
    if not phone_number.startswith('254') or len(phone_number) != 12:
        return jsonify({
            'success': False,
            'message': 'Invalid phone number format. Use 254XXXXXXXXX'
        }), 400
    
    # Validate amount
    try:
        amount = int(amount)
        if amount < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'message': 'Amount must be a positive integer'
        }), 400
    
    # Check M-Pesa configuration
    if not all([CONSUMER_KEY, CONSUMER_SECRET, SHORTCODE, PASSKEY]):
        return jsonify({
            'success': False,
            'message': 'M-Pesa integration not configured on server'
        }), 500
    
    try:
        # Get access token
        access_token = get_access_token()
        
        # Generate password and timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{SHORTCODE}{PASSKEY}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        
        # Prepare request headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Prepare STK Push payload
        payload = {
            "BusinessShortCode": SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": f"{os.environ.get('BACKEND_URL', 'https://unda-youth-network-backend.onrender.com')}/api/mpesa/callback",
            "AccountReference": data.get('accountReference', 'UNDA Youth Network'),
            "TransactionDesc": data.get('transactionDesc', 'Merchandise/Membership Payment')
        }
        
        # Make STK Push request
        api_url = f"{BASE_URL[ENVIRONMENT]}/mpesa/stkpush/v1/processrequest"
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        response_data = response.json()
        
        # Check if request was successful
        if response_data.get('ResponseCode') == '0':
            return jsonify({
                'success': True,
                'message': 'STK Push sent successfully',
                'data': response_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': response_data.get('ResponseDescription', 'STK Push failed'),
                'data': response_data
            }), 400
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'M-Pesa API request failed: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


@mpesa_bp.route('/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa callback after STK Push."""
    data = request.json
    
    # Log the callback for debugging
    print("M-Pesa Callback received:", data)
    
    try:
        # Extract callback data
        result_code = data['Body']['stkCallback']['ResultCode']
        result_desc = data['Body']['stkCallback'].get('ResultDesc', 'Unknown')
        merchant_request_id = data['Body']['stkCallback'].get('MerchantRequestID')
        checkout_request_id = data['Body']['stkCallback'].get('CheckoutRequestID')
        
        if result_code == 0:
            # Payment Successful
            callback_metadata = data['Body']['stkCallback']['CallbackMetadata']['Item']
            
            # Extract details to save to your DB
            receipt = next(item['Value'] for item in callback_metadata if item['Name'] == 'MpesaReceiptNumber')
            amount = next(item['Value'] for item in callback_metadata if item['Name'] == 'Amount')
            transaction_date = next((item['Value'] for item in callback_metadata if item['Name'] == 'TransactionDate'), None)
            phone_number = next((item['Value'] for item in callback_metadata if item['Name'] == 'PhoneNumber'), None)
            
            print(f"Payment Verified! Receipt: {receipt}, Amount: {amount}")
            print(f"Transaction Date: {transaction_date}, Phone: {phone_number}")
            
            # TODO: Update your Database: set order status to 'PAID'
            # Example:
            # payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()
            # if payment:
            #     payment.status = 'PAID'
            #     payment.mpesa_receipt = receipt
            #     payment.transaction_date = transaction_date
            #     db.session.commit()
            
            return jsonify({
                'ResultCode': 0,
                'ResultDesc': 'Accepted'
            }), 200
        else:
            # Payment Failed or Cancelled by User
            print(f"Payment Failed. Result Code: {result_code}")
            print(f"Result Description: {result_desc}")
            
            # TODO: Update database to mark transaction as failed
            # payment = Payment.query.filter_by(checkout_request_id=checkout_request_id).first()
            # if payment:
            #     payment.status = 'FAILED'
            #     payment.failure_reason = result_desc
            #     db.session.commit()
            
            return jsonify({
                'ResultCode': 0,
                'ResultDesc': 'Accepted'
            }), 200
            
    except KeyError as e:
        print(f"Missing key in callback data: {str(e)}")
        print(f"Callback data: {data}")
        return jsonify({
            'ResultCode': 1,
            'ResultDesc': 'Failed to process callback'
        }), 500
    except Exception as e:
        print(f"Error processing callback: {str(e)}")
        return jsonify({
            'ResultCode': 1,
            'ResultDesc': 'Failed to process callback'
        }), 500


@mpesa_bp.route('/query/<checkout_request_id>', methods=['GET'])
@login_required
@supervisor_required
def query_stk_status(checkout_request_id):
    """Query the status of an STK Push transaction."""
    try:
        # Get access token
        access_token = get_access_token()
        
        # Generate password and timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{SHORTCODE}{PASSKEY}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        
        # Prepare request headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Prepare query payload
        payload = {
            "BusinessShortCode": SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        # Make query request
        api_url = f"{BASE_URL[ENVIRONMENT]}/mpesa/stkpushquery/v1/query"
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        return jsonify({
            'success': True,
            'data': response.json()
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': f'Query failed: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }), 500


@mpesa_bp.route('/config', methods=['GET'])
@login_required
@supervisor_required
def get_mpesa_config():
    """Get M-Pesa configuration status (for admin debugging)."""
    return jsonify({
        'success': True,
        'config': {
            'environment': ENVIRONMENT,
            'shortcode': SHORTCODE if SHORTCODE else 'Not configured',
            'consumer_key_set': bool(CONSUMER_KEY),
            'consumer_secret_set': bool(CONSUMER_SECRET),
            'passkey_set': bool(PASSKEY),
            'is_configured': all([CONSUMER_KEY, CONSUMER_SECRET, SHORTCODE, PASSKEY])
        }
    }), 200
