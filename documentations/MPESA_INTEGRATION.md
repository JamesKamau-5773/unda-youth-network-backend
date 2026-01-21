````markdown
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

... (content preserved) ...

````