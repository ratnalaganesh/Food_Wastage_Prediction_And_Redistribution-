from datetime import datetime
from database.db import mongo

class Event:
    def __init__(self, event_data):
        self.id = event_data.get('_id')
        self.user_id = event_data.get('user_id')
        self.event_name = event_data.get('event_name')
        self.event_type = event_data.get('event_type')
        self.date = event_data.get('date')
        self.location = event_data.get('location')
        self.expected_attendees = event_data.get('expected_attendees')
        self.food_items = event_data.get('food_items', [])  # List of food items with quantities
        self.wasted_food = event_data.get('wasted_food', [])  # Actual wasted food items
        self.status = event_data.get('status', 'pending')  # pending, active, completed
        self.redistribution_details = event_data.get('redistribution_details', None)
        self.created_at = event_data.get('created_at', datetime.utcnow())
        self.updated_at = event_data.get('updated_at', datetime.utcnow())

    def to_dict(self):
        return {
            '_id': self.id,
            'user_id': self.user_id,
            'event_name': self.event_name,
            'event_type': self.event_type,
            'date': self.date,
            'location': self.location,
            'expected_attendees': self.expected_attendees,
            'food_items': self.food_items,
            'wasted_food': self.wasted_food,
            'status': self.status,
            'redistribution_details': self.redistribution_details,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data):
        return Event(data)

    def save(self):
        return mongo.db.events.insert_one({
            'user_id': self.user_id,
            'event_type': self.event_type,
            'food_items': self.food_items,
            'quantity': self.quantity,
            'location': self.location,
            'created_at': self.created_at,
            'status': self.status
        })

    @staticmethod
    def find_by_user_id(user_id):
        return list(mongo.db.events.find({'user_id': user_id}))

    @staticmethod
    def find_nearby(location, max_distance=10000):  # max_distance in meters
        return list(mongo.db.events.find({
            'location': {
                '$near': {
                    '$geometry': location,
                    '$maxDistance': max_distance
                }
            }
        })) 