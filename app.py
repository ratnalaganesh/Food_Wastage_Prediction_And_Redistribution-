from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from database.db import mongo, init_db
from routes.auth_routes import auth_bp
from routes.predict_routes import predict_bp
from routes.redistribute_routes import redistribute_bp
from config import Config
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import os
from models.user import User
from bson import ObjectId

app = Flask(__name__)

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Load configuration
app.config.from_object(Config)

# Set secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'your-super-secret-key')

# Initialize extensions
mongo.init_app(app)
jwt = JWTManager(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize database
init_db(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(predict_bp, url_prefix='/predict')
app.register_blueprint(redistribute_bp, url_prefix='/api/redistribute')

# Initialize geocoder
geolocator = Nominatim(user_agent="food_wastage_prediction")

# Base wastage rates in kg per person for different event types
BASE_WASTAGE_RATES = {
    'Wedding': 0.5,
    'Birthday': 0.3,
    'Corporate': 0.4,
    'Festival': 0.6,
    'Other': 0.4
}

def get_coordinates_from_location(city, state, country):
    """Get coordinates from city, state, and country."""
    try:
        location = geolocator.geocode(f"{city}, {state}, {country}")
        if location:
            return location.latitude, location.longitude
        return None
    except Exception as e:
        print(f"Error getting coordinates: {e}")
        return None

def find_nearby_charities(latitude, longitude, radius_km=10):
    """Find nearby organizations using the coordinates."""
    # Mock data for demonstration
    mock_organizations = [
        {
            "name": "Food Bank of Hope",
            "type": "charity",
            "address": "123 Main St, City",
            "latitude": latitude + 0.01,
            "longitude": longitude + 0.01,
            "contact": "+1-234-567-8900",
            "description": "Food bank providing meals to those in need"
        },
        {
            "name": "Community Kitchen",
            "type": "charity",
            "address": "456 Oak Ave, City",
            "latitude": latitude - 0.01,
            "longitude": longitude - 0.01,
            "contact": "+1-234-567-8901",
            "description": "Community kitchen serving daily meals"
        },
        {
            "name": "Green Earth NGO",
            "type": "ngo",
            "address": "789 Pine St, City",
            "latitude": latitude + 0.02,
            "longitude": longitude - 0.02,
            "contact": "+1-234-567-8902",
            "description": "Environmental NGO working on food sustainability"
        },
        {
            "name": "Help Hands Foundation",
            "type": "ngo",
            "address": "321 Elm St, City",
            "latitude": latitude - 0.02,
            "longitude": longitude + 0.02,
            "contact": "+1-234-567-8903",
            "description": "NGO focused on food redistribution"
        },
        {
            "name": "Sunset Senior Home",
            "type": "old_age_home",
            "address": "654 Maple Ave, City",
            "latitude": latitude + 0.015,
            "longitude": longitude - 0.015,
            "contact": "+1-234-567-8904",
            "description": "Old age home with 50 residents"
        },
        {
            "name": "Golden Years Residence",
            "type": "old_age_home",
            "address": "987 Cedar St, City",
            "latitude": latitude - 0.015,
            "longitude": longitude + 0.015,
            "contact": "+1-234-567-8905",
            "description": "Old age home with 75 residents"
        }
    ]
    
    nearby_organizations = {
        "charities": [],
        "ngos": [],
        "old_age_homes": []
    }
    
    for org in mock_organizations:
        org_coords = (org["latitude"], org["longitude"])
        event_coords = (latitude, longitude)
        distance = geodesic(event_coords, org_coords).kilometers
        
        if distance <= radius_km:
            org["distance"] = round(distance, 2)
            if org["type"] == "charity":
                nearby_organizations["charities"].append(org)
            elif org["type"] == "ngo":
                nearby_organizations["ngos"].append(org)
            elif org["type"] == "old_age_home":
                nearby_organizations["old_age_homes"].append(org)
    
    # Sort each category by distance
    for category in nearby_organizations:
        nearby_organizations[category] = sorted(nearby_organizations[category], key=lambda x: x["distance"])
    
    return nearby_organizations

def predict_wastage(event_type, expected_attendees, actual_attendees):
    """
    Calculate predicted food wastage based on event type and attendance.
    
    Args:
        event_type (str): Type of the event
        expected_attendees (int): Number of expected attendees
        actual_attendees (int): Number of actual attendees
    
    Returns:
        float: Predicted food wastage in kg
    """
    # Get base wastage rate for event type
    base_rate = BASE_WASTAGE_RATES.get(event_type, BASE_WASTAGE_RATES['Other'])
    
    # Calculate attendance difference and rate
    attendance_diff = expected_attendees - actual_attendees
    
    # Calculate total wastage based on actual attendance and difference
    if attendance_diff > 0:
        # More food was prepared than needed
        wastage = (actual_attendees * base_rate) + (attendance_diff * base_rate * 1.5)
    else:
        # Less or exact food was prepared
        wastage = actual_attendees * base_rate * 0.2
    
    return round(wastage, 2)

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if not user_data:
            return None
        user = User(
            email=user_data.get('email'),
            mobile=user_data.get('mobile'),
            name=user_data.get('name')
        )
        user._id = user_data['_id']
        user.password_hash = user_data.get('password_hash')
        return user
    except Exception as e:
        print(f"Error loading user: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/prediction')
def prediction():
    return render_template('prediction.html')

@app.route('/predict')
def predict():
    return render_template('predict.html')

@app.route('/login')
def login_page():
    return render_template('auth/login.html')

@app.route('/register')
def register_page():
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(401)
def unauthorized(error):
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
