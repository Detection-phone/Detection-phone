# Kontekst Projektu - System Wykrywania Smartfonów w Klasach

## Opis Projektu
Tworzę aplikację do automatycznego wykrywania używania smartfonów w klasach szkolnych. System ma na celu pomóc nauczycielom w monitorowaniu i ograniczaniu nieautoryzowanego używania telefonów podczas zajęć, co ma zwiększyć efektywność nauczania.

## Architektura Techniczna

### Backend (Python/Flask)
- **Główna aplikacja**: `app.py` - serwer Flask z API REST
- **Kontroler kamery**: `camera_controller.py` - zarządzanie kamerą i detekcją w czasie rzeczywistym
- **Modele danych**: `models.py` - SQLAlchemy ORM dla użytkowników i detekcji
- **Baza danych**: SQLite z migracjami Alembic
- **Autentykacja**: Flask-Login (nie JWT)

### Frontend
- **Główny interfejs**: HTML templates w folderze `templates/` (dashboard, detections, settings, login)
- **React frontend**: Przygotowany w `src/` z Material-UI (Dashboard, Settings, Detections, Login)
- **Styling**: CSS w `static/css/`

### AI/ML Komponenty
- **YOLOv8**: Dwa modele - YOLOv8m (camera_controller) i YOLOv8n (app.py)
- **OpenCV**: Przetwarzanie obrazu i zarządzanie kamerą
- **Haarcascade**: Automatyczne rozmywanie twarzy dla prywatności

## Kluczowe Funkcjonalności

### 1. System Detekcji w Czasie Rzeczywistym
- Kamera działa w trybie ciągłym w skonfigurowanych godzinach
- Przetwarzanie co 5 klatek dla optymalizacji wydajności
- Konfigurowalny próg pewności detekcji (domyślnie 0.2)
- Automatyczne rozmywanie twarzy w wykrytych obrazach

### 2. Zaawansowane Zarządzanie Kamerami
- Automatyczne skanowanie dostępnych kamer
- Robustny system otwierania kamer z fallback backends (DirectShow, MSMF, V4L2)
- Obsługa wielu kamer z automatycznym przełączaniem
- Konfigurowalne parametry (rozdzielczość, FPS)

### 3. System Harmonogramów
- Konfigurowalne godziny pracy kamery
- Automatyczne uruchamianie/zatrzymywanie w określonych godzinach
- Sprawdzanie harmonogramu w tle
- Obsługa różnych stref czasowych

### 4. System Powiadomień
- **Email**: SMTP notifications z konfigurowalnymi szablonami
- **SMS**: Vonage API dla powiadomień SMS
- System retry dla nieudanych wysyłek
- Konfigurowalne priorytety powiadomień

### 5. Zarządzanie Danymi
- Przechowywanie obrazów detekcji w folderze `detections/`
- System kolejkowania detekcji
- Baza danych SQLite z migracjami
- Automatyczne zarządzanie plikami

## Struktura Plików
```
Detection-phone/
├── app.py                    # Główna aplikacja Flask
├── camera_controller.py     # Kontroler kamery i detekcji
├── models.py                # Modele bazy danych
├── requirements.txt         # Zależności Python
├── package.json            # Zależności Node.js
├── templates/              # HTML templates (główny interfejs)
│   ├── base.html
│   ├── dashboard.html
│   ├── detections.html
│   ├── login.html
│   └── settings.html
├── src/                    # React frontend (przygotowany)
│   ├── App.tsx
│   ├── components/Layout.tsx
│   ├── contexts/AuthContext.tsx
│   └── pages/ (Dashboard, Settings, Detections, Login)
├── static/css/            # Style CSS
├── detections/            # Obrazy detekcji
├── instance/              # Baza danych SQLite
├── migrations/            # Migracje Alembic
└── uploads/               # Pliki uploadowane
```

## Technologie i Biblioteki

### Backend
- **Flask 3.0.2** - framework webowy
- **Flask-SQLAlchemy 3.1.1** - ORM
- **Flask-Login 0.6.3** - autentykacja
- **OpenCV 4.9.0.80** - przetwarzanie obrazu
- **Ultralytics 8.1.2** - YOLOv8
- **Vonage 3.2.0** - SMS API
- **Alembic** - migracje bazy danych

### Frontend
- **React 18.2.0** z TypeScript
- **Material-UI 5.15.10** - komponenty UI
- **React Router 6.22.1** - routing
- **Recharts** - wykresy i wizualizacje
- **Axios** - komunikacja z API

## Status Implementacji

### ✅ W pełni zaimplementowane:
- System detekcji w czasie rzeczywistym
- Zarządzanie kamerami z fallback
- System harmonogramów
- Powiadomienia email/SMS
- Baza danych z migracjami
- HTML interface (dashboard, settings, detections)
- Autentykacja użytkowników
- System kolejkowania detekcji

### 🔄 Przygotowane, wymaga integracji:
- React frontend (kompletny kod w `src/`)
- Material-UI komponenty
- TypeScript interfaces

### ❌ Nie zaimplementowane:
- Google Drive integration (wymienione w dokumentacji)
- Telegram notifications
- JWT authentication (używane Flask-Login)

## Konfiguracja i Uruchomienie

### Wymagania:
- Python 3.8+
- Node.js 14+ (dla React)
- Kamera internetowa
- Windows/Linux/macOS

### Instalacja:
```bash
# Backend
pip install -r requirements.txt
python init_db.py
python app.py

# Frontend (opcjonalnie)
npm install
npm start
```

### Konfiguracja:
- Harmonogram pracy kamery
- Próg pewności detekcji
- Włączanie/wyłączanie rozmywania twarzy
- Konfiguracja powiadomień
- Wybór kamery

## Główne Wyzwania Techniczne

1. **Robustne zarządzanie kamerami** - różne backends, fallback mechanizmy
2. **Optymalizacja wydajności** - przetwarzanie co 5 klatek, kolejkowanie detekcji
3. **Synchronizacja czasu** - harmonogramy, strefy czasowe
4. **Zarządzanie pamięcią** - duże obrazy, automatyczne czyszczenie
5. **Bezpieczeństwo** - rozmywanie twarzy, autentykacja, logowanie

## Przypadki Użycia

1. **Nauczyciel** loguje się do systemu, konfiguruje harmonogram pracy kamery
2. **System** automatycznie uruchamia kamerę w określonych godzinach
3. **Kamera** wykrywa smartfony w czasie rzeczywistym, rozmywa twarze
4. **System** zapisuje detekcje, wysyła powiadomienia
5. **Administrator** przegląda historię detekcji, zarządza ustawieniami

## Możliwości Rozwoju

1. **Integracja z Google Drive** - automatyczne backup obrazów
2. **Telegram notifications** - dodatkowy kanał powiadomień
3. **Wykrywanie innych przedmiotów** - rozszerzenie poza smartfony
4. **Analytics i raporty** - statystyki użycia, trendy
5. **Integracja z systemami szkolnymi** - LMS, dzienniki elektroniczne

## Aspekty Prawne i Etyczne

- Automatyczne rozmywanie twarzy dla ochrony prywatności
- Konfigurowalne harmonogramy zgodne z przepisami
- Audit trail wszystkich działań
- Zgodność z RODO
- Przejrzysta polityka prywatności

Ten system jest gotowy do wdrożenia w szkołach z podstawową funkcjonalnością. React frontend może być łatwo zintegrowany jako nowoczesna alternatywa dla HTML templates.
