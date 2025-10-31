"""
Script do bezpiecznego resetowania bazy danych i migracji Alembic.

UWAGA: Ta operacja usuwa wszystkie dane z bazy danych!
"""

import os
import shutil
from pathlib import Path

def reset_database():
    """Resetuje bazę danych i migracje Alembic"""
    
    print("=" * 60)
    print("🔄 RESET BAZY DANYCH")
    print("=" * 60)
    print()
    print("⚠️  UWAGA: Ta operacja usunie WSZYSTKIE dane z bazy!")
    print()
    
    # Ścieżki do plików
    base_dir = Path(__file__).parent
    db_path = base_dir / "instance" / "admin.db"
    alembic_version_table = "alembic_version"  # Tabela w bazie przechowująca wersje migracji
    
    # 1. Usuń plik bazy danych
    if db_path.exists():
        print(f"📁 Znaleziono bazę danych: {db_path}")
        try:
            db_path.unlink()
            print(f"✅ Usunięto plik bazy danych: {db_path}")
        except Exception as e:
            print(f"❌ Błąd usuwania bazy danych: {e}")
            return False
    else:
        print(f"ℹ️  Baza danych nie istnieje: {db_path}")
    
    # 2. Utwórz katalog instance jeśli nie istnieje
    instance_dir = base_dir / "instance"
    if not instance_dir.exists():
        instance_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Utworzono katalog: {instance_dir}")
    
    print()
    print("=" * 60)
    print("✅ Reset bazy danych zakończony!")
    print("=" * 60)
    print()
    print("📋 NASTĘPNE KROKI:")
    print()
    print("1. Uruchom migracje od nowa:")
    print("   flask db upgrade")
    print()
    print("2. LUB utwórz bazę ręcznie:")
    print("   python init_db.py")
    print()
    print("3. Następnie uruchom aplikację:")
    print("   python app.py")
    print()
    
    return True

if __name__ == '__main__':
    # Potwierdzenie
    response = input("Czy na pewno chcesz zresetować bazę danych? (tak/nie): ")
    if response.lower() in ['tak', 'yes', 'y', 't']:
        reset_database()
    else:
        print("❌ Anulowano reset bazy danych.")

