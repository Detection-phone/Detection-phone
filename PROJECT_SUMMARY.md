# Podsumowanie Projektu - System Wykrywania Smartfonów

## 1. Cel projektu (Project Goal)
System został zaprojektowany do automatycznego wykrywania używania smartfonów w klasach szkolnych. Główne cele to:
- Monitorowanie i ograniczanie nieautoryzowanego używania telefonów podczas zajęć
- Automatyczne wykrywanie smartfonów w czasie rzeczywistym
- Zapewnienie nauczycielom narzędzia do efektywnego zarządzania używaniem telefonów
- Zwiększenie efektywności nauczania poprzez ograniczenie rozpraszających czynników

## 2. Opis działania systemu (System Operation)
System działa w następujący sposób:

1. **Inicjalizacja i konfiguracja:**
   - System uruchamia się z konfigurowalnymi parametrami (godziny pracy, próg pewności detekcji)
   - Automatycznie wykrywa dostępne kamery i ich parametry
   - Ładuje model YOLOv8 do detekcji obiektów (YOLOv8m w camera_controller, YOLOv8n w app.py)

2. **Proces detekcji:**
   - Kamera działa w trybie ciągłym w skonfigurowanych godzinach
   - Każda klatka jest przetwarzana przez model YOLOv8 co 5 klatek
   - System wykrywa smartfony z konfigurowalnym progiem pewności (domyślnie 0.2)
   - Wykryte twarze są automatycznie rozmywane dla zachowania prywatności (Haarcascade)

3. **Obsługa wykryć:**
   - Wykrycia są zapisywane w bazie danych SQLite
   - System może wysyłać powiadomienia przez email i SMS (Vonage API)
   - Dane są przechowywane lokalnie w folderze `detections/`
   - Implementowany system kolejkowania detekcji

## 3. Zastosowane technologie (Technologies Used)
- **Języki programowania:**
  - Python (backend)
  - TypeScript/JavaScript (frontend React - przygotowany)
  - HTML/CSS (główny interfejs)
  - SQL (baza danych)

- **Biblioteki i frameworki:**
  - Flask (backend)
  - React (frontend - przygotowany, ale główny interfejs to HTML templates)
  - Material-UI (interfejs użytkownika React)
  - YOLOv8 (detekcja obiektów)
  - OpenCV (przetwarzanie obrazu)
  - SQLite (baza danych)
  - Flask-SQLAlchemy (ORM)
  - Flask-Login (autentykacja)
  - Alembic (migracje bazy danych)

- **Modele AI:**
  - YOLOv8m (model do detekcji obiektów - camera_controller)
  - YOLOv8n (model do detekcji obiektów - app.py)
  - Haarcascade (wykrywanie twarzy)

## 4. Architektura rozwiązania (Solution Architecture)
System składa się z następujących głównych komponentów:

1. **Moduł detekcji (camera_controller.py):**
   - Zarządzanie kamerą z robustnym systemem fallback
   - Przetwarzanie obrazu w czasie rzeczywistym
   - Wykrywanie obiektów YOLOv8
   - Zarządzanie harmonogramem pracy
   - System kolejkowania detekcji
   - Automatyczne skanowanie dostępnych kamer

2. **Backend (app.py):**
   - API REST Flask
   - Zarządzanie użytkownikami (Flask-Login)
   - Obsługa bazy danych (SQLAlchemy)
   - Integracja z zewnętrznymi usługami (Vonage SMS)
   - Serwowanie obrazów detekcji

3. **Frontend:**
   - **Główny interfejs**: HTML templates w `templates/`
   - **React frontend**: Przygotowany w `src/` (Dashboard, Settings, Detections, Login)
   - Panel administracyjny z Material-UI
   - Wizualizacja danych (Recharts)
   - Konfiguracja systemu

4. **Baza danych:**
   - SQLite z SQLAlchemy ORM
   - Migracje Alembic
   - Przechowywanie wykryć i użytkowników
   - Konfiguracja systemu

## 5. Kluczowe funkcjonalności (Key Features)

### System kamer:
- Automatyczne wykrywanie dostępnych kamer
- Robustne otwieranie kamer z fallback backends (DirectShow, MSMF, V4L2)
- Obsługa wielu kamer z automatycznym przełączaniem
- Konfigurowalne parametry kamery (rozdzielczość, FPS)

### System detekcji:
- Wykrywanie w czasie rzeczywistym (30+ FPS)
- Konfigurowalny próg pewności detekcji (domyślnie 0.2)
- Automatyczne rozmywanie twarzy
- System kolejkowania detekcji
- Przetwarzanie co 5 klatek dla optymalizacji

### System harmonogramów:
- Konfigurowalne godziny pracy kamery
- Automatyczne uruchamianie/zatrzymywanie
- Sprawdzanie harmonogramu w tle
- Obsługa różnych stref czasowych

### System powiadomień:
- Email notifications (SMTP)
- SMS notifications (Vonage API)
- Konfigurowalne szablony wiadomości
- System retry dla nieudanych wysyłek

## 6. Struktura projektu (Project Structure)
```
Detection-phone/
├── app.py                    # Główna aplikacja Flask
├── camera_controller.py     # Kontroler kamery i detekcji
├── models.py                # Modele bazy danych
├── requirements.txt         # Zależności Python
├── package.json            # Zależności Node.js
├── templates/              # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── detections.html
│   ├── login.html
│   └── settings.html
├── src/                    # React frontend (przygotowany)
│   ├── App.tsx
│   ├── components/
│   ├── contexts/
│   └── pages/
├── static/                 # Pliki statyczne
├── detections/            # Przechowywanie obrazów detekcji
├── instance/              # Konfiguracja bazy danych
├── migrations/            # Migracje Alembic
└── uploads/               # Pliki uploadowane
```

## 7. Konfiguracja i wdrożenie (Configuration and Deployment)

### Wymagania systemowe:
- Python 3.8+
- Node.js 14+ (dla React frontend)
- Kamera internetowa
- System operacyjny: Windows 10/11, Linux, macOS

### Instalacja:
1. Instalacja zależności Python: `pip install -r requirements.txt`
2. Instalacja zależności Node.js: `npm install`
3. Konfiguracja zmiennych środowiskowych (.env)
4. Inicjalizacja bazy danych: `python init_db.py`
5. Uruchomienie: `python app.py`

### Konfiguracja:
- Harmonogram pracy kamery
- Próg pewności detekcji
- Włączanie/wyłączanie rozmywania twarzy
- Konfiguracja powiadomień (email, SMS)
- Wybór kamery

## 8. Bezpieczeństwo i prywatność (Security and Privacy)
- Flask-Login dla autentykacji
- Automatyczne rozmywanie twarzy w detekcjach
- Bezpieczne przechowywanie danych
- Konfigurowalne hasła administratora
- Logowanie aktywności systemu

## 9. Możliwości rozwoju (Development Opportunities)
1. **Rozszerzenia funkcjonalne:**
   - Integracja z Google Drive (przygotowana w dokumentacji)
   - Rozszerzenie o inne zakazane przedmioty
   - Integracja z systemami zarządzania szkołą
   - Telegram notifications

2. **Optymalizacje:**
   - Lżejszy model YOLO dla szybszej detekcji
   - Lepsze zarządzanie zasobami
   - Optymalizacja przechowywania danych
   - Asynchroniczne przetwarzanie

3. **Aspekty prawne i etyczne:**
   - Zgodność z RODO
   - Przejrzysta polityka prywatności
   - Mechanizmy zgody na monitoring
   - Audit trail dla wszystkich działań

## 10. Status implementacji (Implementation Status)
- ✅ **Zaimplementowane**: System detekcji, zarządzanie kamerami, harmonogramy, powiadomienia email/SMS, baza danych, interfejs HTML
- 🔄 **W przygotowaniu**: React frontend (kompletny kod, wymaga integracji)
- ❌ **Nie zaimplementowane**: Google Drive integration, Telegram notifications

System jest gotowy do wdrożenia w szkołach z podstawową funkcjonalnością. React frontend może być łatwo zintegrowany jako alternatywa dla HTML templates.
