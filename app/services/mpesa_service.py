"""
M-Pesa Daraja API Service
Handles STK Push payment integration for EasyPark
"""
import os
import json
import requests
from datetime import datetime
from base64 import b64encode
from flask import current_app


class MpesaService:
    """Service class for M-Pesa Daraja API integration"""

    def __init__(self):
        """Initialize M-Pesa service with credentials from environment"""
        self.consumer_key = os.getenv('MPESA_CONSUMER_KEY')
        self.consumer_secret = os.getenv('MPESA_CONSUMER_SECRET')
        self.business_shortcode = os.getenv('MPESA_SHORTCODE')
        self.passkey = os.getenv('MPESA_PASSKEY')
        self.callback_url = os.getenv('MPESA_CALLBACK_URL')

        # API endpoints (sandbox)
        self.auth_url = os.getenv(
            'MPESA_AUTH_URL', 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials')
        self.stk_push_url = os.getenv(
            'MPESA_STK_PUSH_URL', 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest')
        self.query_url = os.getenv(
            'MPESA_QUERY_URL', 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query')

        self._validate_credentials()

    def _validate_credentials(self):
        """Validate that all required credentials are set"""
        required = {
            'MPESA_CONSUMER_KEY': self.consumer_key,
            'MPESA_CONSUMER_SECRET': self.consumer_secret,
            'MPESA_SHORTCODE': self.business_shortcode,
            'MPESA_PASSKEY': self.passkey,
            'MPESA_CALLBACK_URL': self.callback_url
        }

        missing = [key for key, value in required.items() if not value]
        if missing:
            current_app.logger.warning(
                f"Missing M-Pesa credentials: {', '.join(missing)}")

    def get_access_token(self):
        """
        Get OAuth access token from M-Pesa API

        Returns:
            str: Access token if successful, None otherwise
        """
        try:
            # Create basic auth credentials
            credentials = b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode('utf-8')

            headers = {
                'Authorization': f'Basic {credentials}'
            }

            response = requests.get(self.auth_url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            access_token = data.get('access_token')

            if access_token:
                current_app.logger.info(
                    "M-Pesa access token obtained successfully")
                return access_token
            else:
                current_app.logger.error("No access token in M-Pesa response")
                return None

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"M-Pesa auth error: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(
                f"Unexpected error getting M-Pesa token: {str(e)}")
            return None

    def _generate_password(self):
        """
        Generate password for STK Push request

        Returns:
            tuple: (password, timestamp)
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.business_shortcode}{self.passkey}{timestamp}"
        password = b64encode(password_str.encode()).decode('utf-8')
        return password, timestamp

    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """
        Initiate STK Push payment request

        Args:
            phone_number (str): Customer phone number (format: 254712345678)
            amount (float): Amount to charge
            account_reference (str): Account reference (e.g., booking reference)
            transaction_desc (str): Transaction description

        Returns:
            dict: Response data with keys:
                - success (bool): Whether request was successful
                - checkout_request_id (str): Checkout request ID
                - merchant_request_id (str): Merchant request ID
                - response_code (str): Response code from M-Pesa
                - response_description (str): Response description
                - customer_message (str): Message for customer
                - error (str): Error message if failed
        """
        try:
            # Get access token
            access_token = self.get_access_token()
            if not access_token:
                return {
                    'success': False,
                    'error': 'Failed to get M-Pesa access token'
                }

            # Generate password and timestamp
            password, timestamp = self._generate_password()

            # Prepare request payload
            payload = {
                'BusinessShortCode': self.business_shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(amount),  # M-Pesa expects integer
                'PartyA': phone_number,
                'PartyB': self.business_shortcode,
                'PhoneNumber': phone_number,
                'CallBackURL': self.callback_url,
                'AccountReference': account_reference,
                'TransactionDesc': transaction_desc
            }

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            current_app.logger.info(
                f"Initiating STK Push for {phone_number}, amount: {amount}")

            response = requests.post(
                self.stk_push_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # Check response code
            response_code = data.get('ResponseCode', '')
            if response_code == '0':
                current_app.logger.info(
                    f"STK Push initiated successfully: {data.get('CheckoutRequestID')}"
                )
                return {
                    'success': True,
                    'checkout_request_id': data.get('CheckoutRequestID'),
                    'merchant_request_id': data.get('MerchantRequestID'),
                    'response_code': response_code,
                    'response_description': data.get('ResponseDescription'),
                    'customer_message': data.get('CustomerMessage', 'Payment request sent to your phone')
                }
            else:
                current_app.logger.warning(
                    f"STK Push failed: {data.get('ResponseDescription')}")
                return {
                    'success': False,
                    'error': data.get('ResponseDescription', 'Payment request failed'),
                    'response_code': response_code
                }

        except requests.exceptions.RequestException as e:
            current_app.logger.error(
                f"M-Pesa STK Push request error: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            current_app.logger.error(f"Unexpected error in STK Push: {str(e)}")
            return {
                'success': False,
                'error': 'An unexpected error occurred'
            }

    def query_payment_status(self, checkout_request_id):
        """
        Query the status of an STK Push transaction

        Args:
            checkout_request_id (str): Checkout request ID from STK Push

        Returns:
            dict: Response data with keys:
                - success (bool): Whether query was successful
                - result_code (str): Result code (0 = success)
                - result_desc (str): Result description
                - status (str): Payment status (COMPLETED, FAILED, PENDING)
                - error (str): Error message if failed
        """
        try:
            # Get access token
            access_token = self.get_access_token()
            if not access_token:
                return {
                    'success': False,
                    'error': 'Failed to get M-Pesa access token'
                }

            # Generate password and timestamp
            password, timestamp = self._generate_password()

            # Prepare request payload
            payload = {
                'BusinessShortCode': self.business_shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id
            }

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            response = requests.post(
                self.query_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            result_code = data.get('ResultCode', '')

            # Determine status based on result code
            if result_code == '0':
                status = 'COMPLETED'
            elif result_code == '1032':
                status = 'CANCELLED'
            elif result_code in ['1', '1037']:
                status = 'FAILED'
            elif data.get('ResponseCode') == '0':
                status = 'PENDING'
            else:
                status = 'FAILED'

            return {
                'success': True,
                'result_code': result_code,
                'result_desc': data.get('ResultDesc', ''),
                'status': status,
                'response_code': data.get('ResponseCode', ''),
                'response_description': data.get('ResponseDescription', '')
            }

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"M-Pesa query error: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            current_app.logger.error(
                f"Unexpected error querying payment: {str(e)}")
            return {
                'success': False,
                'error': 'An unexpected error occurred'
            }

    def process_callback(self, callback_data):
        """
        Process M-Pesa callback data

        Args:
            callback_data (dict): Callback data from M-Pesa

        Returns:
            dict: Processed payment information with keys:
                - success (bool): Whether payment was successful
                - result_code (int): Result code from M-Pesa
                - result_desc (str): Result description
                - merchant_request_id (str): Merchant request ID
                - checkout_request_id (str): Checkout request ID
                - amount (float): Amount paid
                - mpesa_receipt_number (str): M-Pesa receipt number
                - transaction_date (datetime): Transaction date
                - phone_number (str): Phone number used
        """
        try:
            body = callback_data.get('Body', {})
            stk_callback = body.get('stkCallback', {})

            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc', '')
            merchant_request_id = stk_callback.get('MerchantRequestID')
            checkout_request_id = stk_callback.get('CheckoutRequestID')

            result = {
                'success': result_code == 0,
                'result_code': result_code,
                'result_desc': result_desc,
                'merchant_request_id': merchant_request_id,
                'checkout_request_id': checkout_request_id
            }

            # Extract callback metadata if payment was successful
            if result_code == 0:
                callback_metadata = stk_callback.get('CallbackMetadata', {})
                items = callback_metadata.get('Item', [])

                metadata = {}
                for item in items:
                    name = item.get('Name')
                    value = item.get('Value')
                    metadata[name] = value

                result.update({
                    'amount': metadata.get('Amount'),
                    'mpesa_receipt_number': metadata.get('MpesaReceiptNumber'),
                    'transaction_date': self._parse_mpesa_date(metadata.get('TransactionDate')),
                    'phone_number': metadata.get('PhoneNumber')
                })

            return result

        except Exception as e:
            current_app.logger.error(
                f"Error processing M-Pesa callback: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to process callback data'
            }

    def _parse_mpesa_date(self, date_value):
        """
        Parse M-Pesa date format (YYYYMMDDHHMMSS) to datetime

        Args:
            date_value: Date value from M-Pesa (can be int or str)

        Returns:
            datetime: Parsed datetime object or None
        """
        try:
            if not date_value:
                return None

            date_str = str(date_value)
            return datetime.strptime(date_str, '%Y%m%d%H%M%S')
        except Exception as e:
            current_app.logger.error(
                f"Error parsing M-Pesa date {date_value}: {str(e)}")
            return None
