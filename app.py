from flask import Flask, request, jsonify, render_template, send_from_directory
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
from models import db, User, Detection
from camera_controller import camera_controller

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'novaya')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///admin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize YOLO model
try:
    model = YOLO('yolov8n.pt')
except Exception as e:
    print(f"Error loading YOLO model: {e}")
    model = None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
def settings():
    return render_template('settings.html')

# API Routes
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and user.password == password:  # In production, use proper password hashing
        login_user(user)
        return jsonify({'message': 'Login successful'})
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/detections', methods=['GET'])
@login_required
def get_detections():
    detections = Detection.query.order_by(Detection.timestamp.desc()).all()
    return jsonify([{
        'id': d.id,
        'timestamp': d.timestamp.isoformat(),
        'location': d.location,
        'confidence': d.confidence,
        'image_path': d.image_path,
        'status': d.status
    } for d in detections])

@app.route('/api/detections', methods=['POST'])
@login_required
def create_detection():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save image
    filename = f"detections/{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    os.makedirs('detections', exist_ok=True)
    file.save(filename)

    # Process image with YOLO
    if model is None:
        return jsonify({'error': 'YOLO model not loaded'}), 500
        
    results = model(filename)
    
    # Check for phone detection
    phone_detected = False
    confidence = 0.0
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            if box.cls == 67:  # Class ID for cell phone in COCO dataset
                phone_detected = True
                confidence = float(box.conf)
                break

    if phone_detected:
        detection = Detection(
            location=request.form.get('location', 'Unknown'),
            confidence=confidence,
            image_path=filename,
            status='Pending'
        )
        db.session.add(detection)
        db.session.commit()
        
        return jsonify({
            'message': 'Phone detected',
            'detection': {
                'id': detection.id,
                'timestamp': detection.timestamp.isoformat(),
                'confidence': detection.confidence
            }
        })
    
    return jsonify({'message': 'No phone detected'})

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    return jsonify({
        'camera_start_time': camera_controller.settings['camera_start_time'],
        'camera_end_time': camera_controller.settings['camera_end_time'],
        'blur_faces': camera_controller.settings['blur_faces'],
        'confidence_threshold': camera_controller.settings['confidence_threshold'],
        'notifications': {
            'email': True,
            'sms': False,
            'telegram': True
        }
    })

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    
    # Update camera controller settings
    camera_controller.update_settings({
        'camera_start_time': data['camera_start_time'],
        'camera_end_time': data['camera_end_time'],
        'blur_faces': data['blur_faces'],
        'confidence_threshold': data['confidence_threshold']
    })
    
    return jsonify({'message': 'Settings updated successfully'})

# Serve detection images
@app.route('/detections/<path:filename>')
@login_required
def serve_detection(filename):
    return send_from_directory('detections', filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000) 