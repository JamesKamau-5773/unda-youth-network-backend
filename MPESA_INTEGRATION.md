# M-Pesa Integration Guide

## Overview

M-Pesa STK Push integration has been implemented for the UNDA Youth Network backend to enable mobile payments for merchandise and membership fees.

## Endpoints

### 1. POST /api/mpesa/checkout
Initiates an M-Pesa STK Push to the user's phone.

**Authentication:** Required (login_required)

**Request Body:**
```json
{
  "phoneNumber": "254712345678",
  "amount": 100,
  "accountReference": "UNDA Youth Network",
  "transactionDesc": "Merchandise/Membership Payment"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "STK Push sent successfully",
  "data": {
    "MerchantRequestID": "29115-34620561-1",
    "CheckoutRequestID": "ws_CO_191220191020363925",
    "ResponseCode": "0",
    "ResponseDescription": "Success. Request accepted for processing",
    "CustomerMessage": "Success. Request accepted for processing"
  }
}
```

### 2. POST /api/mpesa/callback
Handles callbacks from M-Pesa after payment completion.

**Authentication:** None (called by M-Pesa)

**Note:** This endpoint is called automatically by Safaricom's M-Pesa API.

### 3. GET /api/mpesa/query/<checkout_request_id>
Query the status of an STK Push transaction.

**Authentication:** Required (supervisor_required)

**Response:**
```json
{
  "success": true,
  "data": {
    "ResponseCode": "0",
    "ResultCode": "0",
    "ResultDesc": "The service request is processed successfully."
  }
}
```

### 4. GET /api/mpesa/config
Get M-Pesa configuration status (for debugging).

**Authentication:** Required (supervisor_required)

**Response:**
```json
{
  "success": true,
  "config": {
    "environment": "sandbox",
    "shortcode": "174379",
    "consumer_key_set": true,
    "consumer_secret_set": true,
    "passkey_set": true,
    "is_configured": true
  }
}
```

## Environment Variables

Add these to your `.env` file or Render environment variables:

```bash
# M-Pesa Sandbox Credentials (for testing)
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_SHORTCODE=174379
MPESA_PASSKEY=your_passkey

# M-Pesa Environment (sandbox or production)
MPESA_ENVIRONMENT=sandbox

# Backend URL for callbacks
BACKEND_URL=https://unda-youth-network-backend.onrender.com
```

## Getting M-Pesa Credentials

### Sandbox (Testing)
1. Go to https://developer.safaricom.co.ke/
2. Sign up/Login
3. Create a new app
4. Select "Lipa Na M-Pesa Sandbox"
5. Copy your credentials:
   - Consumer Key
   - Consumer Secret
   - Test Credentials (shortcode and passkey)

### Production
1. Contact Safaricom to register your business
2. Get production credentials
3. Set `MPESA_ENVIRONMENT=production`
4. Update credentials in environment variables

## Phone Number Format

Phone numbers must be in the format: `254XXXXXXXXX`
- Start with country code (254 for Kenya)
- No spaces, dashes, or plus sign
- Example: 254712345678

## Testing

### Test with Sandbox
1. Use test credentials from Safaricom Developer Portal
2. Use test phone numbers provided by Safaricom
3. Test STK Push will appear on the test phone

### Example Request (curl)
```bash
curl -X POST https://unda-youth-network-backend.onrender.com/api/mpesa/checkout \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_cookie" \
  -d '{
    "phoneNumber": "254712345678",
    "amount": 100
  }'
```

### Example Request (JavaScript)
```javascript
const response = await fetch('https://unda-youth-network-backend.onrender.com/api/mpesa/checkout', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  credentials: 'include', // Include cookies for authentication
  body: JSON.stringify({
    phoneNumber: '254712345678',
    amount: 100
  })
});

const data = await response.json();
console.log(data);
```

## Error Handling

### Common Errors

**400 Bad Request**
- Missing required fields (phoneNumber, amount)
- Invalid phone number format
- Invalid amount (must be positive integer)

**500 Internal Server Error**
- M-Pesa credentials not configured
- M-Pesa API request failed
- Network timeout

### Error Response Format
```json
{
  "success": false,
  "message": "Error description"
}
```

## Security

1. Callbacks are public but validate data before processing
2. Checkout requires user authentication
3. Query endpoint requires supervisor role
4. CORS enabled for frontend integration
5. All M-Pesa requests use HTTPS

## Production Checklist

Before deploying to production:

- [ ] Get production M-Pesa credentials from Safaricom
- [ ] Update environment variables with production credentials
- [ ] Set `MPESA_ENVIRONMENT=production`
- [ ] Test callback URL is accessible (https)
- [ ] Implement transaction logging in database
- [ ] Add retry logic for failed requests
- [ ] Set up monitoring for failed transactions
- [ ] Implement transaction reconciliation
- [ ] Add proper error tracking (Sentry already configured)

## Database Integration (Optional Enhancement)

Consider creating a Payment model to track transactions:

```python
class Payment(db.Model):
    payment_id = db.Column(db.Integer, primary_key=True)
    merchant_request_id = db.Column(db.String(100))
    checkout_request_id = db.Column(db.String(100), unique=True)
    phone_number = db.Column(db.String(15))
    amount = db.Column(db.Integer)
    transaction_id = db.Column(db.String(50))
    status = db.Column(db.String(20))  # pending, success, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

## Support

For M-Pesa integration issues:
- Safaricom Developer Portal: https://developer.safaricom.co.ke/
- M-Pesa API Documentation: https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate
