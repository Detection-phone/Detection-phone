"""
Skrypt do aktualizacji bazy danych - dodaje pole config do tabeli settings
"""
from app import app, db
from models import Settings
import json

def upgrade_database():
    """Add config column to settings table if it doesn't exist"""
    with app.app_context():
        try:
            print("⚠️  Próbuję dodać kolumnę 'config' do bazy danych...")
            
            # Add column using raw SQL (for SQLite)
            default_config = json.dumps({
                'blur_faces': True,
                'confidence_threshold': 0.2,
                'camera_index': 0,
                'camera_name': 'Camera 1',
                'email_notifications': False,
                'sms_notifications': False
            })
            
            # For SQLite, we need to use ALTER TABLE
            try:
                db.session.execute(
                    db.text(f"ALTER TABLE settings ADD COLUMN config TEXT NOT NULL DEFAULT '{default_config}'")
                )
                db.session.commit()
                print("✅ Dodano kolumnę 'config' do tabeli settings")
            except Exception as e:
                error_str = str(e).lower()
                if "duplicate column name" in error_str or "already exists" in error_str:
                    print("✅ Kolumna 'config' już istnieje w bazie danych")
                else:
                    print(f"❌ Błąd podczas dodawania kolumny: {e}")
                    print("\n💡 Alternatywne rozwiązanie:")
                    print("   1. Zatrzymaj aplikację")
                    print("   2. Usuń plik: instance/admin.db")
                    print("   3. Uruchom: python init_db.py")
                    print("   4. Uruchom aplikację ponownie")
                    raise
                    
        except Exception as e:
            print(f"❌ Błąd: {e}")
            raise

if __name__ == '__main__':
    print("=" * 60)
    print("AKTUALIZACJA BAZY DANYCH")
    print("=" * 60)
    upgrade_database()
    print("=" * 60)

