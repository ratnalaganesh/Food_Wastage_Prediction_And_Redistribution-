import pandas as pd
from sklearn.linear_model import LinearRegression
import pickle

data = {"event_type": [1, 2, 1, 2, 3], "attendees": [50, 100, 200, 500, 1000],
        "wastage_kg": [5, 15, 30, 80, 150]}

df = pd.DataFrame(data)
X = df[['event_type', 'attendees']]
y = df['wastage_kg']

model = LinearRegression()
model.fit(X, y)

pickle.dump(model, open("models/food_model.pkl", "wb"))

class FoodWastagePrediction:
    def __init__(self, event_type, attendees, food_items):
        self.event_type = event_type
        self.attendees = attendees
        self.food_items = food_items
        
    def predict_wastage(self):
        """
        Predicts the amount of food wastage based on event type, attendees, and food items.
        Returns a dictionary with predicted wastage for each food item.
        """
        wastage_predictions = {}
        
        # Base wastage factors (can be adjusted based on historical data)
        event_type_factors = {
            'wedding': 0.15,
            'conference': 0.10,
            'party': 0.20,
            'corporate': 0.12,
            'other': 0.15
        }
        
        # Get wastage factor for event type (default to 'other' if not found)
        wastage_factor = event_type_factors.get(self.event_type.lower(), event_type_factors['other'])
        
        # Calculate predicted wastage for each food item
        for food_item in self.food_items:
            quantity = food_item.get('quantity', 0)
            serving_size = food_item.get('serving_size', 1)
            
            # Calculate total servings
            total_servings = quantity / serving_size
            
            # Calculate predicted wastage based on attendees and wastage factor
            predicted_wastage = total_servings * wastage_factor
            
            wastage_predictions[food_item['name']] = {
                'original_quantity': quantity,
                'predicted_wastage': round(predicted_wastage, 2),
                'unit': food_item.get('unit', 'servings')
            }
        
        return wastage_predictions

    def to_dict(self):
        return {
            'event_type': self.event_type,
            'attendees': self.attendees,
            'food_items': self.food_items
        }
