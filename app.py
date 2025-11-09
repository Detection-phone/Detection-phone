from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, Response
import time
import cv2
from flask_cors import CORS
import numpy as np
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
from models import db, User, Detection, Settings, DEFAULT_SCHEDULE
from camera_controller import CameraController
import logging
from flask_migrate import Migrate
from sqlalchemy import func
import cloudinary
import cloudinary.uploader
import cloudinary.api
from vonage import Auth
from vonage_sms import Sms
from vonage_http_client import HttpClient
from roboflow import Roboflow

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

# ============================================================
# GLOBALNE ZASOBY - Inicjalizacja TYLKO RAZ przy starcie serwera
# ============================================================
print("=" * 60)
print("INFO: Uruchamiam inicjalizację globalnych zasobów...")
print("=" * 60)

# 1. YOLO Model dla detekcji telefonów
print("INFO: Ładowanie modelu YOLO dla detekcji telefonów...")
try:
    GLOBAL_YOLO_MODEL_DETECTION = YOLO('yolov8s.pt')
    logger.info("✅ YOLO model (detection) loaded successfully")
except Exception as e:
    logger.error(f"❌ Error loading YOLO model (detection): {e}")
    GLOBAL_YOLO_MODEL_DETECTION = None

# 2. Roboflow Model dla anonimizacji (head-detection)
print("INFO: Pobieranie modelu Roboflow (head-detection)...")
try:
    # Inicjalizacja Roboflow z kluczem API
    rf = Roboflow(api_key="DAWQI4w1KCHH1MlWH7t4")
    
    try:
        GLOBAL_YOLO_MODEL_ANONYMIZATION = rf.model("heads-detection/1")
    except:
        try:
            workspace = rf.workspace("heads-detection")
            project = workspace.project("heads-detection")
            GLOBAL_YOLO_MODEL_ANONYMIZATION = project.version(1).model
        except:
            workspace = rf.workspace()
            project = workspace.project("heads-detection")
            GLOBAL_YOLO_MODEL_ANONYMIZATION = project.version(1).model
    
    print("INFO:__main__:✅ Roboflow model (anonymization) loaded successfully")
    logger.info("✅ Roboflow model (anonymization) loaded successfully")
except Exception as e:
    logger.error(f"❌ Error loading Roboflow model (anonymization): {e}")
    GLOBAL_YOLO_MODEL_ANONYMIZATION = None

# 3. Vonage Client (SMS)
print("INFO: Inicjalizacja klienta Vonage...")
GLOBAL_VONAGE_SMS = None
try:
    vonage_api_key = os.getenv('VONAGE_API_KEY')
    vonage_api_secret = os.getenv('VONAGE_API_SECRET')
    vonage_from_number = os.getenv('VONAGE_FROM_NUMBER', 'PhoneDetection')
    vonage_to_number = os.getenv('VONAGE_TO_NUMBER')
    
    if all([vonage_api_key, vonage_api_secret, vonage_to_number]):
        vonage_auth = Auth(api_key=vonage_api_key, api_secret=vonage_api_secret)
        vonage_http_client = HttpClient(vonage_auth)
        GLOBAL_VONAGE_SMS = Sms(vonage_http_client)
        logger.info("✅ Vonage client initialized")
    else:
        logger.warning("⚠️  Brak danych Vonage w zmiennych środowiskowych")
except Exception as e:
    logger.error(f"❌ Error initializing Vonage: {e}")

# 4. Cloudinary
print("INFO: Inicjalizacja Cloudinary...")
GLOBAL_CLOUDINARY_ENABLED = False
try:
    cloudinary_cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    cloudinary_api_key = os.getenv('CLOUDINARY_API_KEY')
    cloudinary_api_secret = os.getenv('CLOUDINARY_API_SECRET')
    
    if all([cloudinary_cloud_name, cloudinary_api_key, cloudinary_api_secret]):
        cloudinary.config(
            cloud_name=cloudinary_cloud_name,
            api_key=cloudinary_api_key,
            api_secret=cloudinary_api_secret,
            secure=True
        )
        GLOBAL_CLOUDINARY_ENABLED = True
        logger.info(f"✅ Cloudinary initialized (Cloud Name: {cloudinary_cloud_name})")
    else:
        logger.warning("⚠️  Brak danych Cloudinary w zmiennych środowiskowych")
except Exception as e:
    logger.error(f"❌ Error initializing Cloudinary: {e}")

# 5. Email credentials (yagmail - połączenie tworzone przy wysyłce)
print("INFO: Pobieranie danych Email...")
GLOBAL_EMAIL_USER = os.environ.get("GMAIL_USER")
GLOBAL_EMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GLOBAL_EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT")
if all([GLOBAL_EMAIL_USER, GLOBAL_EMAIL_PASSWORD, GLOBAL_EMAIL_RECIPIENT]):
    logger.info(f"✅ Email credentials loaded (from: {GLOBAL_EMAIL_USER})")
else:
    logger.warning("⚠️  Brak danych Email w zmiennych środowiskowych")

# 6. Skanowanie kamer (TYLKO RAZ)
print("INFO: Uruchamiam jednorazowe skanowanie kamer...")
try:
    # Użyj statycznej metody do skanowania (przed utworzeniem kontrolera)
    GLOBAL_CAMERA_LIST = CameraController._scan_available_cameras_static()
    logger.info(f"✅ Camera scan completed: Found {len(GLOBAL_CAMERA_LIST)} cameras")
except Exception as e:
    logger.error(f"❌ Error scanning cameras: {e}")
    GLOBAL_CAMERA_LIST = []

print("=" * 60)
print("INFO: Inicjalizacja globalnych zasobów zakończona.")
print("=" * 60)

# Initialize camera controller z przekazanymi zasobami
camera_controller = CameraController(
    yolo_model_detection=GLOBAL_YOLO_MODEL_DETECTION,
    yolo_model_anonymization=GLOBAL_YOLO_MODEL_ANONYMIZATION,
    vonage_sms=GLOBAL_VONAGE_SMS,
    cloudinary_enabled=GLOBAL_CLOUDINARY_ENABLED,
    email_user=GLOBAL_EMAIL_USER,
    email_password=GLOBAL_EMAIL_PASSWORD,
    email_recipient=GLOBAL_EMAIL_RECIPIENT,
    available_cameras_list=GLOBAL_CAMERA_LIST
)
logger.info("Camera controller initialized with global resources")

# Load settings from database and push to camera controller on startup
with app.app_context():
    try:
        # Wczytaj ustawienia RAZ z bazy
        settings = Settings.get_or_create_default()
        
        # Dodaj atrybuty z config do obiektu settings (dla kompatybilności)
        config = settings.config if settings.config else {}
        settings.blur_faces = config.get('blur_faces', True)
        settings.confidence_threshold = config.get('confidence_threshold', 0.2)
        settings.camera_index = config.get('camera_index', 0)
        settings.camera_name = config.get('camera_name', 'Camera 1')
        settings.email_notifications = config.get('email_notifications', False)
        settings.sms_notifications = config.get('sms_notifications', False)
        
        # PRZEKAŻ (push) ustawienia do kontrolera
        camera_controller.update_settings(settings)
        logger.info(f"Loaded settings from database: blur_faces={settings.blur_faces}, {len(settings.roi_zones) if settings.roi_zones else 0} ROI zones, schedule configured")
    except Exception as e:
        logger.error(f"Error loading settings on startup: {e}")

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
        if user and user.check_password(password):
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
    if user and user.check_password(password):
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
@login_required
def get_detections():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination = Detection.query.order_by(Detection.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    detections = pagination.items
    
    return jsonify({
        'detections': [{
            'id': d.id,
            'timestamp': d.timestamp.isoformat(),
            'location': d.location,
            'confidence': d.confidence,
            'image_path': os.path.basename(d.image_path),
            'status': d.status
        } for d in detections],
        'total_pages': pagination.pages,
        'current_page': pagination.page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    })

@app.route('/api/detections/<int:detection_id>', methods=['GET'])
@login_required
def get_detection_detail(detection_id: int):
    d = Detection.query.get_or_404(detection_id)
    return jsonify({
        'id': d.id,
        'timestamp': d.timestamp.isoformat(),
        'location': d.location,
        'confidence': d.confidence,
        'image_path': os.path.basename(d.image_path) if d.image_path else None,
        'status': d.status,
        'user_id': d.user_id
    })

@app.route('/api/detections/<int:detection_id>', methods=['DELETE'])
@login_required
def delete_detection(detection_id: int):
    d = Detection.query.get_or_404(detection_id)
    db.session.delete(d)
    db.session.commit()
    return jsonify({'message': 'Detection deleted successfully'})

@app.route('/api/detections/batch', methods=['DELETE'])
@login_required
def delete_many_detections():
    data = request.get_json()
    ids_to_delete = data.get('ids', [])

    if not ids_to_delete:
        return jsonify({'message': 'Brak ID do usunięcia.'}), 400

    try:
        # Konwertuj ID na int jeśli są stringami
        ids_to_delete = [int(id) if isinstance(id, str) else id for id in ids_to_delete]
        
        # Usuń detekcje z bazy
        num_deleted = Detection.query.filter(Detection.id.in_(ids_to_delete)).delete(synchronize_session=False)
        db.session.commit()

        return jsonify({'message': f'Usunięto {num_deleted} detekcji.', 'deleted_count': num_deleted}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting detections: {e}")
        return jsonify({'message': f'Błąd podczas usuwania detekcji: {str(e)}'}), 500

@app.route('/api/dashboard-stats', methods=['GET'])
@login_required
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
@login_required
def get_settings():
    # Get available cameras (with error handling) - używamy szybkiej metody z cache
    try:
        available_cameras = camera_controller.get_available_cameras()
        # Ensure it's always a list
        if not isinstance(available_cameras, list):
            logger.warning("get_available_cameras() did not return a list, using empty list")
            available_cameras = []
    except Exception as e:
        logger.error(f"BŁĄD podczas pobierania listy kamer: {e}")
        import traceback
        traceback.print_exc()
        available_cameras = []
    
    # --- KLUCZOWA POPRAWKA (FALLBACK) ---
    # Jeśli lista jest pusta, dodaj domyślną kamerę, aby UI nie było puste
    if not available_cameras:
        logger.warning("OSTRZEŻENIE: Skanowanie kamer nie zwróciło wyników. Dodaję domyślny fallback (Kamera 0).")
        print("⚠️ OSTRZEŻENIE: Skanowanie kamer nie zwróciło wyników. Dodaję domyślny fallback (Kamera 0).")
        available_cameras = [
            {
                'index': 0,
                'name': 'Domyślna Kamera (Indeks 0)',
                'resolution': '640x480',
                'fps': 30
            }
        ]
    
    # Get settings from database
    settings_db = Settings.get_or_create_default()
    
    # Get schedule from database
    schedule = settings_db.schedule if settings_db.schedule else DEFAULT_SCHEDULE.copy()
    
    # Get ROI zones from database
    roi_zones = settings_db.roi_zones if settings_db.roi_zones else []
    
    # Get config from database (with defaults)
    config = settings_db.config if settings_db.config else {
        'blur_faces': True,
        'confidence_threshold': 0.2,
        'camera_index': 0,
        'camera_name': 'Camera 1',
        'email_notifications': False,
        'sms_notifications': False
    }
    
    return jsonify({
        'schedule': schedule,  # Weekly schedule JSON
        'blur_faces': config.get('blur_faces', True),
        'confidence_threshold': config.get('confidence_threshold', 0.2),
        'camera_index': config.get('camera_index', 0),
        'camera_name': config.get('camera_name', 'Camera 1'),
        'anonymization_percent': config.get('anonymization_percent', 50),
        'roi_coordinates': config.get('roi_coordinates'),
        'roi_zones': roi_zones,  # ROI zones from database
        'available_cameras': available_cameras,  # Always a list (empty if error)
        'notifications': {
            'email': config.get('email_notifications', False),
            'sms': config.get('sms_notifications', False)
        }
    })

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    print("\nReceived settings update request")
    print(f"Data: {data}")
    
    try:
        # Update camera controller settings
        camera_settings = {
            'blur_faces': data.get('blur_faces', camera_controller.settings.get('blur_faces', True)),
            'confidence_threshold': data.get('confidence_threshold', camera_controller.settings.get('confidence_threshold', 0.2))
        }
        
        # Handle weekly schedule
        if 'schedule' in data:
            schedule = data['schedule']
            # Validate schedule structure
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            for day in days:
                if day not in schedule:
                    raise ValueError(f"Missing day in schedule: {day}")
                day_config = schedule[day]
                if 'enabled' not in day_config or 'start' not in day_config or 'end' not in day_config:
                    raise ValueError(f"Invalid config for {day}")
                # Validate time format
                try:
                    datetime.strptime(day_config['start'], '%H:%M')
                    datetime.strptime(day_config['end'], '%H:%M')
                except ValueError as e:
                    raise ValueError(f"Invalid time format for {day}: {e}")
            camera_settings['schedule'] = schedule
            print(f"📅 Schedule updated: {schedule}")
        
        # Handle camera selection
        if 'camera_index' in data:
            camera_index = int(data['camera_index'])
            camera_settings['camera_index'] = camera_index
            # Ustaw przypisaną kamerę w kontrolerze
            camera_controller.set_assigned_camera(camera_index)
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

        # Handle anonymization percent
        if 'anonymization_percent' in data:
            try:
                camera_settings['anonymization_percent'] = int(data['anonymization_percent'])
            except Exception:
                camera_settings['anonymization_percent'] = 50
        
        # Optional: Handle ROI coordinates (normalized [x1,y1,x2,y2])
        if 'roi_coordinates' in data:
            roi = data['roi_coordinates']
            try:
                if isinstance(roi, (list, tuple)) and len(roi) == 4:
                    roi_floats = [float(v) for v in roi]
                    camera_settings['roi_coordinates'] = roi_floats
            except Exception:
                pass
        
        # Zapisz ustawienia do bazy danych
        settings_db = Settings.get_or_create_default()
        
        # Aktualizuj schedule jeśli podany
        if 'schedule' in camera_settings:
            settings_db.schedule = camera_settings['schedule']
        
        # Pobierz obecny config lub utwórz nowy
        config = settings_db.config if settings_db.config else {}
        
        # Aktualizuj config z nowymi wartościami
        if 'blur_faces' in camera_settings:
            config['blur_faces'] = camera_settings['blur_faces']
            print(f"🔧 DEBUG: Zapisuję do DB config['blur_faces'] = {camera_settings['blur_faces']}")
        if 'confidence_threshold' in camera_settings:
            config['confidence_threshold'] = camera_settings['confidence_threshold']
            print(f"🔧 DEBUG: Zapisuję do DB config['confidence_threshold'] = {camera_settings['confidence_threshold']}")
        if 'camera_index' in camera_settings:
            config['camera_index'] = camera_settings['camera_index']
        if 'camera_name' in camera_settings:
            config['camera_name'] = camera_settings['camera_name']
        if 'email_notifications' in camera_settings:
            config['email_notifications'] = camera_settings['email_notifications']
            print(f"🔧 DEBUG: Zapisuję do DB config['email_notifications'] = {camera_settings['email_notifications']}")
        if 'sms_notifications' in camera_settings:
            config['sms_notifications'] = camera_settings['sms_notifications']
            print(f"🔧 DEBUG: Zapisuję do DB config['sms_notifications'] = {camera_settings['sms_notifications']}")
        if 'anonymization_percent' in camera_settings:
            config['anonymization_percent'] = camera_settings['anonymization_percent']
        if 'roi_coordinates' in camera_settings:
            config['roi_coordinates'] = camera_settings['roi_coordinates']
        
        # Zapisz zaktualizowany config do bazy
        settings_db.config = config
        settings_db.updated_at = datetime.utcnow()
        db.session.commit()
        
        print(f"✅ Zapisano ustawienia do bazy danych (config): {config}")
        
        # Dodaj ustawienia jako atrybuty obiektu (dla kompatybilności z update_settings)
        settings_db.blur_faces = config.get('blur_faces', True)
        settings_db.confidence_threshold = config.get('confidence_threshold', 0.2)
        settings_db.email_notifications = config.get('email_notifications', False)
        settings_db.sms_notifications = config.get('sms_notifications', False)
        settings_db.camera_name = config.get('camera_name', 'Camera 1')
        settings_db.camera_index = config.get('camera_index', 0)
        
        # DEBUG: Sprawdź wartości przed przekazaniem
        print(f"🔧 DEBUG: Przed update_settings:")
        print(f"  - blur_faces: {getattr(settings_db, 'blur_faces', 'BRAK')}")
        print(f"  - confidence_threshold: {getattr(settings_db, 'confidence_threshold', 'BRAK')}")
        print(f"  - email_notifications: {getattr(settings_db, 'email_notifications', 'BRAK')}")
        print(f"  - sms_notifications: {getattr(settings_db, 'sms_notifications', 'BRAK')}")
        
        # Przekaż zaktualizowany obiekt 'settings' do kontrolera
        camera_controller.update_settings(settings_db)
        
        return jsonify({
            'message': 'Settings updated successfully',
            'camera_status': {
                'is_running': camera_controller.is_running,
                'within_schedule': camera_controller._is_within_schedule()
            }
        })
    except Exception as e:
        print(f"Error updating settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/start', methods=['POST'])
@login_required
def start_camera():
    """Manually start the camera (ignore schedule)"""
    try:
        print("\n🚀 Manual camera start requested")
        camera_controller.manual_stop_engaged = False  # Resetuj blokadę manual stop
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
@login_required
def stop_camera():
    """Manually stop the camera"""
    try:
        print("\n🛑 Manual camera stop requested")
        camera_controller.manual_stop_engaged = True  # Ustaw blokadę manual stop
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
@login_required
def camera_status():
    """Get current camera status"""
    try:
        return jsonify({
            'is_running': camera_controller.is_running,
            'within_schedule': camera_controller._is_within_schedule(),
            'settings': {
                'schedule': camera_controller.settings.get('schedule', DEFAULT_SCHEDULE.copy()),
                'camera_name': camera_controller.settings['camera_name']
            }
        })
    except Exception as e:
        print(f"❌ Error getting camera status: {e}")
        return jsonify({'error': str(e)}), 500

# ✅ Serve detection images (secure endpoint with absolute path)
@app.route('/detections/<path:filename>')
@login_required
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

# =========================
# Camera MJPEG video stream
# =========================
# Placeholder image (Garfield) path - use absolute path
PLACEHOLDER_IMG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images', 'looking.png')

# Preload and encode placeholder once
# Always create a fallback image - never let this fail
def _create_fallback_placeholder():
    """Create a fallback placeholder image with 'Camera Offline' text"""
    try:
        placeholder_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            placeholder_frame, 
            'Camera Offline', 
            (160, 240), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1, 
            (255, 255, 255), 
            2
        )
        success, placeholder_buf = cv2.imencode('.jpg', placeholder_frame)
        if success:
            return placeholder_buf.tobytes()
        else:
            # If encoding fails, return empty bytes (shouldn't happen)
            logger.warning("Failed to encode fallback placeholder")
            return b''
    except Exception as e:
        logger.error(f"Critical error creating fallback placeholder: {e}")
        # Last resort: return empty bytes (will cause frame errors but app won't crash)
        return b''

# Try to load the real placeholder image, fallback to generated one
PLACEHOLDER_BYTES = None
try:
    # Check if file exists first
    if not os.path.exists(PLACEHOLDER_IMG_PATH):
        raise FileNotFoundError(f"Placeholder image not found: {PLACEHOLDER_IMG_PATH}")
    
    _ph_frame = cv2.imread(PLACEHOLDER_IMG_PATH)
    if _ph_frame is None or _ph_frame.size == 0:
        raise RuntimeError(f"Placeholder image not readable: {PLACEHOLDER_IMG_PATH}")
    success, _ph_buf = cv2.imencode('.jpg', _ph_frame)
    if not success:
        raise RuntimeError("Failed to encode placeholder image")
    PLACEHOLDER_BYTES = _ph_buf.tobytes()
    logger.info(f"✅ Loaded placeholder image from {PLACEHOLDER_IMG_PATH}")
except Exception as e:
    logger.debug(f"Placeholder image not available ({PLACEHOLDER_IMG_PATH}): {e}. Using fallback.")
    logger.info("Creating fallback placeholder image...")
    PLACEHOLDER_BYTES = _create_fallback_placeholder()
    if PLACEHOLDER_BYTES:
        logger.info("✅ Fallback placeholder created successfully")
    else:
        logger.error("❌ Failed to create fallback placeholder - video stream may fail")

# Ensure PLACEHOLDER_BYTES is never None
if PLACEHOLDER_BYTES is None:
    logger.error("CRITICAL: PLACEHOLDER_BYTES is None, creating emergency fallback...")
    PLACEHOLDER_BYTES = _create_fallback_placeholder()

def generate_frames():
    """Yield JPEG frames as multipart for MJPEG streaming with privacy Canny filter and offline placeholder.
    
    Odporna na wyścig wątków - jeśli _camera_loop podmieni self.last_frame na None w trakcie
    przetwarzania, cała operacja jest opakowana w try...except dla bezpieczeństwa.
    """
    while True:
        try:
            frame = camera_controller.get_last_frame() 
            
            if frame is None:
                # Jeśli klatka jest 'None', wyślij placeholder
                frame_bytes = PLACEHOLDER_BYTES
            else:
                # Spróbuj przetworzyć klatkę. To może się nie udać,
                # jeśli Wątek 1 podmieni ją na 'None' w trakcie.
                try:
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    edges = cv2.Canny(gray_frame, 100, 200)
                    edges_color = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                    
                    ret, buffer = cv2.imencode('.jpg', edges_color)
                    if not ret:
                        frame_bytes = PLACEHOLDER_BYTES  # Fallback
                    else:
                        frame_bytes = buffer.tobytes()
                except Exception as proc_err:
                    # Błąd podczas przetwarzania (np. frame zmienił się w trakcie)
                    print(f"BŁĄD W WĄTKU STREAMINGU (przetwarzanie Canny): {proc_err}")
                    frame_bytes = PLACEHOLDER_BYTES

        except Exception as e:
            # Jeśli cokolwiek pójdzie nie tak (np. cv::Mat::Mat, wyścig wątków),
            # złap błąd i wyślij placeholder, zamiast zawieszać wątek.
            print(f"BŁĄD W WĄTKU STREAMINGU (generate_frames): {e}")
            frame_bytes = PLACEHOLDER_BYTES
        
        # Zawsze coś wysyłaj, aby utrzymać połączenie
        try:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.05)  # Ok. 20 FPS
        except Exception as yield_err:
            # Jeśli yield się nie powiedzie, poczekaj i spróbuj ponownie
            print(f"BŁĄD W WĄTKU STREAMINGU (yield): {yield_err}")
            time.sleep(0.1)
            continue

@app.route('/api/camera/video_feed', methods=['GET'])
@login_required
def video_feed():
    """Stream live camera frames as MJPEG for the frontend settings page."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def anonymize_frame(frame, anonymization_model, settings):
    """
    Anonimizuje wykryte głowy na numpy array (frame).
    Używa modelu Roboflow head-detection do wykrywania i zamazywania całej głowy.
    
    Args:
        frame: numpy array (BGR image)
        anonymization_model: Roboflow model instance (head-detection)
        settings: camera controller settings dict (nieużywane, zachowane dla kompatybilności)
        
    Returns:
        anonymized_frame: numpy array z zanonimizowanymi głowami
    """
    try:
        if anonymization_model is None:
            logger.warning("Anonymization model not available, returning original frame")
            return frame.copy()
        
        # Kopiuj klatkę aby nie modyfikować oryginału
        anonymized_frame = frame.copy()
        img_h, img_w = anonymized_frame.shape[:2]
        
        # Zapisz klatkę tymczasowo (Roboflow wymaga pliku)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            temp_path = tmp.name
            cv2.imwrite(temp_path, frame)
        
        try:
            # Wykryj głowy za pomocą modelu Roboflow
            prediction = anonymization_model.predict(temp_path, confidence=40, overlap=30)
            results = prediction.json()
            heads_found = 0
            
            # Przetwórz wyniki (format Roboflow: x, y = środek; width, height)
            for det in results.get('predictions', []):
                confidence = det.get('confidence', 0)
                
                # Wykrywamy głowy
                if confidence >= 0.4:  # 0.4 = 40%
                    heads_found += 1
                    
                    # Pobierz współrzędne (Roboflow: środek + wymiary)
                    center_x = int(det['x'])
                    center_y = int(det['y'])
                    width = int(det['width'])
                    height = int(det['height'])
                    
                    # Konwertuj na (x1, y1, x2, y2)
                    x1 = center_x - width // 2
                    y1 = center_y - height // 2
                    x2 = center_x + width // 2
                    y2 = center_y + height // 2
                    
                    # Upewnij się, że współrzędne są w granicach obrazu
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(img_w, x2), min(img_h, y2)
                    
                    # Sprawdź czy ROI ma sens
                    if x2 <= x1 or y2 <= y1:
                        continue
                    
                    # Wybierz region (całą głowę)
                    roi = anonymized_frame[y1:y2, x1:x2]
                    
                    # Zastosuj silne rozmycie
                    if roi.size > 0:
                        blur = cv2.GaussianBlur(roi, (99, 99), 30)
                        anonymized_frame[y1:y2, x1:x2] = blur
            
            if heads_found > 0:
                logger.info(f"Anonymized {heads_found} heads in config snapshot")
        
        finally:
            # Usuń tymczasowy plik
            try:
                os.remove(temp_path)
            except:
                pass
        
        return anonymized_frame
        
    except Exception as e:
        logger.error(f"Error anonymizing frame: {e}")
        import traceback
        traceback.print_exc()
        return frame.copy()  # Return original on error

@app.route('/api/settings/roi', methods=['GET'])
@login_required
def get_roi_zones():
    """Get current ROI zones from database"""
    try:
        settings_db = Settings.get_or_create_default()
        roi_zones = settings_db.roi_zones if settings_db.roi_zones else []
        return jsonify({'roi_zones': roi_zones})
    except Exception as e:
        logger.error(f"Error getting ROI zones: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/roi', methods=['POST'])
@login_required
def save_roi_zones():
    """Save ROI zones to database"""
    try:
        data = request.get_json()
        roi_zones = data.get('roi_zones', [])
        
        # Validate format
        if not isinstance(roi_zones, list):
            return jsonify({'error': 'roi_zones must be a list'}), 400
        
        # Validate each ROI zone
        for zone in roi_zones:
            if not isinstance(zone, dict):
                return jsonify({'error': 'Each ROI zone must be an object'}), 400
            if 'id' not in zone or 'name' not in zone or 'coords' not in zone:
                return jsonify({'error': 'Each ROI zone must have id, name, and coords'}), 400
            coords = zone.get('coords', {})
            if not isinstance(coords, dict) or not all(k in coords for k in ['x', 'y', 'w', 'h']):
                return jsonify({'error': 'coords must have x, y, w, h properties'}), 400
            # Validate normalized coordinates (0-1)
            for coord_key in ['x', 'y', 'w', 'h']:
                val = coords[coord_key]
                if not isinstance(val, (int, float)) or val < 0 or val > 1:
                    return jsonify({'error': f'coords.{coord_key} must be between 0 and 1'}), 400
        
        # Save to database
        settings_db = Settings.get_or_create_default()
        settings_db.roi_zones = roi_zones
        settings_db.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Przekaż zaktualizowany obiekt 'settings' do kontrolera
        camera_controller.update_settings(settings_db)
        
        logger.info(f"Saved {len(roi_zones)} ROI zones to database")
        return jsonify({'message': 'ROI zones saved successfully', 'roi_zones': roi_zones})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving ROI zones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/config_snapshot', methods=['GET'])
@login_required
def config_snapshot():
    """
    Endpoint do pobrania pojedynczego, zanonimizowanego zdjęcia konfiguracyjnego.
    Użytkownik może użyć tego obrazu do rysowania ROI bez naruszania prywatności.
    
    UWAGA: Ten endpoint NIE czyta z kamery bezpośrednio!
    Pobiera tylko ostatnią klatkę z pętli detekcji (_camera_loop).
    """
    try:
        # 1. Pobierz pasywnie ostatnią klatkę z kontrolera
        frame = camera_controller.get_last_frame()
        
        # 2. Sprawdź, czy pętla detekcji w ogóle działa
        if frame is None:
            # Pętla nie działa, więc klatka jest 'None'
            return jsonify({
                'error': 'Kamera jest zatrzymana. Uruchom kamerę w panelu "Camera Control" i spróbuj ponownie.'
            }), 409  # 409 Conflict - stan zasobu jest niepoprawny
        
        # 3. Klatka istnieje. Zanonimizuj ją.
        try:
            anonymized_frame = camera_controller.anonymize_frame_logic(frame)
            
            ret, buffer = cv2.imencode('.jpg', anonymized_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                raise Exception("Nie udało się zakodować obrazu na JPEG.")
            
            return Response(buffer.tobytes(), mimetype='image/jpeg')
            
        except Exception as e:
            logger.error(f"Błąd podczas anonimizacji snapshotu: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Błąd przetwarzania obrazu.'}), 500
        
    except Exception as e:
        logger.error(f"Error in config_snapshot endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000) 