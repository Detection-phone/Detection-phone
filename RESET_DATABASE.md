# 🔄 Reset Bazy Danych - Instrukcja

## ⚠️ UWAGA
**Ta operacja usuwa WSZYSTKIE dane z bazy danych!** (użytkownicy, detekcje, ustawienia)

---

## 📋 Metoda 1: Automatyczny skrypt (ZALECANE)

### Krok 1: Zatrzymaj aplikację Flask
Upewnij się, że aplikacja Flask NIE jest uruchomiona (Ctrl+C w terminalu).

### Krok 2: Uruchom skrypt resetujący
```bash
cd C:\Users\askik\Desktop\Phone_detection\Detection-phone
python reset_db.py
```

### Krok 3: Potwierdź reset
Wpisz `tak` gdy zostaniesz zapytany.

### Krok 4: Uruchom migracje
```bash
flask db upgrade
```

### Krok 5: Utwórz użytkownika admin
```bash
python init_db.py
```

### Krok 6: Uruchom aplikację
```bash
python app.py
```

---

## 📋 Metoda 2: Ręczny reset (dla zaawansowanych)

### Krok 1: Zatrzymaj aplikację Flask

### Krok 2: Usuń plik bazy danych
```bash
# Windows PowerShell
Remove-Item "instance\admin.db"

# Lub ręcznie:
# Usuń plik: Detection-phone\instance\admin.db
```

### Krok 3: Zresetuj historię migracji Alembic

**Opcja A: Usuń tylko tabelę `alembic_version` (jeśli baza jeszcze istnieje)**
```bash
python -c "from app import app, db; import sqlalchemy; app.app_context().push(); db.engine.execute(sqlalchemy.text('DROP TABLE IF EXISTS alembic_version')); print('✅ Tabela alembic_version usunięta')"
```

**Opcja B: Całkowite usunięcie bazy (jeśli używasz metody 2)**
Baza już została usunięta w kroku 2.

### Krok 4: Utwórz nową bazę i uruchom migracje
```bash
# Uruchom migracje (stworzy nową bazę)
flask db upgrade

# Utwórz użytkownika admin
python init_db.py
```

---

## 🔍 Weryfikacja

Po resecie sprawdź:

1. **Plik bazy istnieje:**
   ```bash
   # Windows
   dir instance\admin.db
   ```

2. **Tabele zostały utworzone:**
   ```bash
   python -c "from app import app, db; app.app_context().push(); print('Tabele:', db.engine.table_names())"
   ```

3. **Użytkownik admin istnieje:**
   ```bash
   python -c "from app import app, db, User; app.app_context().push(); admin = User.query.filter_by(username='admin').first(); print('Admin:', '✅ Istnieje' if admin else '❌ Brak')"
   ```

---

## 🐛 Rozwiązywanie problemów

### Problem: "table already exists"
**Rozwiązanie:** Upewnij się, że plik `instance/admin.db` został usunięty przed uruchomieniem migracji.

### Problem: "No such file or directory: instance/admin.db"
**Rozwiązanie:** To jest OK - Flask utworzy nowy plik przy pierwszej migracji.

### Problem: "Target database is not up to date"
**Rozwiązanie:** 
```bash
flask db stamp head  # Oznacz jako aktualną
flask db upgrade     # Uruchom migracje
```

---

## ✅ Po udanym resecie

Twoja baza danych będzie miała:
- ✅ Tabela `user` z użytkownikiem `admin` (hasło: `admin`)
- ✅ Tabela `detection` (pusta)
- ✅ Tabela `settings` (z domyślnym harmonogramem)
- ✅ Tabela `alembic_version` (historia migracji)

**Dane logowania po resecie:**
- Username: `admin`
- Password: `admin`

---

## 📝 Notatki

- Po resecie **wszystkie detekcje zostaną usunięte**
- Po resecie **wszyscy użytkownicy zostaną usunięci** (trzeba utworzyć admin przez `init_db.py`)
- Harmonogram zostanie zresetowany do domyślnych wartości (Mon-Fri 07:00-16:00)

