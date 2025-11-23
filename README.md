# System Wykrywania Telefonów

Nowoczesna aplikacja webowa do wykrywania i zarządzania użyciem telefonów w obszarach ograniczonych z priorytetem prywatności.

## Funkcje

- **Wykrywanie telefonów w czasie rzeczywistym** przy użyciu YOLOv8
- **Anonimizacja głów** dla prywatności (zamazuje cały region głowy przy użyciu Roboflow AI)
- Nowoczesny, responsywny panel webowy (React + TypeScript)
- Historia detekcji i zarządzanie
- Konfigurowalne ustawienia kamery i harmonogramy tygodniowe
- **Strefy ROI** - definiuj wiele stref detekcji z wyciszaniem per-strefa
- **Wiele kanałów powiadomień:**
  - **Email** z załączonym zanonimizowanym obrazem (przez Yagmail)
  - **SMS** z linkiem do obrazu (przez Vonage)
- Integracja z Cloudinary do przechowywania obrazów w chmurze
- Uwierzytelnianie i autoryzacja użytkowników
- **Kolejka przetwarzania offline** dla nieblokującej detekcji

## Struktura Projektu

```
Detection-phone/
├── app.py                    # Serwer backend Flask
├── camera_controller.py      # Logika kamery i detekcji
├── models.py                 # Modele bazy danych
├── requirements.txt          # Zależności Pythona
├── package.json              # Zależności Node.js (frontend)
├── src/                      # Źródła frontendu React
│   ├── components/           # Komponenty React
│   ├── pages/                # Komponenty stron (Dashboard, Detections, Settings, Login)
│   ├── contexts/             # Konteksty React (Auth)
│   └── App.tsx               # Główny komponent aplikacji
├── detections/               # Zapisane obrazy detekcji (zanonimizowane)
├── instance/admin.db         # Baza danych SQLite
└── static/                   # Zasoby statyczne
```

## Wymagania

- **Python 3.8-3.12** (backend)
- **Node.js 14 lub nowszy** (frontend)
- Kamera internetowa (fizyczna lub wirtualna jak Iriun)
- Dostęp do internetu (dla Roboflow AI, powiadomień i przechowywania w chmurze)

## Instalacja i Uruchomienie

### 1. Sklonuj repozytorium
```bash
git clone <repository-url>
cd Detection-phone
```

### 2. Zainstaluj zależności

**Backend (Python):**
```bash
pip install -r requirements.txt
```

**Frontend (React):**
```bash
npm install
```

### 3. Skonfiguruj zmienne środowiskowe
Utwórz plik `.env` w katalogu głównym projektu:

```env
# Konfiguracja Email
GMAIL_USER=twoj_email@gmail.com
GMAIL_APP_PASSWORD=twoje_16_znakowe_haslo_aplikacji
EMAIL_RECIPIENT=odbiorca@example.com

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

Musisz uruchomić **oba** backend i frontend w **osobnych terminalach**:

**Terminal 1 - Backend (Flask):**
```bash
flask run --debug --no-reload
```
Backend będzie działał na `http://localhost:5000`

**Terminal 2 - Frontend (React):**
```bash
npm start
```
Frontend będzie działał na `http://localhost:3000` i przekieruje żądania API do backendu

Aplikacja będzie dostępna pod adresem `http://localhost:3000`

**Domyślne dane logowania:**
- Nazwa użytkownika: `admin`
- Hasło: `admin`

### 5. Skonfiguruj system
1. Zaloguj się do panelu na `http://localhost:3000`
2. Przejdź do **Ustawienia** → Ustaw harmonogram kamery (harmonogram tygodniowy z czasem rozpoczęcia/zakończenia)
3. Skonfiguruj preferencje powiadomień (Email/SMS)
4. Dostosuj próg pewności detekcji telefonów jeśli potrzeba (domyślnie: 0.2)
5. **Zdefiniuj strefy ROI** dla ukierunkowanej detekcji (szczegółowe instrukcje poniżej)
6. System automatycznie rozpocznie wykrywanie telefonów w zaplanowanych godzinach

## Konfiguracja

System może być konfigurowany przez stronę Ustawienia:

- **Harmonogram tygodniowy** - Automatyczna aktywacja kamery na dzień z czasem rozpoczęcia/zakończenia
- **Anonimizacja głów** - Ochrona prywatności (zamazuje cały region głowy przy użyciu Roboflow AI)
- **Pewność detekcji telefonów** - Dostosuj czułość wykrywania telefonów (domyślnie: 0.2, zakres: 0.0-1.0)
- **Kanały powiadomień** (Email, SMS) - Preferencje alertów
- **Wybór kamery** - Wybierz którą kamerę użyć
- **Strefy ROI** - Zdefiniuj wiele stref detekcji z niestandardowymi nazwami (patrz poniżej)

### Konfiguracja Stref ROI

**Strefy ROI (Region of Interest)** pozwalają zdefiniować konkretne obszary, w których powinna występować detekcja telefonów. Jest to **bardzo zalecane** dla środowisk klasowych/biurowych.

**Korzyści:**
- ✅ Monitoruj konkretne miejsca/ławki
- ✅ Ignoruj obszary, gdzie telefony są dozwolone (np. biurko nauczyciela)
- ✅ Zmniejsz fałszywe alarmy z obiektów w tle
- ✅ Wyciszanie alertów per-strefa (zapobiega spamowi)

**Przewodnik krok po kroku:**

1. **Załaduj Zdjęcie Konfiguracyjne:**
   - Przejdź do Ustawienia → Sekcja Strefy ROI
   - Kliknij przycisk "Załaduj Zdjęcie Konfiguracyjne"
   - System przechwytuje aktualny widok kamery jako tło

2. **Wybierz Tryb Rysowania:**
   - **Pojedyncza Strefa**: Rysuj pojedyncze strefy jedna po drugiej
   - **Generator Siatki**: Narysuj jeden prostokąt i automatycznie wygeneruj siatkę (idealne dla klas!)

3. **Rysowanie Pojedynczej Strefy:**
   - Kliknij i przeciągnij na obrazie, aby narysować prostokąt
   - Zwolnij mysz, aby zakończyć
   - Wprowadź nazwę strefy (np. "Ławka 1", "Rząd 2 - Miejsce 3")
   - Kliknij "Zapisz Strefę"

4. **Generator Siatki (Zalecane dla Klas):**
   - Narysuj jeden duży prostokąt pokrywający wszystkie miejsca
   - Ustaw wiersze (np. 4) i kolumny (np. 5)
   - Wybierz tryb nazewnictwa:
     - **Sekwencyjne**: "Ławka 1", "Ławka 2", ..., "Ławka 20"
     - **Siatka**: "R1-M1", "R1-M2", ..., "R4-M5"
   - Opcjonalnie: Dodaj prefiks (np. "Ławka")
   - Kliknij "Wygeneruj Siatkę" → Tworzy 20 stref automatycznie!

5. **Edycja Stref:**
   - **Przenieś**: Kliknij i przeciągnij strefę
   - **Zmień rozmiar**: Przeciągnij uchwyty narożników
   - **Zmień nazwę**: Kliknij ikonę edycji (✏️)
   - **Usuń**: Kliknij ikonę usuwania (🗑️)

6. **Auto-Zapis:**
   - Strefy automatycznie zapisują się 2 sekundy po zmianach
   - Zielone powiadomienie potwierdza zapis

**Wyciszanie Per-Strefa:**

Każda strefa ma **niezależne 5-minutowe wyciszanie alertów**:

```
Przykład:
14:00 - Telefon w "Ławka 1" → Alert wysłany, "Ławka 1" wyciszona na 5 min
14:01 - Telefon w "Ławka 2" → Alert wysłany (osobne wyciszanie)
14:02 - Telefon w "Ławka 1" → Zignorowany (nadal wyciszona)
14:06 - Telefon w "Ławka 1" → Alert wysłany (wyciszanie wygasło)
```

**Przykładowa Konfiguracja Klasowa:**

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

### Konfiguracja Powiadomień

Szczegółowe instrukcje konfiguracji:
- **Powiadomienia Email**: Zobacz [EMAIL_NOTIFICATIONS_SETUP.md](EMAIL_NOTIFICATIONS_SETUP.md)
- **Powiadomienia SMS**: Zobacz [SMS_NOTIFICATIONS_SETUP.md](SMS_NOTIFICATIONS_SETUP.md)

## Jak To Działa

System używa wzorca **Producer-Consumer** dla wydajnej, nieblokującej detekcji:

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

1. **Detekcja Telefonów w Czasie Rzeczywistym (Wątek Główny)**: 
   - Kamera przechwytuje klatki z prędkością 20-30 FPS
   - YOLOv8 wykrywa telefony natychmiast
   - Zapisuje oryginalną klatkę na dysk
   - Dodaje do kolejki przetwarzania

2. **Anonimizacja Głów Offline (Wątek Workera)**: 
   - Przetwarza kolejkę asynchronicznie
   - Wykrywa głowy przy użyciu modelu Roboflow AI (pewność ≥ 40%)
   - Zamazuje cały region głowy rozmyciem Gaussa (99x99, sigma=30)
   - Nadpisuje oryginalny plik zanonimizowaną wersją
   - Zapisuje do bazy danych (tylko zanonimizowane obrazy!)
   - Wysyła powiadomienia jeśli włączone

3. **Strefy ROI i Wyciszanie**:
   - Zdefiniuj wiele stref detekcji (np. "ławka 1", "ławka 2")
   - Wyciszanie per-strefa na 5 minut zapobiega spamowi alertów
   - Detekcje poza strefami są ignorowane

Ta architektura zapewnia:
- ✅ Detekcję telefonów w czasie rzeczywistym z prędkością 20-30 FPS (nie blokowana przez anonimizację)
- ✅ Dokładne wykrywanie głów przy użyciu Roboflow AI (dokładność 90%+)
- ✅ Baza danych zawiera **tylko** zanonimizowane obrazy
- ✅ Operacje nieblokujące
- ✅ Projekt z priorytetem prywatności

Szczegółowa architektura systemu: zobacz [README_SYSTEM.md](README_SYSTEM.md)

## Stos Technologiczny

### Backend

- **Flask** - Framework webowy z ORM SQLAlchemy
- **SQLite** - Baza danych
- **YOLOv8** - Detekcja telefonów (Ultralytics)
- **Roboflow AI** - Wykrywanie głów do anonimizacji
- **OpenCV** - Przetwarzanie obrazu i rozmycie Gaussa
- **Cloudinary** - Przechowywanie obrazów w chmurze
- **Vonage API** - Powiadomienia SMS
- **Yagmail** - Powiadomienia Email
- **Threading** - Nieblokująca kolejka przetwarzania

### Frontend

- **React 18** z **TypeScript**
- **Material-UI (MUI)** - Komponenty UI
- **React Router** - Nawigacja
- **Recharts** - Wizualizacja danych
- **Axios** - Klient HTTP
- **Chart.js** - Dodatkowe wykresy

## Prywatność i Bezpieczeństwo

- **Uwierzytelnianie JWT** - Bezpieczne sesje użytkowników
- **Bezpieczne przechowywanie haseł** (hashowane z Werkzeug)
- **Zarządzanie kluczami API** przez zmienne środowiskowe
- **Projekt z priorytetem prywatności**:
  - Oryginalne klatki są zapisywane tymczasowo
  - Głowy są wykrywane i zamazywane przy użyciu Roboflow AI
  - Oryginalne pliki są **nadpisywane** zanonimizowanymi wersjami
  - Baza danych zawiera **tylko** zanonimizowane obrazy
  - Rozmycie Gaussa (99x99) jest nieodwracalne
- **Gotowe wsparcie HTTPS**

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
- Zdefiniuj strefy ROI, aby ograniczyć detekcję do konkretnych obszarów

### Frontend nie łączy się z backendem
- Upewnij się, że zarówno Flask (port 5000) jak i React (port 3000) działają
- Sprawdź, czy `proxy` jest ustawione na `http://localhost:5000` w `package.json`
- Zweryfikuj, czy CORS jest włączone w backendzie Flask (powinno być automatyczne)
- Sprawdź konsolę przeglądarki pod kątem błędów CORS

### Powiadomienia nie działają
- **Email**: Zweryfikuj, czy Hasło Aplikacji Gmail jest poprawne (16 znaków, bez spacji)
- **SMS**: Sprawdź dane uwierzytelniające API Vonage i format numeru telefonu
- **Cloudinary**: Zweryfikuj nazwę chmury, klucz API i sekret API
- Sprawdź logi konsoli pod kątem szczegółowych komunikatów o błędach

## Licencja

MIT License
