from datetime import datetime
from database.db import mongo

class Charity:
    def __init__(self, charity_data):
        self.id = charity_data.get('_id')
        self.name = charity_data.get('name')
        self.organization_type = charity_data.get('organization_type')  # shelter, food_bank, ngo, etc.
        self.address = charity_data.get('address')
        self.location = charity_data.get('location')  # {lat: float, lng: float}
        self.contact_person = charity_data.get('contact_person')
        self.phone = charity_data.get('phone')
        self.email = charity_data.get('email')
        self.capacity = charity_data.get('capacity')  # Maximum food capacity they can handle
        self.available_times = charity_data.get('available_times', [])  # Time slots for food collection
        self.requirements = charity_data.get('requirements', [])  # Specific food requirements/restrictions
        self.active = charity_data.get('active', True)
        self.verified = charity_data.get('verified', False)
        self.rating = charity_data.get('rating', 0.0)
        self.created_at = charity_data.get('created_at', datetime.utcnow())
        self.updated_at = charity_data.get('updated_at', datetime.utcnow())

    def to_dict(self):
        return {
            '_id': self.id,
            'name': self.name,
            'organization_type': self.organization_type,
            'address': self.address,
            'location': self.location,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'email': self.email,
            'capacity': self.capacity,
            'available_times': self.available_times,
            'requirements': self.requirements,
            'active': self.active,
            'verified': self.verified,
            'rating': self.rating,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(data):
        return Charity(data)

    def is_suitable_for_food(self, food_items):
        """
        Check if the charity can accept the given food items based on their requirements
        """
        if not self.active or not self.verified:
            return False
            
        # Check if the charity has capacity
        total_quantity = sum(item.get('quantity', 0) for item in food_items)
        if total_quantity > self.capacity:
            return False
            
        # Check if food items meet the charity's requirements
        for requirement in self.requirements:
            if requirement.get('type') == 'restriction':
                restricted_items = requirement.get('items', [])
                for food_item in food_items:
                    if food_item['name'].lower() in [item.lower() for item in restricted_items]:
                        return False
                        
        return True

    def save(self):
        return mongo.db.charities.insert_one({
            'name': self.name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'location': self.location,
            'capacity': self.capacity,
            'created_at': self.created_at,
            'rating': self.rating,
            'total_donations': self.total_donations
        })

    @staticmethod
    def find_nearby(location, max_distance=10000):  # max_distance in meters
        return list(mongo.db.charities.find({
            'location': {
                '$near': {
                    '$geometry': location,
                    '$maxDistance': max_distance
                }
            }
        }))

    @staticmethod
    def find_by_id(charity_id):
        return mongo.db.charities.find_one({'_id': charity_id}) 