# Instrukcja Integracji Systemu Wykrywania Smartfonów w Szkole

Ten dokument opisuje, jak zintegrować system wykrywania smartfonów w środowisku szkolnym. System został zaprojektowany z myślą o szkołach podstawowych, gdzie problem nieodpowiedniego korzystania ze smartfonów podczas zajęć jest szczególnie widoczny.

## Wymagania Wstępne

Przed rozpoczęciem integracji upewnij się, że masz:

- Komputer z systemem Windows 10 lub nowszym
- Kamerę internetową (może być wbudowana w laptopa lub zewnętrzna)
- Dostęp do internetu (wymagany dla Roboflow AI i powiadomień)
- Python 3.8-3.12 zainstalowany
- Node.js 14 lub nowszy zainstalowany
- Konto Gmail (dla powiadomień email, opcjonalne)
- Konto Cloudinary (dla przechowywania zdjęć w chmurze, opcjonalne)

## Krok 1: Instalacja Systemu

### 1.1 Pobranie Projektu

Sklonuj repozytorium lub pobierz pliki projektu do wybranego katalogu:

```bash
cd C:\Users\TwojaNazwa\Desktop
git clone <repository-url>
cd Detection-phone
```

### 1.2 Instalacja Zależności Backend

Zainstaluj wszystkie wymagane biblioteki Pythona:

```bash
pip install -r requirements.txt
```

Jeśli masz problemy z uprawnieniami na Windows:

```bash
pip install --user -r requirements.txt
```

### 1.3 Instalacja Zależności Frontend

Zainstaluj pakiety Node.js:

```bash
npm install
```

## Krok 2: Konfiguracja Zmiennych Środowiskowych

Utwórz plik `.env` w głównym katalogu projektu. Ten plik zawiera wrażliwe dane, więc nie commituj go do repozytorium.

### 2.1 Konfiguracja Email (Opcjonalne)

Jeśli chcesz otrzymywać powiadomienia email:

```env
GMAIL_USER=twoj_email@gmail.com
GMAIL_APP_PASSWORD=twoje_16_znakowe_haslo_aplikacji
EMAIL_RECIPIENT=nauczyciel@szkola.pl
```

Jak uzyskać Hasło Aplikacji Gmail:
1. Zaloguj się do konta Google
2. Przejdź do Ustawienia konta → Zabezpieczenia
3. Włącz weryfikację dwuetapową (jeśli nie jest włączona)
4. Przejdź do "Hasła aplikacji"
5. Wygeneruj nowe hasło dla aplikacji
6. Skopiuj 16-znakowe hasło (bez spacji)

### 2.2 Konfiguracja Cloudinary (Opcjonalne)

Cloudinary służy do przechowywania zdjęć w chmurze. Jeśli nie chcesz używać chmury, system będzie przechowywał zdjęcia lokalnie.

```env
CLOUDINARY_CLOUD_NAME=twoja_nazwa_chmury
CLOUDINARY_API_KEY=twoj_klucz_api
CLOUDINARY_API_SECRET=twoj_sekret_api
```

Jak uzyskać dane Cloudinary:
1. Zarejestruj się na cloudinary.com
2. Przejdź do Dashboard
3. Skopiuj Cloud Name, API Key i API Secret

### 2.3 Konfiguracja SMS (Opcjonalne)

Jeśli chcesz otrzymywać powiadomienia SMS:

```env
VONAGE_API_KEY=twoj_klucz_vonage
VONAGE_API_SECRET=twoj_sekret_vonage
VONAGE_FROM_NUMBER=PhoneDetection
VONAGE_TO_NUMBER=48123456789
```

Jak uzyskać dane Vonage:
1. Zarejestruj się na vonage.com
2. Przejdź do Dashboard
3. Skopiuj API Key i API Secret
4. Wpisz numer telefonu w formacie międzynarodowym (bez +)

## Krok 3: Inicjalizacja Bazy Danych

Przed pierwszym uruchomieniem musisz zainicjalizować bazę danych:

```bash
python init_db.py
```

To utworzy plik `instance/admin.db` z domyślnym kontem administratora:
- Nazwa użytkownika: `admin`
- Hasło: `admin`

WAŻNE: Zmień hasło administratora po pierwszym logowaniu!

## Krok 4: Uruchomienie Systemu

System składa się z dwóch części - backendu (Flask) i frontendu (React). Musisz uruchomić oba w osobnych terminalach.

### 4.1 Terminal 1 - Backend (Flask)

```bash
cd Detection-phone
flask run --debug --no-reload
```

Backend będzie działał na `http://localhost:5000`

### 4.2 Terminal 2 - Frontend (React)

```bash
cd Detection-phone
npm start
```

Frontend będzie działał na `http://localhost:3000` i automatycznie otworzy się w przeglądarce.

## Krok 5: Konfiguracja Systemu dla Środowiska Szkolnego

### 5.1 Logowanie

1. Otwórz przeglądarkę i przejdź do `http://localhost:3000`
2. Zaloguj się używając domyślnych danych:
   - Nazwa użytkownika: `admin`
   - Hasło: `admin`
3. ZMIEŃ HASŁO w ustawieniach po pierwszym logowaniu!

### 5.2 Konfiguracja Harmonogramu Kamery

Harmonogram pozwala automatycznie włączać i wyłączać kamerę zgodnie z planem lekcji.

1. Przejdź do Ustawienia → Harmonogram Kamery
2. Dla każdego dnia tygodnia ustaw:
   - Czas rozpoczęcia - kiedy kamera ma się włączyć (np. 8:00)
   - Czas zakończenia - kiedy kamera ma się wyłączyć (np. 14:00)
3. Możesz ustawić różne godziny dla różnych dni (np. w piątek lekcje kończą się wcześniej)

Przykład dla typowej szkoły podstawowej:
- Poniedziałek - Piątek: 8:00 - 14:00
- Sobota - Niedziela: wyłączone

### 5.3 Konfiguracja Stref ROI (Region of Interest)

Strefy ROI pozwalają definiować konkretne miejsca w klasie, gdzie powinna występować detekcja telefonów. To jest szczególnie przydatne w szkołach, gdzie chcemy monitorować konkretne ławki.

Krok po kroku:

1. Załaduj Zdjęcie Konfiguracyjne:
   - Przejdź do Ustawienia → Strefy ROI
   - Kliknij przycisk "Załaduj Zdjęcie Konfiguracyjne"
   - System przechwytuje aktualny widok kamery jako tło

2. Użyj Generatora Siatki (Zalecane dla Klas):
   - Narysuj jeden duży prostokąt pokrywający wszystkie miejsca w klasie
   - Ustaw Wiersze (np. 4) i Kolumny (np. 5)
   - Wybierz tryb nazewnictwa:
     - Sekwencyjne: "Ławka 1", "Ławka 2", ..., "Ławka 20"
     - Siatka: "R1-M1", "R1-M2", ..., "R4-M5"
   - Opcjonalnie: Dodaj prefiks (np. "Ławka")
   - Kliknij "Wygeneruj Siatkę" → Tworzy 20 stref automatycznie!

3. Dostosuj Strefy:
   - Przenieś: Kliknij i przeciągnij strefę
   - Zmień rozmiar: Przeciągnij uchwyty narożników
   - Zmień nazwę: Kliknij ikonę edycji
   - Usuń: Kliknij ikonę usuwania

4. Auto-Zapis:
   - Strefy automatycznie zapisują się 2 sekundy po zmianach
   - Zielone powiadomienie potwierdza zapis

Przykładowa Konfiguracja dla Klas:

Dla klasy z 4 rzędami po 5 ławek (20 miejsc):

```
Ustawienia Generatora Siatki:
- Wiersze: 4
- Kolumny: 5
- Tryb Nazewnictwa: Sekwencyjne
- Prefiks: "Ławka"

Wynik: 20 stref z niezależnym wyciszaniem!
```

### 5.4 Konfiguracja Powiadomień

Email:
1. Przejdź do Ustawienia → Powiadomienia
2. Włącz Email Notifications
3. Upewnij się, że w pliku `.env` są poprawne dane Gmail

SMS:
1. Przejdź do Ustawienia → Powiadomienia
2. Włącz SMS Notifications
3. Upewnij się, że w pliku `.env` są poprawne dane Vonage

### 5.5 Konfiguracja Progu Pewności

Próg pewności kontroluje, jak czuły jest system na wykrywanie telefonów.

- Niższe wartości (0.1-0.2): Więcej detekcji, ale możliwe fałszywe alarmy
- Wyższe wartości (0.3-0.5): Mniej detekcji, ale bardziej pewne

Zalecane ustawienie dla szkół: 0.2-0.3

1. Przejdź do Ustawienia → Detection Settings
2. Dostosuj suwak Confidence Threshold
3. Wyższe wartości = mniej fałszywych alarmów

### 5.6 Konfiguracja Anonimizacji

System automatycznie zamazuje głowy uczniów na zdjęciach przed zapisaniem do bazy danych. To jest ważne dla ochrony prywatności.

1. Przejdź do Ustawienia → Privacy Settings
2. Upewnij się, że Blur Faces in Images jest włączone
3. System używa Roboflow AI do wykrywania głów (dokładność 90%+)

## Krok 6: Testowanie Systemu

### 6.1 Test Kamery

1. Przejdź do Dashboard
2. Sprawdź status kamery - powinien być "Online" jeśli harmonogram jest aktywny
3. Jeśli kamera nie startuje, sprawdź:
   - Czy harmonogram jest ustawiony poprawnie
   - Czy żadna inna aplikacja nie używa kamery
   - Czy kamera jest podłączona i działa

### 6.2 Test Detekcji

1. Włącz kamerę ręcznie (jeśli harmonogram nie jest aktywny)
2. Pokaż telefon przed kamerą
3. System powinien wykryć telefon i zapisać zdjęcie
4. Sprawdź Detections - powinieneś zobaczyć nowe wykrycie
5. Otwórz zdjęcie - głowy powinny być zamazane

### 6.3 Test Powiadomień

1. Włącz powiadomienia (Email lub SMS)
2. Wykryj telefon przed kamerą
3. Sprawdź, czy otrzymałeś powiadomienie

## Krok 7: Uruchomienie Produkcyjne

### 7.1 Uruchamianie przy Starcie Systemu

Aby system uruchamiał się automatycznie przy starcie komputera:

Windows (Task Scheduler):
1. Otwórz Task Scheduler
2. Utwórz nowe zadanie
3. Ustaw trigger: "At startup"
4. Ustaw akcję: uruchom `start_backend.bat` i `start_frontend.bat`

Lub użyj PM2 (dla Node.js):
```bash
npm install -g pm2
pm2 start npm --name "phone-detection-frontend" -- start
pm2 startup
pm2 save
```

### 7.2 Bezpieczeństwo

- Zmień domyślne hasło administratora
- Używaj HTTPS w produkcji (certyfikat SSL)
- Regularnie aktualizuj zależności
- Twórz kopie zapasowe bazy danych

### 7.3 Monitoring

- Sprawdzaj regularnie logi systemu
- Monitoruj zużycie dysku (zdjęcia mogą zajmować dużo miejsca)
- Sprawdzaj status kamery w Dashboard

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

### Powiadomienia nie działają
- Email: Zweryfikuj, czy Hasło Aplikacji Gmail jest poprawne (16 znaków, bez spacji)
- SMS: Sprawdź dane uwierzytelniające API Vonage i format numeru telefonu
- Cloudinary: Zweryfikuj nazwę chmury, klucz API i sekret API
- Sprawdź logi konsoli pod kątem szczegółowych komunikatów o błędach

## Wsparcie

Jeśli napotkasz problemy podczas integracji, sprawdź:
- Logi konsoli (backend i frontend)
- Plik `instance/admin.db` (baza danych)
- Folder `detections/` (zapisane zdjęcia)

## Podsumowanie

Po wykonaniu wszystkich kroków system powinien być gotowy do użycia w środowisku szkolnym. Pamiętaj o:
- Regularnym sprawdzaniu statusu systemu
- Tworzeniu kopii zapasowych bazy danych
- Monitorowaniu zużycia dysku
- Aktualizacji hasła administratora
- Informowaniu uczniów o monitorowaniu (zgodnie z przepisami RODO)
