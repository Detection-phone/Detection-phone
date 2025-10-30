from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import cv2
import numpy as np
from ultralytics import YOLO
import json
import torch
from models import db, User, Detection
from camera_controller import CameraController
import logging
from flask_migrate import Migrate
from sqlalchemy import func

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ✅ CORS configuration for React frontend (applies to ALL routes)
# Allows requests from http://localhost:3000 to every Flask route, including /detections/*
CORS(
    app,
    origins=["http://localhost:3000"],
    supports_credentials=True,
)

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'novaya')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///admin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ DETECTION FOLDER: Absolute path to detections directory
DETECTION_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'detections')

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Musisz się zalogować, aby uzyskać dostęp do tej strony."
login_manager.login_message_category = "danger"

# Initialize camera controller
camera_controller = CameraController()
logger.info("Camera controller initialized")

# Initialize YOLO model
try:
    model = YOLO('yolov8n.pt')
    logger.info("YOLO model loaded successfully")
except Exception as e:
    logger.error(f"Error loading YOLO model: {e}")
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle both JSON (API) and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # In production, use proper password hashing
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        
        # If JSON request, return JSON error
        if request.is_json:
            return jsonify({'message': 'Invalid credentials'}), 401
        
        # If form request, render login with error
        return render_template('login.html', error='Nieprawidłowe dane logowania')
    
    # GET request - render login page
    return render_template('login.html')

# API Routes
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and user.password == password:  # In production, use proper password hashing
        login_user(user)
        return jsonify({'message': 'Login successful'})
    
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/logout')
@login_required
def logout_page():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/logout')
@login_required
def logout_api():
    logout_user()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/detections', methods=['GET'])
# @login_required  # ⚠️ TEMPORARILY DISABLED for CORS testing
def get_detections():
    detections = Detection.query.order_by(Detection.timestamp.desc()).all()
    return jsonify([{
        'id': d.id,
        'timestamp': d.timestamp.isoformat(),
        'location': d.location,
        'confidence': d.confidence,
        'image_path': os.path.basename(d.image_path),
        'status': d.status
    } for d in detections])

@app.route('/api/dashboard-stats', methods=['GET'])
# @login_required  # ⚠️ TEMPORARILY DISABLED for CORS testing
def get_dashboard_stats():
    """Get real-time dashboard statistics"""
    # Get all detections
    all_detections = Detection.query.all()
    total_detections = len(all_detections)
    
    # Get today's detections
    today = datetime.now().date()
    today_detections = Detection.query.filter(
        db.func.date(Detection.timestamp) == today
    ).count()
    
    # Get camera status
    camera_status = 'Online' if camera_controller.is_running else 'Offline'
    within_schedule = camera_controller._is_within_schedule()
    
    # Get recent detections (last 5)
    recent_detections = Detection.query.order_by(
        Detection.timestamp.desc()
    ).limit(5).all()
    
    recent_detections_list = [{
        'id': d.id,
        'timestamp': d.timestamp.isoformat(),
        'location': d.location,
        'confidence': d.confidence,
        'image_path': os.path.basename(d.image_path),
        'status': d.status
    } for d in recent_detections]
    
    return jsonify({
        'total_detections': total_detections,
        'today_detections': today_detections,
        'camera_status': camera_status,
        'within_schedule': within_schedule,
        'recent_detections': recent_detections_list
    })

@app.route('/api/stats/detections_over_time', methods=['GET'])
def detections_over_time_stats():
    """Return detections count for the last 7 days, grouped by date."""
    try:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        rows = db.session.query(
            func.date(Detection.timestamp).label('date'),
            func.count(Detection.id).label('count')
        ).filter(
            Detection.timestamp >= seven_days_ago
        ).group_by(
            func.date(Detection.timestamp)
        ).order_by(
            func.date(Detection.timestamp)
        ).all()

        formatted = [{
            'name': str(r.date),
            'count': int(r.count)
        } for r in rows]

        return jsonify(formatted)
    except Exception as e:
        logger.error(f"Error building detections_over_time stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/detections', methods=['POST'])
@login_required
def create_detection():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save image
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    os.makedirs('detections', exist_ok=True)
    filepath = os.path.join('detections', filename)
    file.save(filepath)

    # Process image with YOLO
    if model is None:
        return jsonify({'error': 'YOLO model not loaded'}), 500
        
    results = model(filepath)
    
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
            image_path=filename,  # Only filename
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
# @login_required  # ⚠️ TEMPORARILY DISABLED for testing
def get_settings():
    # Get available cameras
    available_cameras = CameraController.scan_available_cameras()
    
    return jsonify({
        'camera_start_time': camera_controller.settings['camera_start_time'],
        'camera_end_time': camera_controller.settings['camera_end_time'],
        'blur_faces': camera_controller.settings['blur_faces'],
        'confidence_threshold': camera_controller.settings['confidence_threshold'],
        'camera_index': camera_controller.settings['camera_index'],
        'camera_name': camera_controller.settings['camera_name'],
        'available_cameras': available_cameras,
        'notifications': {
            'email': camera_controller.settings.get('email_notifications', False),
            'sms': camera_controller.settings.get('sms_notifications', False)
        }
    })

@app.route('/api/settings', methods=['POST'])
# @login_required  # ⚠️ TEMPORARILY DISABLED for testing
def update_settings():
    data = request.get_json()
    print("\nReceived settings update request")
    print(f"Data: {data}")
    
    try:
        # Update camera controller settings
        camera_settings = {
            'camera_start_time': data['camera_start_time'],
            'camera_end_time': data['camera_end_time'],
            'blur_faces': data['blur_faces'],
            'confidence_threshold': data['confidence_threshold']
        }
        
        # Handle camera selection
        if 'camera_index' in data:
            camera_settings['camera_index'] = int(data['camera_index'])
        if 'camera_name' in data:
            camera_settings['camera_name'] = data['camera_name']
        
        # Handle notifications (SMS and Email)
        if 'notifications' in data:
            if 'sms' in data['notifications']:
                camera_settings['sms_notifications'] = data['notifications']['sms']
                print(f"📱 SMS notifications: {data['notifications']['sms']}")
            if 'email' in data['notifications']:
                camera_settings['email_notifications'] = data['notifications']['email']
                print(f"📧 Email notifications: {data['notifications']['email']}")
        
        print(f"Updating camera controller with settings: {camera_settings}")
        camera_controller.update_settings(camera_settings)
        
        # Check current camera status
        print(f"Camera running: {camera_controller.is_running}")
        print(f"Within schedule: {camera_controller._is_within_schedule()}")
        
        return jsonify({
            'message': 'Settings updated successfully',
            'camera_status': {
                'is_running': camera_controller.is_running,
                'within_schedule': camera_controller._is_within_schedule()
            }
        })
    except Exception as e:
        print(f"Error updating settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/start', methods=['POST'])
# @login_required  # ⚠️ TEMPORARILY DISABLED for testing
def start_camera():
    """Manually start the camera (ignore schedule)"""
    try:
        print("\n🚀 Manual camera start requested")
        camera_controller.start_camera()
        return jsonify({
            'message': 'Camera started successfully',
            'camera_status': {
                'is_running': camera_controller.is_running,
                'within_schedule': camera_controller._is_within_schedule()
            }
        })
    except Exception as e:
        print(f"❌ Error starting camera: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/stop', methods=['POST'])
# @login_required  # ⚠️ TEMPORARILY DISABLED for testing
def stop_camera():
    """Manually stop the camera"""
    try:
        print("\n🛑 Manual camera stop requested")
        camera_controller.stop_camera()
        return jsonify({
            'message': 'Camera stopped successfully',
            'camera_status': {
                'is_running': camera_controller.is_running,
                'within_schedule': camera_controller._is_within_schedule()
            }
        })
    except Exception as e:
        print(f"❌ Error stopping camera: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/status', methods=['GET'])
# @login_required  # ⚠️ TEMPORARILY DISABLED for testing
def camera_status():
    """Get current camera status"""
    try:
        return jsonify({
            'is_running': camera_controller.is_running,
            'within_schedule': camera_controller._is_within_schedule(),
            'settings': {
                'camera_start_time': camera_controller.settings['camera_start_time'],
                'camera_end_time': camera_controller.settings['camera_end_time'],
                'camera_name': camera_controller.settings['camera_name']
            }
        })
    except Exception as e:
        print(f"❌ Error getting camera status: {e}")
        return jsonify({'error': str(e)}), 500

# ✅ Serve detection images (secure endpoint with absolute path)
@app.route('/detections/<path:filename>')
# @login_required  # ⚠️ TEMPORARILY DISABLED for testing
def serve_detection_image(filename):
    """
    Securely serve detection images from the detections folder.
    Uses absolute path to ensure cross-platform compatibility.
    """
    try:
        print(f"📸 Serving image: {filename} from {DETECTION_FOLDER}")
        return send_from_directory(DETECTION_FOLDER, filename)
    except FileNotFoundError:
        print(f"❌ Image not found: {filename}")
        return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        print(f"❌ Error serving image {filename}: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000) 