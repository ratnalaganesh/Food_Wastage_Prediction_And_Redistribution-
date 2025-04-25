from datetime import datetime
from database.db import mongo

class User:
    def __init__(self, email, mobile, password):
        self.email = email
        self.mobile = mobile
        self.password = password
        self.created_at = datetime.utcnow()
        self.verified = False

    def save(self):
        return mongo.db.users.insert_one({
            'email': self.email,
            'mobile': self.mobile,
            'password': self.password,
            'created_at': self.created_at,
            'verified': self.verified
        })

    @staticmethod
    def find_by_email(email):
        return mongo.db.users.find_one({'email': email})

    @staticmethod
    def find_by_mobile(mobile):
        return mongo.db.users.find_one({'mobile': mobile}) 