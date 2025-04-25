from flask_pymongo import PyMongo
from flask import current_app

mongo = PyMongo()

def init_db(app):
    app.config['MONGO_URI'] = 'mongodb://localhost:27017/food_wastage'
    mongo.init_app(app)
