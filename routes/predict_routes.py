from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import mongo
from models.event_model import Event
from models.prediction_model import FoodWastagePrediction
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import requests
import time
from config import Config
from geopy.geocoders import Nominatim
from flask_login import login_required, current_user

predict_bp = Blueprint('predict', __name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance

def get_coordinates_from_location(location):
    try:
        # Use Nominatim (OpenStreetMap) for geocoding
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        headers = {'User-Agent': 'FoodWastageApp/1.0'}
        params = {
            'q': location,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'in'  # Limit to India
        }
        
        print(f"Making geocoding request for location: {location}")
        response = requests.get(nominatim_url, headers=headers, params=params)
        
        if not response.ok:
            print(f"Geocoding request failed with status {response.status_code}")
            return None, None
            
        data = response.json()
        print(f"Geocoding response: {data}")
        
        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            print(f"Found coordinates: {lat}, {lon}")
            return lat, lon
        else:
            print("No results found for this location")
            return None, None
            
    except Exception as e:
        print(f"Error getting coordinates: {str(e)}")
        return None, None

def search_places_overpass(latitude, longitude, radius_km):
    try:
        # Convert radius to meters
        radius_m = radius_km * 1000
        
        # Overpass API query to find charities, NGOs, and old age homes
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Query for amenities that could be charities or old age homes
        query = f"""
        [out:json][timeout:25];
        (
          // Old age homes and nursing homes
          node["social_facility"~"nursing_home|group_home|shelter|elderly_nursing_home"](around:{radius_m},{latitude},{longitude});
          way["social_facility"~"nursing_home|group_home|shelter|elderly_nursing_home"](around:{radius_m},{latitude},{longitude});
          
          // Social facilities and centers
          node["amenity"~"social_facility|social_centre|community_centre"](around:{radius_m},{latitude},{longitude});
          way["amenity"~"social_facility|social_centre|community_centre"](around:{radius_m},{latitude},{longitude});
          
          // NGOs and charities
          node["office"~"ngo|charity"](around:{radius_m},{latitude},{longitude});
          way["office"~"ngo|charity"](around:{radius_m},{latitude},{longitude});
          
          // Additional social services
          node["social_facility"="food_bank"](around:{radius_m},{latitude},{longitude});
          way["social_facility"="food_bank"](around:{radius_m},{latitude},{longitude});
        );
        out body;
        >;
        out skel qt;
        """
        
        print(f"Searching for places near {latitude}, {longitude}")
        response = requests.post(overpass_url, data=query)
        
        if not response.ok:
            print(f"Overpass request failed with status {response.status_code}")
            return []
            
        data = response.json()
        print(f"Found {len(data.get('elements', []))} elements")
        
        places = []
        seen_places = set()
        
        for element in data.get('elements', []):
            if element.get('type') in ['node', 'way']:
                place_id = element.get('id')
                if place_id not in seen_places:
                    seen_places.add(place_id)
                    
                    tags = element.get('tags', {})
                    place_lat = element.get('lat', latitude)
                    place_lon = element.get('lon', longitude)
                    
                    # Calculate distance
                    distance = haversine_distance(
                        latitude, longitude,
                        place_lat, place_lon
                    )
                    
                    if distance <= radius_km:
                        # Get a better name for the type
                        place_type = tags.get('social_facility', 
                                    tags.get('amenity',
                                    tags.get('office', 'NGO/Charity')))
                        
                        # Clean up the type name
                        place_type = place_type.replace('_', ' ').title()
                        
                        # Get the best available address
                        address_parts = []
                        if tags.get('addr:street'):
                            address_parts.append(tags.get('addr:street'))
                        if tags.get('addr:housenumber'):
                            address_parts.append(tags.get('addr:housenumber'))
                        if tags.get('addr:city'):
                            address_parts.append(tags.get('addr:city'))
                        if not address_parts and tags.get('addr:full'):
                            address_parts.append(tags.get('addr:full'))
                        
                        address = ', '.join(address_parts) if address_parts else 'Address not available'
                        
                        place_data = {
                            'name': tags.get('name', 'Unnamed Place'),
                            'address': address,
                            'phone': tags.get('phone', tags.get('contact:phone', 'Phone not available')),
                            'website': tags.get('website', tags.get('contact:website', '')),
                            'type': place_type,
                            'distance': round(distance, 1)
                        }
                        places.append(place_data)
        
        print(f"Returning {len(places)} places within {radius_km}km")
        return places
        
    except Exception as e:
        print(f"Error searching places: {str(e)}")
        return []

def predict_wastage(event_type, expected_attendees, actual_attendees):
    # Base wastage rates per person (in grams)
    base_rates = {
        'Wedding': 250,
        'Birthday': 200,
        'Corporate': 180,
        'Festival': 300,
        'Other': 220
    }
    
    # Calculate wastage based on difference in attendance
    attendance_difference = expected_attendees - actual_attendees
    
    # Base wastage calculation
    base_wastage = base_rates.get(event_type, 220)
    
    # If actual attendance is less than expected, more food waste
    if attendance_difference > 0:
        total_wastage = (base_wastage * attendance_difference) * 1.2  # 20% extra waste due to over-preparation
    else:
        # If more people attended than expected, less waste but still some
        total_wastage = base_wastage * abs(attendance_difference) * 0.3  # 30% of normal waste
    
    # Convert to kilograms and round to 2 decimal places
    total_wastage_kg = round(total_wastage / 1000, 2)
    
    return total_wastage_kg

@predict_bp.route('/', methods=['GET'])
@login_required
def predict_page():
    return render_template('predict.html')

def get_default_organizations(latitude, longitude):
    """Get default organizations when API fails"""
    return {
        'ngos': [
            {
                'name': 'Food Bank Foundation',
                'address': 'Near City Center, Main Road',
                'phone': '+91 9876543210',
                'type': 'NGO',
                'distance': 2.5,
                'capacity': '100-200 plates/day'
            },
            {
                'name': 'Helping Hands NGO',
                'address': 'Behind Railway Station',
                'phone': '+91 9876543211',
                'type': 'NGO',
                'distance': 3.2,
                'capacity': '150-300 plates/day'
            }
        ],
        'charities': [
            {
                'name': 'City Food Relief',
                'address': 'Market Area, Street 5',
                'phone': '+91 9876543212',
                'type': 'Charity',
                'distance': 1.8,
                'capacity': '200-400 plates/day'
            },
            {
                'name': 'Daily Bread Charity',
                'address': 'Hospital Road',
                'phone': '+91 9876543213',
                'type': 'Charity',
                'distance': 4.0,
                'capacity': '100-150 plates/day'
            }
        ],
        'old_age_homes': [
            {
                'name': 'Senior Care Home',
                'address': 'Peaceful Colony',
                'phone': '+91 9876543214',
                'type': 'Old Age Home',
                'distance': 2.1,
                'capacity': '50-100 plates/day'
            },
            {
                'name': 'Golden Years Home',
                'address': 'Garden Road',
                'phone': '+91 9876543215',
                'type': 'Old Age Home',
                'distance': 3.5,
                'capacity': '75-125 plates/day'
            }
        ]
    }

@predict_bp.route('/predict', methods=['POST'])
@login_required
def predict():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        event_type = data.get('event_type')
        plates = data.get('plates')
        location = data.get('location')
        
        if not all([event_type, plates, location]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Get coordinates based on location type
        try:
            if 'latitude' in location and 'longitude' in location:
                # Using current location
                latitude = float(location['latitude'])
                longitude = float(location['longitude'])
            else:
                # Using manual location
                location_str = f"{location.get('city', '')}, {location.get('state', '')}, {location.get('country', 'India')}"
                coords = get_coordinates_from_location(location_str)
                if not coords:
                    return jsonify({'error': 'Could not find coordinates for the given location'}), 400
                latitude, longitude = coords
                
            # Calculate food wastage prediction
            wastage_percentage = calculate_wastage_percentage(event_type)
            estimated_wastage = round(plates * wastage_percentage)
            recommended_plates = plates - estimated_wastage
            
            # Try to get organizations from API, fallback to default if fails
            try:
                nearby = search_places_overpass(latitude, longitude, radius_km=5)
                if not nearby:
                    raise Exception("No organizations found")
                    
                organizations = {
                    'ngos': [],
                    'charities': [],
                    'old_age_homes': []
                }
                
                for place in nearby:
                    if 'ngo' in place['type'].lower():
                        organizations['ngos'].append(place)
                    elif 'charity' in place['type'].lower():
                        organizations['charities'].append(place)
                    elif 'home' in place['type'].lower() or 'elderly' in place['type'].lower():
                        organizations['old_age_homes'].append(place)
            except Exception as e:
                print(f"Error fetching organizations: {str(e)}")
                organizations = get_default_organizations(latitude, longitude)
            
            return jsonify({
                'recommended_plates': recommended_plates,
                'estimated_wastage': estimated_wastage,
                'nearby_organizations': organizations,
                'message': 'Using default organizations as live data could not be fetched' if not nearby else None
            })
            
        except Exception as e:
            return jsonify({'error': f'Location error: {str(e)}'}), 400
            
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

def calculate_wastage_percentage(event_type):
    """Calculate the expected wastage percentage based on event type."""
    wastage_rates = {
        'Wedding': 0.15,  # 15% wastage
        'Corporate': 0.10,  # 10% wastage
        'Birthday': 0.08,  # 8% wastage
        'Festival': 0.20,  # 20% wastage
        'Other': 0.12  # 12% wastage
    }
    return wastage_rates.get(event_type, wastage_rates['Other'])

@predict_bp.route('/create-event', methods=['POST'])
@jwt_required()
def create_event():
    """Create a new event with food items"""
    data = request.get_json()
    
    # Validate input data
    required_fields = ['event_name', 'event_type', 'date', 'location', 
                      'expected_attendees', 'food_items']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
        
    # Create event
    event_data = {
        'user_id': get_jwt_identity(),
        'event_name': data['event_name'],
        'event_type': data['event_type'],
        'date': data['date'],
        'location': data['location'],
        'expected_attendees': data['expected_attendees'],
        'food_items': data['food_items'],
        'status': 'pending',
        'created_at': datetime.utcnow()
    }
    
    # Get wastage predictions
    predictor = FoodWastagePrediction(
        event_type=data['event_type'],
        attendees=data['expected_attendees'],
        food_items=data['food_items']
    )
    predictions = predictor.predict_wastage()
    event_data['wastage_predictions'] = predictions
    
    # Save event to database
    result = mongo.db.events.insert_one(event_data)
    event_data['_id'] = result.inserted_id
    
    return jsonify({
        'message': 'Event created successfully',
        'event': event_data
    })

@predict_bp.route('/update-actual-wastage/<event_id>', methods=['POST'])
@jwt_required()
def update_actual_wastage(event_id):
    """Update actual food wastage for an event"""
    data = request.get_json()
    
    # Validate input
    if 'wasted_food' not in data:
        return jsonify({'error': 'Missing wasted food data'}), 400
        
    # Update event with actual wastage
    result = mongo.db.events.update_one(
        {'_id': event_id},
        {
            '$set': {
                'wasted_food': data['wasted_food'],
                'status': 'completed',
                'updated_at': datetime.utcnow()
            }
        }
    )
    
    if result.modified_count == 0:
        return jsonify({'error': 'Event not found'}), 404
        
    return jsonify({
        'message': 'Actual wastage updated successfully'
    })

@predict_bp.route('/event/<event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    """Get event details including predictions and actual wastage"""
    event = mongo.db.events.find_one({'_id': event_id})
    if not event:
        return jsonify({'error': 'Event not found'}), 404
        
    return jsonify(event)

@predict_bp.route('/events', methods=['GET'])
@jwt_required()
def get_user_events():
    """Get all events for the current user"""
    user_id = get_jwt_identity()
    events = list(mongo.db.events.find({'user_id': user_id}))
    
    return jsonify({
        'events': events
    })

@predict_bp.route('/add-charity', methods=['POST'])
def add_charity():
    try:
        data = request.get_json()
        required_fields = ['name', 'address', 'phone', 'email', 'latitude', 'longitude', 'capacity']
        
        if not all(k in data for k in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Add charity to database
        result = mongo.db.charities.insert_one({
            'name': data['name'],
            'address': data['address'],
            'phone': data['phone'],
            'email': data['email'],
            'latitude': float(data['latitude']),
            'longitude': float(data['longitude']),
            'capacity': int(data['capacity']),
            'rating': float(data.get('rating', 5.0)),
            'created_at': datetime.utcnow()
        })
        
        return jsonify({
            'message': 'Charity added successfully',
            'charity_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"Add charity error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@predict_bp.route('/find-charities', methods=['GET', 'POST'])
def find_charities():
    try:
        max_distance = 20  # Maximum distance in kilometers
        
        if request.method == 'GET':
            location = request.args.get('location')
            if not location:
                return jsonify({'error': 'Location is required'}), 400
            
            print(f"Searching for location: {location}")    
            latitude, longitude = get_coordinates_from_location(location)
            
            if not latitude or not longitude:
                return jsonify({
                    'error': 'Could not find coordinates for the given location',
                    'possible_reasons': [
                        'Location not found',
                        'Invalid location name',
                        'Network error'
                    ]
                }), 400
                
            print(f"Found coordinates: {latitude}, {longitude}")
        else:
            data = request.get_json()
            if not data or 'latitude' not in data or 'longitude' not in data:
                return jsonify({'error': 'Coordinates are required'}), 400
            
            latitude = float(data['latitude'])
            longitude = float(data['longitude'])
        
        # Search for places using OpenStreetMap
        places = search_places_overpass(latitude, longitude, max_distance)
        
        # Sort by distance
        places.sort(key=lambda x: x['distance'])
        
        return jsonify({
            'charities': places,
            'message': f'Found {len(places)} places within {max_distance}km'
        }), 200
        
    except Exception as e:
        print(f"Find charities error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@predict_bp.route('/confirm-donation', methods=['POST'])
@login_required
def confirm_donation():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['organization', 'plateCount', 'pickupTime', 'notes']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Create donation record
        donation = {
            'user_id': str(current_user._id),
            'user_name': current_user.name,
            'user_email': current_user.email,
            'user_phone': current_user.mobile,
            'organization_name': data['organization']['name'],
            'organization_address': data['organization']['address'],
            'organization_phone': data['organization']['phone'],
            'plate_count': int(data['plateCount']),
            'pickup_time': data['pickupTime'],
            'notes': data['notes'],
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
        
        # Save to database
        result = mongo.db.donations.insert_one(donation)
        
        # In a real application, you would send notifications here
        # For now, we'll just return a success message
        return jsonify({
            'message': 'Donation confirmed successfully!',
            'donation_id': str(result.inserted_id),
            'next_steps': [
                'The organization will be notified immediately',
                'You will receive a confirmation SMS/email shortly',
                'The organization\'s agent will contact you at your registered number',
                'Please keep the food ready for pickup at the specified time'
            ]
        })
        
    except Exception as e:
        print(f"Error confirming donation: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
