from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    location = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    image_path = db.Column(db.String(200))
    status = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='detections')

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(500))
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_value(key, default=None):
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set_value(key, value, description=None):
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = Settings(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return setting 