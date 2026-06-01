# M-Pesa Integration Setup Guide

## Current Issues Fixed

### 1. M-Pesa 500 Error (Fixed)

- **Issue**: Server was sending improperly formatted payload to Safaricom API
- **Fix**: All payload fields are now properly typed (strings, integers) and truncated to Safaricom's limits:
  - `AccountReference`: Max 20 characters
  - `TransactionDesc`: Max 13 characters
  - Phone numbers: Ensured 254XXXXXXXXX format (12 digits)

### 2. Better Error Handling (Added)

- Added validation for phone numbers before sending to M-Pesa
- Added validation for amount
- Improved error logging with detailed response information
- Better handling of 400 and 500 HTTP errors

## Required Setup Steps

### 1. Update Callback URL

Your current callback URL is set to a placeholder: `https://your-ngrok-url.ngrok.io/api/mpesa/callback`

**For Local Development:**

1. Install ngrok (if not already installed):

   ```bash
   choco install ngrok
   # OR download from https://ngrok.com/download
   ```

2. Start ngrok tunnel:

   ```bash
   ngrok http 5000
   ```

3. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

4. Update `.env` file:

   ```
   MPESA_CALLBACK_URL=https://abc123.ngrok.io/api/mpesa/callback
   ```

5. Restart your Flask application

**For Production:**

- Use your production domain URL: `https://yourdomain.com/api/mpesa/callback`

### 2. Verify M-Pesa Credentials

Your credentials appear to be for the Safaricom sandbox. Verify they are current:

1. Visit: https://developer.safaricom.co.ke/
2. Log in to your account
3. Navigate to your app
4. Verify/update:
   - Consumer Key
   - Consumer Secret
   - Business Shortcode (should match passkey)
   - Passkey

**Important**: Sandbox credentials expire periodically. If you're getting authentication errors, regenerate them.

### 3. Common M-Pesa Error Codes

- **500 Internal Server Error**: Invalid credentials, malformed payload, or expired credentials
- **400 Bad Request**: Missing required fields or invalid data format
- **401 Unauthorized**: Invalid or expired access token
- **403 Forbidden**: Invalid credentials or IP not whitelisted

### 4. Testing

After fixing the callback URL:

1. Make a test booking
2. Initiate payment with a valid Safaricom number (format: 254712345678)
3. Check logs for any errors:
   ```powershell
   Get-Content logs\easypark.log -Tail 50
   ```

### 5. Phone Number Format

The system now validates phone numbers strictly:

- Must start with `254`
- Must be exactly 12 digits
- Example valid number: `254712345678`

Front-end accepts:

- `07XXXXXXXX` → converts to `254712345678`
- `2547XXXXXXXX` → already correct
- `+2547XXXXXXXX` → strips `+`

## Troubleshooting

### Still getting 500 errors?

1. **Check credentials are current**: Safaricom sandbox credentials expire
2. **Verify shortcode matches**: Business shortcode in .env must match the one used to generate the passkey
3. **Check amount**: Must be a positive number, system converts to integer
4. **Monitor logs**: Detailed error info is now logged

### Callback not working?

1. Ensure ngrok is running (for local dev)
2. Check callback URL is accessible: `curl https://your-url.ngrok.io/api/mpesa/callback`
3. Verify firewall isn't blocking Safaricom's IPs
4. Check callback endpoint in logs when M-Pesa sends response

### Phone number rejected?

- Use Safaricom test numbers for sandbox: `254708374149`, `254711222333`
- Ensure format is `254XXXXXXXXX` (12 digits total)

## Additional Resources

- [Safaricom Daraja API Documentation](https://developer.safaricom.co.ke/Documentation)
- [M-Pesa STK Push API](https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate)
- [Ngrok Documentation](https://ngrok.com/docs)
