from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin):
    def __init__(self, email, name='', mobile=''):
        self.email = email
        self.name = name
        self.mobile = mobile
        self.created_at = datetime.utcnow()
        self._is_active = True
        self._id = None
        self.password_hash = None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self._id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    @property
    def is_anonymous(self):
        return False

    def to_dict(self):
        return {
            'id': str(self._id),
            'email': self.email,
            'mobile': self.mobile,
            'name': self.name,
            'created_at': self.created_at
        } 