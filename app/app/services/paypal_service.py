"""
PayPal Payment Service
Handles PayPal payment processing for ethics assessments
"""

import requests
import base64
from flask import current_app
import json


class PayPalService:
    """Service for PayPal payment processing"""
    
    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.base_url = "https://api-m.sandbox.paypal.com"  # Sandbox URL
        # Use production URL in production: https://api-m.paypal.com
    
    def initialize(self):
        """Initialize PayPal credentials from app config"""
        self.client_id = current_app.config.get('PAYPAL_CLIENT_ID')
        self.client_secret = current_app.config.get('PAYPAL_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("PayPal credentials not configured")
    
    def get_access_token(self):
        """Get OAuth access token from PayPal"""
        if not self.client_id or not self.client_secret:
            self.initialize()
        
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {'grant_type': 'client_credentials'}
        
        response = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            raise Exception(f"Failed to get PayPal access token: {response.text}")
    
    def create_order(self, amount, currency='USD', description='Ethics Assessment'):
        """Create a PayPal order"""
        access_token = self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        order_data = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {
                    'currency_code': currency,
                    'value': f'{amount:.2f}'
                },
                'description': description
            }],
            'application_context': {
                'return_url': f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/api/ethics/payment-success",
                'cancel_url': f"{current_app.config.get('BASE_URL', 'http://localhost:5000')}/api/ethics/payment-cancel",
                'brand_name': 'AIACMate Pro',
                'landing_page': 'BILLING',
                'user_action': 'PAY_NOW'
            }
        }
        
        response = requests.post(
            f"{self.base_url}/v2/checkout/orders",
            headers=headers,
            json=order_data
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create PayPal order: {response.text}")
    
    def capture_order(self, order_id):
        """Capture a PayPal order"""
        access_token = self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.post(
            f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
            headers=headers
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to capture PayPal order: {response.text}")
    
    def get_order(self, order_id):
        """Get order details"""
        access_token = self.get_access_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(
            f"{self.base_url}/v2/checkout/orders/{order_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get PayPal order: {response.text}")
