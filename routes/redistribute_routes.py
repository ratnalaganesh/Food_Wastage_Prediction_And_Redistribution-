from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import mongo
from models.event_model import Event
from models.charity_model import Charity
from datetime import datetime
import requests
from math import radians, sin, cos, sqrt, atan2

redistribute_bp = Blueprint('redistribute', __name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth"""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance

def get_coordinates_from_location(location):
    """Get coordinates from location name using Nominatim"""
    try:
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        headers = {'User-Agent': 'FoodWastageApp/1.0'}
        params = {
            'q': location,
            'format': 'json',
            'limit': 1
        }
        
        response = requests.get(nominatim_url, headers=headers, params=params)
        
        if not response.ok:
            return None, None
            
        data = response.json()
        
        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
        return None, None
            
    except Exception as e:
        print(f"Error getting coordinates: {str(e)}")
        return None, None

@redistribute_bp.route('/', methods=['GET'])
def get_locations():
    locations = [{"name": "Charity A", "address": "123 Street"},
                 {"name": "Charity B", "address": "456 Avenue"}]
    return jsonify({"locations": locations})

@redistribute_bp.route('/select-charity', methods=['POST'])
@jwt_required()
def select_charity():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if not all(k in data for k in ['charity_id', 'event_id']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    event = Event.find_by_id(data['event_id'])
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    charity = Charity.find_by_id(data['charity_id'])
    if not charity:
        return jsonify({'error': 'Charity not found'}), 404
    
    # Update event status and assign charity
    mongo.db.events.update_one(
        {'_id': event['_id']},
        {
            '$set': {
                'status': 'assigned',
                'charity_id': data['charity_id'],
                'assigned_at': datetime.utcnow()
            }
        }
    )
    
    # Update charity's total donations
    mongo.db.charities.update_one(
        {'_id': charity['_id']},
        {'$inc': {'total_donations': 1}}
    )
    
    return jsonify({
        'message': 'Charity assigned successfully',
        'event': event,
        'charity': charity
    }), 200

@redistribute_bp.route('/my-donations', methods=['GET'])
@jwt_required()
def get_my_donations():
    user_id = get_jwt_identity()
    events = Event.find_by_user_id(user_id)
    
    # Get charity details for each event
    for event in events:
        if 'charity_id' in event:
            charity = Charity.find_by_id(event['charity_id'])
            if charity:
                event['charity'] = charity
    
    return jsonify({
        'donations': events
    }), 200

@redistribute_bp.route('/charity-donations/<charity_id>', methods=['GET'])
@jwt_required()
def get_charity_donations(charity_id):
    events = list(mongo.db.events.find({
        'charity_id': charity_id,
        'status': 'assigned'
    }))
    
    return jsonify({
        'donations': events
    }), 200

@redistribute_bp.route('/suggest-locations', methods=['POST'])
@jwt_required()
def suggest_locations():
    """Suggest suitable locations for food redistribution"""
    data = request.get_json()
    event_id = data.get('event_id')
    
    # Get event details
    event_data = mongo.db.events.find_one({'_id': event_id})
    if not event_data:
        return jsonify({'error': 'Event not found'}), 404
        
    event = Event(event_data)
    
    # Find nearby charities
    nearby_charities = find_nearby_charities(event.location, event.food_items)
    
    return jsonify({
        'suggestions': nearby_charities
    })

@redistribute_bp.route('/confirm-redistribution', methods=['POST'])
@jwt_required()
def confirm_redistribution():
    """Confirm food redistribution to selected charity"""
    data = request.get_json()
    event_id = data.get('event_id')
    charity_id = data.get('charity_id')
    food_items = data.get('food_items', [])
    
    # Validate event and charity
    event_data = mongo.db.events.find_one({'_id': event_id})
    charity_data = mongo.db.charities.find_one({'_id': charity_id})
    
    if not event_data or not charity_data:
        return jsonify({'error': 'Invalid event or charity ID'}), 404
        
    event = Event(event_data)
    charity = Charity(charity_data)
    
    # Create redistribution record
    redistribution = {
        'event_id': event_id,
        'charity_id': charity_id,
        'food_items': food_items,
        'status': 'pending',
        'created_at': datetime.utcnow(),
        'pickup_time': data.get('pickup_time'),
        'notes': data.get('notes', '')
    }
    
    mongo.db.redistributions.insert_one(redistribution)
    
    # Update event status
    mongo.db.events.update_one(
        {'_id': event_id},
        {
            '$set': {
                'status': 'redistribution_pending',
                'redistribution_details': redistribution
            }
        }
    )
    
    # Notify charity (implement notification logic here)
    
    return jsonify({
        'message': 'Redistribution confirmed',
        'redistribution': redistribution
    })

@redistribute_bp.route('/track-redistribution/<redistribution_id>', methods=['GET'])
@jwt_required()
def track_redistribution(redistribution_id):
    """Track status of food redistribution"""
    redistribution = mongo.db.redistributions.find_one({'_id': redistribution_id})
    if not redistribution:
        return jsonify({'error': 'Redistribution not found'}), 404
        
    return jsonify(redistribution)

def find_nearby_charities(location, food_items, radius_km=10):
    """Find nearby charities that can accept the food items"""
    try:
        # Get all active and verified charities
        charities = mongo.db.charities.find({
            'active': True,
            'verified': True
        })
        
        nearby_charities = []
        for charity_data in charities:
            charity = Charity(charity_data)
            
            # Calculate distance using Haversine formula
            distance = haversine_distance(
                location['lat'], location['lng'],
                charity.location['lat'], charity.location['lng']
            )
            
            if distance <= radius_km and charity.is_suitable_for_food(food_items):
                charity_info = charity.to_dict()
                charity_info['distance'] = round(distance, 2)
                nearby_charities.append(charity_info)
        
        # Sort by distance
        nearby_charities.sort(key=lambda x: x['distance'])
        
        return nearby_charities
        
    except Exception as e:
        print(f"Error finding nearby charities: {str(e)}")
        return []
