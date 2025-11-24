from app import app, db, User, Settings, DEFAULT_SCHEDULE

def init_db():
    with app.app_context():

        db.create_all()
        

        settings = Settings.query.first()
        if not settings:
            settings = Settings(
                schedule=DEFAULT_SCHEDULE,
                config={
                    'blur_faces': True,
                    'confidence_threshold': 0.2,
                    'camera_index': 0,
                    'camera_name': 'Camera 1',
                    'email_notifications': False,
                    'sms_notifications': False
                }
            )
            db.session.add(settings)
            db.session.commit()
            print("✅ Default settings created successfully!")
        else:
            print("ℹ️  Settings already exist")
        

        admin = User.query.filter_by(username='admin').first()
        if not admin:

            admin = User(username='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created successfully!")
            print("   Username: admin")
            print("   Password: admin")
        else:
            print("ℹ️  Admin user already exists!")

if __name__ == '__main__':
    init_db() 