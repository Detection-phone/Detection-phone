from app import app, db, User, Settings, DEFAULT_SCHEDULE

def init_db():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create default settings if they don't exist
        settings = Settings.query.first()
        if not settings:
            settings = Settings(schedule=DEFAULT_SCHEDULE)
            db.session.add(settings)
            db.session.commit()
            print("✅ Default settings created successfully!")
        else:
            print("ℹ️  Settings already exist")
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
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