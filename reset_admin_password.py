from app import app, db, User

def reset_admin_password():
    """Resetuje hasło użytkownika admin na 'admin'"""
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            admin.set_password('admin')
            db.session.commit()
            print("✅ Hasło użytkownika 'admin' zostało zresetowane na 'admin'")
            print("   Username: admin")
            print("   Password: admin")
        else:
            # Jeśli nie istnieje, utwórz
            admin = User(username='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print("✅ Utworzono użytkownika 'admin' z hasłem 'admin'")
            print("   Username: admin")
            print("   Password: admin")

if __name__ == '__main__':
    reset_admin_password()

