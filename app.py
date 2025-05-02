from flask import Flask, request, jsonify, render_template, send_from_directory, abort
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
import os
from dotenv import load_dotenv
import cv2
import numpy as np
from ultralytics import YOLO
import json
import torch
from models import db, User, Detection, Settings
from camera_controller import camera_controller
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash
from werkzeug.exceptions import HTTPException
from flask_migrate import Migrate

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
logger.addHandler(handler)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'novaya')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///admin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize YOLO model
try:
    model = YOLO('yolov8n.pt')
    logger.info("YOLO model loaded successfully")
except Exception as e:
    logger.error(f"Error loading YOLO model: {e}")
    model = None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def validate_json(schema):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400
            try:
                data = request.get_json()
                # Basic validation example - expand based on your needs
                for key, value_type in schema.items():
                    if key not in data:
                        return jsonify({'error': f'Missing required field: {key}'}), 400
                    if not isinstance(data[key], value_type):
                        return jsonify({'error': f'Invalid type for {key}'}), 400
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': str(e)}), 400
        return decorated_function
    return decorator

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    logger.error(f"Error: {str(e)}")
    return jsonify({'error': str(e)}), code

# Frontend Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/detections')
@login_required
def detections():
    return render_template('detections.html')

@app.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('settings.html')

# API Routes
@app.route('/api/login', methods=['POST'])
@validate_json({'username': str, 'password': str})
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user)
        logger.info(f"User {username} logged in successfully")
        return jsonify({'message': 'Login successful'})
    
    logger.warning(f"Failed login attempt for username: {username}")
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/logout')
@login_required
def logout():
    logger.info(f"User {current_user.username} logged out")
    logout_user()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/detections', methods=['GET'])
@login_required
def get_detections():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Detection.query
    
    if status:
        query = query.filter_by(status=status)
    if start_date:
        query = query.filter(Detection.timestamp >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Detection.timestamp <= datetime.fromisoformat(end_date))
    
    if current_user.role != 'admin':
        query = query.filter_by(user_id=current_user.id)
    
    detections = query.order_by(Detection.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'detections': [{
            'id': d.id,
            'timestamp': d.timestamp.isoformat(),
            'location': d.location,
            'confidence': d.confidence,
            'image_path': d.image_path,
            'status': d.status
        } for d in detections.items],
        'total': detections.total,
        'pages': detections.pages,
        'current_page': detections.page
    })

@app.route('/api/detections/<int:detection_id>', methods=['DELETE'])
@login_required
def delete_detection(detection_id):
    detection = Detection.query.get_or_404(detection_id)
    
    if current_user.role != 'admin' and detection.user_id != current_user.id:
        abort(403)
    
    try:
        if os.path.exists(detection.image_path):
            os.remove(detection.image_path)
        db.session.delete(detection)
        db.session.commit()
        logger.info(f"Detection {detection_id} deleted by user {current_user.username}")
        return jsonify({'message': 'Detection deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting detection {detection_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET'])
@login_required
@admin_required
def get_settings():
    settings = {
        'camera': {
            'start_time': Settings.get_value('camera_start_time', '00:00'),
            'end_time': Settings.get_value('camera_end_time', '23:59'),
            'blur_faces': Settings.get_value('blur_faces', 'true').lower() == 'true',
            'confidence_threshold': float(Settings.get_value('confidence_threshold', '0.4'))
        },
        'notifications': {
            'email': Settings.get_value('email_enabled', 'true').lower() == 'true',
            'sms': Settings.get_value('sms_enabled', 'false').lower() == 'true',
            'telegram': Settings.get_value('telegram_enabled', 'true').lower() == 'true'
        }
    }
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
@login_required
@admin_required
@validate_json({
    'camera_start_time': str,
    'camera_end_time': str,
    'blur_faces': bool,
    'confidence_threshold': (int, float),
    'email_enabled': bool,
    'sms_enabled': bool,
    'telegram_enabled': bool
})
def update_settings():
    data = request.get_json()
    
    # Update camera settings
    camera_settings = {
        'camera_start_time': data['camera_start_time'],
        'camera_end_time': data['camera_end_time'],
        'blur_faces': data['blur_faces'],
        'confidence_threshold': data['confidence_threshold']
    }
    camera_controller.update_settings(camera_settings)
    
    # Save settings to database
    Settings.set_value('camera_start_time', data['camera_start_time'], 'Camera start time (24h format)')
    Settings.set_value('camera_end_time', data['camera_end_time'], 'Camera end time (24h format)')
    Settings.set_value('blur_faces', str(data['blur_faces']).lower(), 'Enable/disable face blurring')
    Settings.set_value('confidence_threshold', str(data['confidence_threshold']), 'Detection confidence threshold')
    Settings.set_value('email_enabled', str(data['email_enabled']).lower(), 'Enable/disable email notifications')
    Settings.set_value('sms_enabled', str(data['sms_enabled']).lower(), 'Enable/disable SMS notifications')
    Settings.set_value('telegram_enabled', str(data['telegram_enabled']).lower(), 'Enable/disable Telegram notifications')
    
    logger.info(f"Settings updated by user {current_user.username}")
    return jsonify({'message': 'Settings updated successfully'})

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
@validate_json({'username': str, 'password': str, 'role': str})
def create_user():
    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    user = User(username=data['username'], role=data['role'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    
    logger.info(f"New user created: {data['username']} with role {data['role']}")
    return jsonify({'message': 'User created successfully'}), 201

# Serve detection images
@app.route('/detections/<path:filename>')
@login_required
def serve_detection(filename):
    return send_from_directory('detections', filename)

def init_default_settings():
    with app.app_context():
        # Create default admin user if none exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Default admin user created")
        
        # Initialize default settings
        default_settings = {
            'camera_start_time': ('00:00', 'Camera start time (24h format)'),
            'camera_end_time': ('23:59', 'Camera end time (24h format)'),
            'blur_faces': ('true', 'Enable/disable face blurring'),
            'confidence_threshold': ('0.4', 'Detection confidence threshold'),
            'email_enabled': ('true', 'Enable/disable email notifications'),
            'sms_enabled': ('false', 'Enable/disable SMS notifications'),
            'telegram_enabled': ('true', 'Enable/disable Telegram notifications')
        }
        
        for key, (value, description) in default_settings.items():
            if not Settings.query.filter_by(key=key).first():
                Settings.set_value(key, value, description)
                logger.info(f"Default setting initialized: {key}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_default_settings()
    app.run(debug=True, port=5000) 