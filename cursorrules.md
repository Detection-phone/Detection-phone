# Zasady Programowania

## Podstawowe Zasady
1. Zawsze używaj polskiego w komentarzach i dokumentacji
2. Utrzymuj spójną strukturę kodu
3. Dokumentuj zmiany w kodzie
4. Testuj zmiany przed implementacją

## Struktura Projektu
- `app.py` - główna aplikacja Flask
- `config.py` - konfiguracja i modele bazy danych
- `phone_detector.py` - logika detekcji telefonów
- `templates/` - pliki HTML
- `static/` - pliki statyczne (CSS, JS, obrazy)
- `instance/` - pliki konfiguracyjne
- `detections/` - przechowywanie detekcji

## Konwencje Nazewnictwa
- Pliki Python: snake_case (np. `phone_detector.py`)
- Klasy: PascalCase (np. `PhoneDetector`)
- Funkcje: snake_case (np. `detect_phone`)
- Zmienne: snake_case (np. `detection_count`)

## Organizacja Kodu
1. Każdy plik powinien mieć jasny cel
2. Trzymaj powiązaną funkcjonalność razem
3. Używaj znaczących nazw plików i folderów
4. Utrzymuj logiczną strukturę katalogów

## Zasady Bezpieczeństwa
1. Nigdy nie przechowuj wrażliwych danych w kodzie (hasła, klucze API)
2. Używaj zmiennych środowiskowych dla wrażliwych danych
3. Regularnie aktualizuj zależności
4. Sprawdzaj kod pod kątem luk bezpieczeństwa

## Zasady Testowania
1. Testuj nowe funkcje przed implementacją
2. Utrzymuj testy jednostkowe
3. Sprawdzaj funkcjonalność na różnych systemach operacyjnych
4. Dokumentuj znalezione błędy

## Zasady Dokumentacji
1. Dokumentuj wszystkie nowe funkcje
2. Aktualizuj dokumentację przy znaczących zmianach
3. Używaj docstringów w kodzie Python
4. Utrzymuj aktualną dokumentację API

## Zasady Obsługi Powiadomień
1. Formatowanie Wiadomości:
   - Używaj szablonów z `templates/notifications/`
   - Utrzymuj spójny styl wiadomości
   - Skracaj linki w wiadomościach SMS

2. Obsługa Błędów:
   - Loguj wszystkie błędy wysyłania
   - Zaimplementuj mechanizm ponawiania
   - Powiadamiaj o krytycznych błędach
   - Przechowuj kopie zapasowe wiadomości

3. Bezpieczeństwo:
   - Szyfruj wrażliwe dane
   - Używaj tokenów dostępu
   - Rotuj klucze API
   - Monitoruj limity użycia

## Zasady Integracji z Google Drive
1. Struktura Plików:
   - Utrzymuj hierarchię folderów
   - Używaj znaczników czasu w nazwach plików
   - Generuj metadane dla każdego pliku
   - Zaimplementuj mechanizm czyszczenia

2. Zarządzanie Uprawnieniami:
   - Używaj konta serwisowego
   - Ogranicz dostęp do folderów
   - Regularnie weryfikuj uprawnienia
   - Loguj operacje na plikach

3. Optymalizacja:
   - Kompresuj obrazy przed przesłaniem
   - Używaj asynchronicznego przesyłania
   - Zaimplementuj kolejkowanie zadań
   - Monitoruj użycie przestrzeni

4. Obsługa Błędów:
   - Zaimplementuj mechanizm ponawiania
   - Loguj błędy synchronizacji
   - Przechowuj lokalne kopie zapasowe
   - Powiadamiaj o problemach

## Zasady Testowania Powiadomień
1. Testy Jednostkowe:
   - Testuj każdy typ powiadomienia
   - Weryfikuj formaty wiadomości
   - Sprawdzaj obsługę błędów
   - Testuj limity i ograniczenia

2. Testy Integracyjne:
   - Weryfikuj przepływ danych
   - Testuj kolejkowanie
   - Sprawdzaj synchronizację
   - Weryfikuj priorytety

3. Testy Wydajnościowe:
   - Mierz czas wysyłania
   - Sprawdzaj obciążenie
   - Testuj pod obciążeniem
   - Monitoruj zasoby

4. Testy Bezpieczeństwa:
   - Weryfikuj szyfrowanie
   - Testuj autoryzację
   - Sprawdzaj limity
   - Weryfikuj logi
