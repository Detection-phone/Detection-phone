# Przewodnik Konfiguracji - Plik .env

## 📋 Szybki Start

Aby skonfigurować powiadomienia e-mail, utwórz plik `.env` w katalogu `Detection-phone` z następującą zawartością:

```env
# ======================================
# EMAIL NOTIFICATIONS (Yagmail + Gmail)
# ======================================
GMAIL_USER=twoj_email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_RECIPIENT=odbiorca@example.com

# ======================================
# CLOUDINARY (Image Hosting)
# ======================================
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# ======================================
# SMS NOTIFICATIONS (Opcjonalne)
# ======================================
VONAGE_API_KEY=your_vonage_api_key
VONAGE_API_SECRET=your_vonage_api_secret
VONAGE_FROM_NUMBER=PhoneDetection
VONAGE_TO_NUMBER=48123456789
```

## 🔑 Zmienne Środowiskowe - Szczegóły

### Email (Wymagane dla powiadomień e-mail)

| Zmienna | Opis | Przykład |
|---------|------|----------|
| `GMAIL_USER` | Twój adres Gmail | `jan.kowalski@gmail.com` |
| `GMAIL_APP_PASSWORD` | Hasło aplikacji Gmail (16 znaków) | `abcd efgh ijkl mnop` |
| `EMAIL_RECIPIENT` | Adres odbiorcy powiadomień | `security@firma.pl` |

⚠️ **WAŻNE**: `GMAIL_APP_PASSWORD` to NIE zwykłe hasło Gmail!

### Jak wygenerować Gmail App Password?

1. Przejdź do: **https://myaccount.google.com/apppasswords**
2. Zaloguj się na konto Gmail
3. Włącz **weryfikację dwuetapową** (jeśli nie jest włączona)
4. Wróć do App Passwords
5. Wybierz:
   - Aplikacja: **Mail**
   - Urządzenie: **Other** (wpisz: "Phone Detection")
6. Kliknij **Generate**
7. Skopiuj 16-znakowy kod (format: `xxxx xxxx xxxx xxxx`)
8. Wklej do `.env` jako `GMAIL_APP_PASSWORD`

### Cloudinary (Wymagane dla hostingu obrazów)

| Zmienna | Opis | Gdzie znaleźć |
|---------|------|---------------|
| `CLOUDINARY_CLOUD_NAME` | Nazwa chmury | Dashboard → Cloud name |
| `CLOUDINARY_API_KEY` | Klucz API | Dashboard → API Key |
| `CLOUDINARY_API_SECRET` | Sekret API | Dashboard → API Secret |

📍 Dashboard: **https://cloudinary.com/console**

### Vonage (Opcjonalne - dla SMS)

| Zmienna | Opis | Format |
|---------|------|--------|
| `VONAGE_API_KEY` | Klucz API Vonage | `abc123def456` |
| `VONAGE_API_SECRET` | Sekret API Vonage | `1234567890ABCDEF` |
| `VONAGE_FROM_NUMBER` | Nadawca | `PhoneDetection` lub `+48123456789` |
| `VONAGE_TO_NUMBER` | Odbiorca | `48987654321` (BEZ +) |

📍 Dashboard: **https://dashboard.nexmo.com/**

## 📝 Instrukcja Krok po Kroku

### 1. Utwórz plik `.env`

W katalogu `Detection-phone`, utwórz nowy plik o nazwie `.env` (bez żadnego rozszerzenia):

**Windows (PowerShell):**
```powershell
cd Detection-phone
New-Item -Path ".env" -ItemType File
```

**Windows (CMD):**
```cmd
cd Detection-phone
type nul > .env
```

**Linux/Mac:**
```bash
cd Detection-phone
touch .env
```

### 2. Otwórz plik `.env` w edytorze

Możesz użyć:
- Notepad: `notepad .env`
- VS Code: `code .env`
- Dowolny inny edytor tekstu

### 3. Wklej konfigurację

Skopiuj szablon z początku tego dokumentu i wypełnij swoimi danymi.

### 4. Zapisz i uruchom

```bash
python app.py
```

### 5. Sprawdź inicjalizację

W konsoli powinieneś zobaczyć:

```
✅ Cloudinary zainicjalizowane
   Cloud Name: your_cloud_name
✅ Klient Yagmail (Email) zainicjalizowany.
   Wysyłka z: twoj_email@gmail.com
   Odbiorca: recipient@example.com
✅ AnonymizerWorker uruchomiony w tle
```

## ⚠️ Troubleshooting

### Komunikat: "Brak danych Email w zmiennych środowiskowych"

```
⚠️  Brak danych Email w zmiennych środowiskowych (.env)
   Wymagane: GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_RECIPIENT
```

**Rozwiązanie:**
1. Sprawdź czy plik `.env` istnieje w katalogu `Detection-phone`
2. Upewnij się, że wszystkie 3 zmienne są ustawione
3. Sprawdź nazwy zmiennych (wielkość liter ma znaczenie!)
4. Restart aplikacji po zmianie `.env`

### Komunikat: "Błąd inicjalizacji Yagmail"

```
❌ Błąd inicjalizacji Yagmail: (535, b'5.7.8 Username and Password not accepted...')
```

**Przyczyny:**
1. Używasz zwykłego hasła Gmail zamiast App Password
2. App Password wygasło lub zostało odwołane
3. Weryfikacja 2-etapowa nie jest włączona

**Rozwiązanie:**
1. Wygeneruj nowe App Password: https://myaccount.google.com/apppasswords
2. Upewnij się, że weryfikacja 2-etapowa jest włączona
3. Skopiuj App Password bez spacji do `.env`

### Plik .env nie ładuje się

**Sprawdź:**
1. Plik nazywa się dokładnie `.env` (nie `.env.txt` ani `env`)
2. Plik znajduje się w katalogu `Detection-phone` (obok `app.py`)
3. Format zmiennych: `NAZWA=wartość` (bez spacji wokół `=`)
4. Brak cudzysłowów wokół wartości (chyba że są częścią hasła)

**Przykład poprawny:**
```env
GMAIL_USER=jan@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

**Przykład niepoprawny:**
```env
GMAIL_USER = "jan@gmail.com"
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

## 🔒 Bezpieczeństwo

### ✅ ZAWSZE:
- Trzymaj `.env` lokalnie (NIE commituj do git)
- Używaj App Password (nie zwykłego hasła)
- Regularnie rotuj hasła aplikacji
- Dodaj `.env` do `.gitignore` (już zrobione)

### ❌ NIGDY:
- Nie udostępniaj pliku `.env`
- Nie commituj `.env` do repozytorium
- Nie używaj zwykłego hasła Gmail
- Nie wysyłaj `.env` przez email/chat

## 📁 Struktura Plików

Po konfiguracji powinieneś mieć:

```
Detection-phone/
├── .env                          # ⚠️ TWÓJ PLIK (nie w git!)
├── .gitignore                    # Zawiera ".env"
├── app.py
├── camera_controller.py
├── requirements.txt
├── EMAIL_NOTIFICATIONS_SETUP.md
├── ENV_SETUP_GUIDE.md           # Ten plik
└── ...
```

## 🎯 Przykładowy Kompletny .env

Oto przykład w pełni skonfigurowanego pliku `.env`:

```env
# Email Notifications
GMAIL_USER=jan.kowalski@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
EMAIL_RECIPIENT=security@mojafrima.pl

# Cloudinary
CLOUDINARY_CLOUD_NAME=mojacloud
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abc123def456ghi789jkl

# SMS (opcjonalnie)
VONAGE_API_KEY=a1b2c3d4
VONAGE_API_SECRET=1234567890abcdef
VONAGE_FROM_NUMBER=PhoneDetection
VONAGE_TO_NUMBER=48123456789
```

## 📚 Dalsze Kroki

Po skonfigurowaniu `.env`:

1. ✅ Uruchom aplikację: `python app.py`
2. ✅ Sprawdź logi inicjalizacji
3. ✅ Zaloguj się do panelu
4. ✅ Włącz Email Notifications w Settings
5. ✅ Przetestuj detekcję telefonu

## 🆘 Pomoc

Jeśli nadal masz problemy:

1. Zobacz szczegółową dokumentację: `EMAIL_NOTIFICATIONS_SETUP.md`
2. Sprawdź logi w konsoli
3. Upewnij się że `python-dotenv` jest zainstalowane: `pip install python-dotenv`

---

**Ostatnia aktualizacja**: 29 października 2025  
**Status**: ✅ Zaktualizowano do nowych nazw zmiennych (`GMAIL_USER`, `GMAIL_APP_PASSWORD`)

