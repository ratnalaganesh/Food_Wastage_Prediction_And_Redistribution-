from flask import Blueprint, request, jsonify, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import mongo
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
import json
from bson import ObjectId
from models.user import User
from flask_login import login_user, logout_user, current_user, login_required

auth_bp = Blueprint('auth', __name__)

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # Get form data
            email = request.form.get('email')
            mobile = request.form.get('mobile')
            password = request.form.get('password')
            name = request.form.get('name')
            
            # Validate required fields
            if not all([email, mobile, password]):
                flash('Missing required fields', 'error')
                return render_template('auth/register.html')
            
            # Check if user already exists
            if mongo.db.users.find_one({
                '$or': [
                    {'email': email},
                    {'mobile': mobile}
                ]
            }):
                flash('Email or mobile number already registered', 'error')
                return render_template('auth/register.html')
            
            # Create new user
            user = User(
                email=email,
                mobile=mobile,
                name=name
            )
            user.set_password(password)
            
            # Save user to database
            result = mongo.db.users.insert_one({
                'email': user.email,
                'mobile': user.mobile,
                'password': user.password_hash,
                'name': user.name,
                'created_at': user.created_at,
                'is_active': user.is_active
            })
            
            # Set the user's ID
            user._id = result.inserted_id
            
            # Log the user in
            login_user(user)
            
            flash('Registration successful!', 'success')
            return redirect(url_for('predict.predict_page'))
            
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            # Get form data
            login_id = request.form.get('login_id')
            password = request.form.get('password')
            
            if not login_id or not password:
                flash('Please enter both login ID and password', 'error')
                return render_template('auth/login.html')
            
            # Check if login is with email or mobile
            is_email = '@' in login_id
            
            # Find user by email or mobile
            user_data = mongo.db.users.find_one({
                '$or': [
                    {'email': login_id} if is_email else {'mobile': login_id}
                ]
            })
            
            if not user_data:
                flash('Invalid login credentials', 'error')
                return render_template('auth/login.html')
            
            # Create User object
            user = User(
                email=user_data['email'],
                name=user_data.get('name', ''),
                mobile=user_data.get('mobile', '')
            )
            user._id = user_data['_id']
            user.password_hash = user_data['password']
            
            # Verify password
            if not user.check_password(password):
                flash('Invalid login credentials', 'error')
                return render_template('auth/login.html')
            
            # Log the user in
            login_user(user)
            
            # Redirect to next page or default
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('predict.predict_page')
            
            flash('Login successful!', 'success')
            return redirect(next_page)
            
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def get_profile():
    try:
        # Get user's predictions
        predictions = list(mongo.db.predictions.find({
            'user_id': current_user._id
        }).sort('created_at', -1).limit(10))

        # Calculate average wastage
        total_wastage = sum(p.get('estimated_wastage', 0) for p in predictions)
        average_wastage = total_wastage / len(predictions) if predictions else 0

        return render_template('profile.html',
                             predictions=predictions,
                             average_wastage=average_wastage)
    except Exception as e:
        flash('Error loading profile: ' + str(e), 'danger')
        return redirect(url_for('index'))

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        # Get the user ID from the JWT token
        current_user_id = get_jwt_identity()
        
        # Find the user in the database
        user = mongo.db.users.find_one({'_id': ObjectId(current_user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Return user data (excluding sensitive information)
        return jsonify({
            'id': str(user['_id']),
            'email': user['email'],
            'mobile': user.get('mobile'),
            'name': user.get('name')
        }), 200
        
    except Exception as e:
        print(f"Get current user error: {str(e)}")
        return jsonify({'error': str(e)}), 500
