import requests
import json

# Test charities data
test_charities = [
    {
        "name": "Food Bank India",
        "address": "123 Main Street, Mumbai, Maharashtra",
        "phone": "+91 9876543210",
        "email": "foodbank@example.com",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "capacity": 1000,
        "rating": 4.5
    },
    {
        "name": "Helping Hands Foundation",
        "address": "456 Park Avenue, Delhi, Delhi",
        "phone": "+91 9876543211",
        "email": "helpinghands@example.com",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "capacity": 800,
        "rating": 4.8
    },
    {
        "name": "Share Food Trust",
        "address": "789 Lake Road, Bangalore, Karnataka",
        "phone": "+91 9876543212",
        "email": "sharefood@example.com",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "capacity": 1200,
        "rating": 4.2
    },
    {
        "name": "Feed the Hungry",
        "address": "321 Beach Road, Chennai, Tamil Nadu",
        "phone": "+91 9876543213",
        "email": "feedhungry@example.com",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "capacity": 900,
        "rating": 4.6
    },
    {
        "name": "Food for All",
        "address": "654 Hill Street, Kolkata, West Bengal",
        "phone": "+91 9876543214",
        "email": "foodforall@example.com",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "capacity": 1100,
        "rating": 4.7
    }
]

def add_test_charities():
    base_url = "http://localhost:5000/api/predict/add-charity"
    
    for charity in test_charities:
        try:
            response = requests.post(base_url, json=charity)
            if response.status_code == 201:
                print(f"Successfully added charity: {charity['name']}")
            else:
                print(f"Failed to add charity {charity['name']}: {response.text}")
        except Exception as e:
            print(f"Error adding charity {charity['name']}: {str(e)}")

if __name__ == "__main__":
    add_test_charities() 