from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()


DEFAULT_SCHEDULE = {
    'monday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'tuesday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'wednesday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'thursday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'friday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'saturday': {'enabled': False, 'start': '07:00', 'end': '16:00'},
    'sunday': {'enabled': False, 'start': '07:00', 'end': '16:00'}
}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    location = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    image_path = db.Column(db.String(200))
    status = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    schedule = db.Column(db.JSON, nullable=False, default=lambda: DEFAULT_SCHEDULE)

    roi_zones = db.Column(db.JSON, nullable=False, default=lambda: [])

    config = db.Column(db.JSON, nullable=False, default=lambda: {
        'blur_faces': True,
        'confidence_threshold': 0.2,
        'camera_index': 0,
        'camera_name': 'Camera 1',
        'email_notifications': False,
        'sms_notifications': False
    })
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_or_create_default():
        """Get the first settings record or create one with defaults"""
        settings = Settings.query.first()
        if not settings:
            settings = Settings(schedule=DEFAULT_SCHEDULE)
            db.session.add(settings)
            db.session.commit()
        return settings
    