import requests
import json

BASE_URL = 'http://localhost:5000/api'

def test_register():
    url = f'{BASE_URL}/auth/register'
    data = {
        'email': 'test@example.com',
        'mobile': '1234567890',
        'password': 'testpass123'
    }
    response = requests.post(url, json=data)
    print('Register Response:', response.status_code)
    print(response.json())
    return response.json().get('token')

def test_login():
    url = f'{BASE_URL}/auth/login'
    data = {
        'email': 'test@example.com',
        'password': 'testpass123'
    }
    response = requests.post(url, json=data)
    print('Login Response:', response.status_code)
    print(response.json())
    return response.json().get('token')

def test_prediction(token):
    url = f'{BASE_URL}/predict/predict-wastage'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
        'event_type': 'Wedding',
        'expected_attendees': 1000,
        'actual_attendees': 800,
        'food_items': [
            {
                'name': 'Main Course',
                'quantity': 1000,
                'unit': 'servings'
            }
        ]
    }
    response = requests.post(url, json=data, headers=headers)
    print('Prediction Response:', response.status_code)
    print(response.json())

if __name__ == '__main__':
    # Try to register (might fail if user exists)
    token = test_register()
    
    # If registration fails, try login
    if not token:
        token = test_login()
    
    # Test prediction with the token
    if token:
        test_prediction(token)
    else:
        print("Failed to get authentication token") 