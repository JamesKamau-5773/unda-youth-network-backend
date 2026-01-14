import base64
from datetime import datetime
import requests
from utils.http import get_session, request_with_timeout
from utils.circuit import CircuitBreaker, circuit
from utils.endpoint_guard import endpoint_guard
from utils.idempotency import reserve_key, get_key, update_key, make_key_from_args
from flask import Blueprint, request, jsonify
from flask_login import login_required
from flask_login import current_user
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

# Allow local test runs to short-circuit external M-Pesa calls
MPESA_MOCK = os.environ.get('MPESA_MOCK', 'False') == 'True'

# Base URLs based on environment
BASE_URL = {
    'sandbox': 'https://sandbox.safaricom.co.ke',
    'production': 'https://api.safaricom.co.ke'
}

# Shared session with retries
_session = get_session()

# Circuit breaker for external M-Pesa calls
_mpesa_cb = CircuitBreaker(fail_max=4, reset_timeout=30)


def get_access_token():
    """Get OAuth access token from M-Pesa API."""
    if MPESA_MOCK:
        return 'fake-access-token'
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        raise ValueError("M-Pesa credentials not configured. Set MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET.")
    api_url = f"{BASE_URL[ENVIRONMENT]}/oauth/v1/generate?grant_type=client_credentials"
    try:
        resp = request_with_timeout(_session, 'GET', api_url, timeout=10, auth=(CONSUMER_KEY, CONSUMER_SECRET))
        resp.raise_for_status()
        return resp.json().get('access_token')
    except Exception as e:
        raise Exception(f"Failed to get M-Pesa access token: {str(e)}")


@mpesa_bp.route('/checkout', methods=['POST'])
@login_required
@endpoint_guard(cb=_mpesa_cb, timeout=12)
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
    
    # Idempotency handling: prefer client-provided Idempotency-Key header
    idem_key = request.headers.get('Idempotency-Key') or data.get('idempotencyKey')
    if not idem_key:
        # Fallback deterministic key so repeated clicks produce same key
        user_id = getattr(current_user, 'id', 'anon')
        account_ref = data.get('accountReference', 'UNDA Youth Network')
        idem_key = make_key_from_args(user_id, phone_number, amount, account_ref)

    # If a record already exists and succeeded, return the stored response
    existing = get_key(idem_key)
    if existing:
        status = existing.get('status')
        if status == 'success':
            return jsonify({'success': True, 'message': 'STK Push already processed', 'data': existing.get('response')}), 200
        if status == 'pending':
            return jsonify({'success': False, 'message': 'Payment is already being processed'}), 202
        # if failed, fall through and allow retry which will attempt to reserve again

    # Try to reserve the idempotency key — only one process will win
    reserved = reserve_key(idem_key, meta={'phone': phone_number, 'amount': amount})
    if not reserved:
        # Another worker/process reserved it; return pending
        return jsonify({'success': False, 'message': 'Payment is already being processed'}), 202

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
        
        # Make STK Push request with circuit breaker protection
        @circuit(_mpesa_cb)
        def do_request():
            # If MPESA_MOCK is enabled, return a fake successful response
            if MPESA_MOCK:
                return {
                    'ResponseCode': '0',
                    'CheckoutRequestID': 'MOCK_CHECKOUT_123',
                    'ResponseDescription': 'Mock STK Push accepted'
                }
            api_url = f"{BASE_URL[ENVIRONMENT]}/mpesa/stkpush/v1/processrequest"
            resp = request_with_timeout(_session, 'POST', api_url, timeout=10, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

        try:
            response_data = do_request()
        except RuntimeError:
            # Mark pending -> failed temporarily so clients can retry later
            update_key(idem_key, status='failed', response={'error': 'service_unavailable'})
            return jsonify({'success': False, 'message': 'M-Pesa service temporarily unavailable.'}), 503
        except Exception as e:
            update_key(idem_key, status='failed', response={'error': str(e)})
            return jsonify({'success': False, 'message': f'M-Pesa API request failed: {str(e)}'}), 500

        # Persist success response into idempotency store so replays are safe
        if response_data.get('ResponseCode') == '0':
            update_key(idem_key, status='success', response=response_data, meta={'checkout_request_id': response_data.get('CheckoutRequestID')})
            return jsonify({'success': True, 'message': 'STK Push sent successfully', 'data': response_data}), 200

        update_key(idem_key, status='failed', response=response_data)
        return jsonify({'success': False, 'message': response_data.get('ResponseDescription', 'STK Push failed'), 'data': response_data}), 400
            
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
