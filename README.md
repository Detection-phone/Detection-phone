# System Wykrywania Smartfonów w Szkołach Podstawowych

Aplikacja do monitorowania użycia telefonów komórkowych przez uczniów podczas zajęć lekcyjnych. System został zaprojektowany z myślą o szkołach podstawowych, gdzie problem nieodpowiedniego korzystania ze smartfonów w czasie lekcji jest szczególnie widoczny.

## Problem

W dzisiejszych czasach uczniowie często korzystają z telefonów podczas zajęć, co negatywnie wpływa na koncentrację i wyniki w nauce. Nauczyciele mają trudności z kontrolowaniem tego zjawiska, szczególnie w większych klasach. System został stworzony, aby pomóc w monitorowaniu tego problemu w sposób automatyczny i obiektywny.

## Funkcje

- Wykrywanie telefonów w czasie rzeczywistym podczas lekcji przy użyciu modelu YOLOv8
- Automatyczna anonimizacja twarzy uczniów dla ochrony prywatności (zamazywanie głów przez Roboflow AI)
- Panel webowy do przeglądania wykryć i zarządzania systemem
- Historia wszystkich detekcji z możliwością eksportu
- Konfigurowalne harmonogramy pracy kamery (dopasowane do planu lekcji)
- Strefy ROI - możliwość definiowania konkretnych miejsc w klasie (ławki, rzędy)
- Powiadomienia dla nauczycieli:
  - Email z załączonym zanonimizowanym zdjęciem
  - SMS z linkiem do zdjęcia
- Integracja z chmurą do przechowywania zdjęć
- System logowania dla nauczycieli i administratorów

## Struktura Projektu

```
Detection-phone/
├── app.py
├── camera_controller.py
├── models.py
├── requirements.txt
├── package.json
├── src/
│   ├── components/
│   ├── pages/
│   ├── contexts/
│   └── App.tsx
├── detections/
├── instance/admin.db
└── static/
```

## Wymagania

- Python 3.8-3.12 (backend)
- Node.js 14 lub nowszy (frontend)
- Kamera internetowa (może być wbudowana w laptopa lub zewnętrzna)
- Dostęp do internetu (dla Roboflow AI, powiadomień i przechowywania w chmurze)

## Instalacja

### 1. Pobierz projekt

```bash
git clone <repository-url>
cd Detection-phone
```

### 2. Zainstaluj zależności

Backend (Python):
```bash
pip install -r requirements.txt
```

Frontend (React):
```bash
npm install
```

### 3. Skonfiguruj zmienne środowiskowe

Utwórz plik `.env` w głównym katalogu:

```env
# Konfiguracja Email
GMAIL_USER=twoj_email@gmail.com
GMAIL_APP_PASSWORD=twoje_16_znakowe_haslo_aplikacji
EMAIL_RECIPIENT=nauczyciel@szkola.pl

# Konfiguracja Cloudinary
CLOUDINARY_CLOUD_NAME=twoja_nazwa_chmury
CLOUDINARY_API_KEY=twoj_klucz_api
CLOUDINARY_API_SECRET=twoj_sekret_api

# Konfiguracja SMS (Opcjonalne)
VONAGE_API_KEY=twoj_klucz_vonage
VONAGE_API_SECRET=twoj_sekret_vonage
VONAGE_FROM_NUMBER=PhoneDetection
VONAGE_TO_NUMBER=48123456789
```

### 4. Uruchom aplikację

Musisz uruchomić backend i frontend w osobnych terminalach:

Terminal 1 - Backend (Flask):
```bash
flask run --debug --no-reload
```
Backend działa na `http://localhost:5000`

Terminal 2 - Frontend (React):
```bash
npm start
```
Frontend działa na `http://localhost:3000`

Aplikacja będzie dostępna pod adresem `http://localhost:3000`

Domyślne dane logowania:
- Nazwa użytkownika: `admin`
- Hasło: `admin`

### 5. Konfiguracja systemu

1. Zaloguj się do panelu na `http://localhost:3000`
2. Przejdź do Ustawienia → Ustaw harmonogram kamery (dopasuj do planu lekcji)
3. Skonfiguruj powiadomienia (Email/SMS) jeśli chcesz otrzymywać alerty
4. Dostosuj próg pewności detekcji telefonów (domyślnie: 0.2)
5. Zdefiniuj strefy ROI dla konkretnych miejsc w klasie (szczegóły poniżej)
6. System automatycznie rozpocznie wykrywanie telefonów w zaplanowanych godzinach

## Konfiguracja

System może być konfigurowany przez stronę Ustawienia:

- Harmonogram tygodniowy - Automatyczna aktywacja kamery na konkretne dni z czasem rozpoczęcia/zakończenia (np. poniedziałek 8:00-14:00)
- Anonimizacja głów - Ochrona prywatności uczniów (zamazywanie głów przez Roboflow AI)
- Pewność detekcji telefonów - Dostosuj czułość wykrywania (domyślnie: 0.2, zakres: 0.0-1.0)
- Kanały powiadomień (Email, SMS) - Preferencje alertów dla nauczycieli
- Wybór kamery - Wybierz którą kamerę użyć (jeśli masz kilka)
- Strefy ROI - Zdefiniuj konkretne miejsca w klasie (patrz poniżej)

### Konfiguracja Stref ROI dla Klas

Strefy ROI (Region of Interest) pozwalają zdefiniować konkretne obszary w klasie, gdzie powinna występować detekcja telefonów. To jest szczególnie przydatne w szkołach, gdzie chcemy monitorować konkretne ławki lub miejsca.

Korzyści:
- Monitoruj konkretne ławki lub rzędy
- Ignoruj obszary, gdzie telefony są dozwolone (np. biurko nauczyciela)
- Zmniejsz fałszywe alarmy z obiektów w tle
- Wyciszanie alertów per-strefa (zapobiega spamowi gdy uczeń ciągle używa telefonu)

Jak to skonfigurować:

1. Załaduj Zdjęcie Konfiguracyjne:
   - Przejdź do Ustawienia → Sekcja Strefy ROI
   - Kliknij przycisk "Załaduj Zdjęcie Konfiguracyjne"
   - System przechwytuje aktualny widok kamery jako tło

2. Wybierz Tryb Rysowania:
   - Pojedyncza Strefa: Rysuj pojedyncze strefy jedna po drugiej
   - Generator Siatki: Narysuj jeden prostokąt i automatycznie wygeneruj siatkę (idealne dla klas!)

3. Rysowanie Pojedynczej Strefy:
   - Kliknij i przeciągnij na obrazie, aby narysować prostokąt
   - Zwolnij mysz, aby zakończyć
   - Wprowadź nazwę strefy (np. "Ławka 1", "Rząd 2 - Miejsce 3")
   - Kliknij "Zapisz Strefę"

4. Generator Siatki (Zalecane dla Klas):
   - Narysuj jeden duży prostokąt pokrywający wszystkie miejsca w klasie
   - Ustaw wiersze (np. 4) i kolumny (np. 5)
   - Wybierz tryb nazewnictwa:
     - Sekwencyjne: "Ławka 1", "Ławka 2", ..., "Ławka 20"
     - Siatka: "R1-M1", "R1-M2", ..., "R4-M5"
   - Opcjonalnie: Dodaj prefiks (np. "Ławka")
   - Kliknij "Wygeneruj Siatkę" → Tworzy 20 stref automatycznie!

5. Edycja Stref:
   - Przenieś: Kliknij i przeciągnij strefę
   - Zmień rozmiar: Przeciągnij uchwyty narożników
   - Zmień nazwę: Kliknij ikonę edycji
   - Usuń: Kliknij ikonę usuwania

6. Auto-Zapis:
   - Strefy automatycznie zapisują się 2 sekundy po zmianach
   - Zielone powiadomienie potwierdza zapis

Wyciszanie Per-Strefa:

Każda strefa ma niezależne 5-minutowe wyciszanie alertów. To zapobiega spamowi, gdy uczeń ciągle używa telefonu:

```
Przykład:
14:00 - Telefon w "Ławka 1" → Alert wysłany, "Ławka 1" wyciszona na 5 min
14:01 - Telefon w "Ławka 2" → Alert wysłany (osobne wyciszanie)
14:02 - Telefon w "Ławka 1" → Zignorowany (nadal wyciszona)
14:06 - Telefon w "Ławka 1" → Alert wysłany (wyciszanie wygasło)
```

Przykładowa Konfiguracja dla Klas:

```
4 wiersze × 5 kolumn = 20 stref

┌─────────┬─────────┬─────────┬─────────┬─────────┐
│ Ławka 1 │ Ławka 2 │ Ławka 3 │ Ławka 4 │ Ławka 5 │
├─────────┼─────────┼─────────┼─────────┼─────────┤
│ Ławka 6 │ Ławka 7 │ Ławka 8 │ Ławka 9 │ Ławka10 │
├─────────┼─────────┼─────────┼─────────┼─────────┤
│ Ławka11 │ Ławka12 │ Ławka13 │ Ławka14 │ Ławka15 │
├─────────┼─────────┼─────────┼─────────┼─────────┤
│ Ławka16 │ Ławka17 │ Ławka18 │ Ławka19 │ Ławka20 │
└─────────┴─────────┴─────────┴─────────┴─────────┘

Ustawienia Generatora Siatki:
- Wiersze: 4
- Kolumny: 5
- Tryb Nazewnictwa: Sekwencyjne
- Prefiks: "Ławka"

Wynik: 20 stref z niezależnym wyciszaniem!
```

## Jak To Działa

System używa wzorca Producer-Consumer dla wydajnej, nieblokującej detekcji:

### Przegląd Architektury

```
┌─────────────────────────────────────────────────────────┐
│         WĄTEK GŁÓWNY - Detekcja w Czasie Rzeczywistym  │
│                                                         │
│  📷 Kamera → 🔍 Detekcja Telefonów (YOLOv8)           │
│                        │                                │
│                        ↓ (telefon wykryty)              │
│                  💾 Zapisz ORYGINALNĄ klatkę            │
│                        │                                │
│                        ↓                                │
│                  📤 Dodaj do Kolejki                   │
└────────────────────────┼────────────────────────────────┘
                         │
                    Kolejka<filepath>
                         │
                         ↓
┌────────────────────────┼────────────────────────────────┐
│         WĄTEK WORKERA - Anonimizacja Głów Offline       │
│                        │                                │
│                  📥 Pobierz z Kolejki                   │
│                        ↓                                │
│            👁️ Wykryj Głowy (Roboflow AI)              │
│                        ↓                                │
│            🔒 Zamazuj Głowy (Gaussian 99x99)           │
│                        ↓                                │
│            💾 Nadpisz zanonimizowaną wersją            │
│                        ↓                                │
│            💾 Zapisz do Bazy Danych                    │
│                        ↓                                │
│            📧 Wyślij Powiadomienia (Email/SMS)        │
└─────────────────────────────────────────────────────────┘
```

### Kluczowe Funkcje:

1. Detekcja Telefonów w Czasie Rzeczywistym (Wątek Główny): 
   - Kamera przechwytuje klatki z prędkością 20-30 FPS
   - YOLOv8 wykrywa telefony natychmiast
   - Zapisuje oryginalną klatkę na dysk
   - Dodaje do kolejki przetwarzania

2. Anonimizacja Głów Offline (Wątek Workera): 
   - Przetwarza kolejkę asynchronicznie
   - Wykrywa głowy przy użyciu modelu Roboflow AI (pewność ≥ 40%)
   - Zamazuje cały region głowy rozmyciem Gaussa (99x99, sigma=30)
   - Nadpisuje oryginalny plik zanonimizowaną wersją
   - Zapisuje do bazy danych (tylko zanonimizowane obrazy!)
   - Wysyła powiadomienia jeśli włączone

3. Strefy ROI i Wyciszanie:
   - Zdefiniuj wiele stref detekcji (np. "ławka 1", "ławka 2")
   - Wyciszanie per-strefa na 5 minut zapobiega spamowi alertów
   - Detekcje poza strefami są ignorowane

Ta architektura zapewnia:
- Detekcję telefonów w czasie rzeczywistym z prędkością 20-30 FPS (nie blokowana przez anonimizację)
- Dokładne wykrywanie głów przy użyciu Roboflow AI (dokładność 90%+)
- Baza danych zawiera tylko zanonimizowane obrazy
- Operacje nieblokujące
- Projekt z priorytetem prywatności uczniów

Szczegółowa architektura systemu: zobacz CURRENT_ARCHITECTURE.md

## Stos Technologiczny

### Backend

- Flask - Framework webowy z ORM SQLAlchemy
- SQLite - Baza danych
- YOLOv8 - Detekcja telefonów (Ultralytics)
- Roboflow AI - Wykrywanie głów do anonimizacji
- OpenCV - Przetwarzanie obrazu i rozmycie Gaussa
- Cloudinary - Przechowywanie obrazów w chmurze
- Vonage API - Powiadomienia SMS
- Yagmail - Powiadomienia Email
- Threading - Nieblokująca kolejka przetwarzania

### Frontend

- React 18 z TypeScript
- Material-UI (MUI) - Komponenty UI
- React Router - Nawigacja
- Recharts - Wizualizacja danych
- Axios - Klient HTTP
- Chart.js - Dodatkowe wykresy

## Prywatność i Bezpieczeństwo

- Uwierzytelnianie JWT - Bezpieczne sesje użytkowników
- Bezpieczne przechowywanie haseł (hashowane z Werkzeug)
- Zarządzanie kluczami API przez zmienne środowiskowe
- Projekt z priorytetem prywatności uczniów:
  - Oryginalne klatki są zapisywane tymczasowo
  - Głowy są wykrywane i zamazywane przy użyciu Roboflow AI
  - Oryginalne pliki są nadpisywane zanonimizowanymi wersjami
  - Baza danych zawiera tylko zanonimizowane obrazy
  - Rozmycie Gaussa (99x99) jest nieodwracalne
- Gotowe wsparcie HTTPS

## Rozwiązywanie Problemów

### Kamera nie startuje
- Sprawdź uprawnienia kamery w ustawieniach Windows
- Zweryfikuj, czy harmonogram kamery jest ustawiony poprawnie
- Upewnij się, że żadna inna aplikacja nie używa kamery (zamknij Zoom, Teams, OBS, itp.)
- Spróbuj zrestartować serwer Flask

### Głowy nie są zamazywane
- System używa Roboflow AI do wykrywania głów (dokładność 90%+)
- Sprawdź, czy anonimizacja głów jest włączona w Ustawieniach
- Zweryfikuj połączenie internetowe (Roboflow wymaga dostępu do API)
- Sprawdź logi konsoli pod kątem błędów API Roboflow

### Zbyt wiele fałszywych detekcji telefonów
- Zwiększ próg pewności detekcji telefonów w Ustawieniach (domyślnie: 0.2)
- Wyższe wartości = mniej fałszywych alarmów (spróbuj 0.3-0.5)
- Zdefiniuj strefy ROI, aby ograniczyć detekcję do konkretnych obszarów w klasie

### Frontend nie łączy się z backendem
- Upewnij się, że zarówno Flask (port 5000) jak i React (port 3000) działają
- Sprawdź, czy `proxy` jest ustawione na `http://localhost:5000` w `package.json`
- Zweryfikuj, czy CORS jest włączone w backendzie Flask (powinno być automatyczne)
- Sprawdź konsolę przeglądarki pod kątem błędów CORS

### Powiadomienia nie działają
- Email: Zweryfikuj, czy Hasło Aplikacji Gmail jest poprawne (16 znaków, bez spacji)
- SMS: Sprawdź dane uwierzytelniające API Vonage i format numeru telefonu
- Cloudinary: Zweryfikuj nazwę chmury, klucz API i sekret API
- Sprawdź logi konsoli pod kątem szczegółowych komunikatów o błędach

## Licencja

MIT License
