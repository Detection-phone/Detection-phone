# Quick Start - Frontend Refactor

## Uruchomienie Aplikacji

### 1. Uruchom serwer Flask

```bash
cd Detection-phone
python app.py
```

Aplikacja będzie dostępna pod adresem: **http://localhost:5000**

### 2. Zaloguj się

Użyj swoich danych logowania. Po zalogowaniu zobaczysz nowy, ciemny interfejs.

---

## Co Zobaczyć

### 🏠 Dashboard (http://localhost:5000/dashboard)
- **Karty statystyk** - Auto-refresh co 3 sekundy
- **Status kamery** - Zmienia kolor w zależności od stanu
- **Tabela wykryć** - Ostatnie 5 detekcji, aktualizowane na żywo

**Efekty do sprawdzenia:**
- Poczekaj 3 sekundy - dane się odświeżą
- Hover na kartach - subtle lift effect
- Kliknij "eye icon" przy wykryciu - otwiera się w nowej karcie

### 📸 Detections (http://localhost:5000/detections)
- **Grid View** - Karty z miniaturami
- **List View** - Tabela ze szczegółami

**Efekty do sprawdzenia:**
- **Kliknij na kartę** - otwiera się modal z pełnym obrazem
- Hover na kartach - lift + scale + niebieskie podświetlenie
- Obrazek w karcie zoomuje się przy hover
- W modalu możesz pobrać obraz

### ⚙️ Settings (http://localhost:5000/settings)
- Sekcje wizualnie oddzielone
- Ikony przy każdej opcji
- Slider dla confidence threshold

**Efekty do sprawdzenia:**
- Zmień wartość confidence - wartość pokazuje się na żywo
- Kliknij "Save Settings" - loading spinner + success message
- Wszystkie sekcje mają ikony i kolory

### 🔐 Login (http://localhost:5000/ - gdy niezalogowany)
- Wycentrowany formularz
- Ikona telefonu u góry

**Efekty do sprawdzenia:**
- Zaloguj się poprawnie - spinner + success + redirect
- Zaloguj się błędnie - shake animation + error message

---

## Key Features do Demonstracji

### 1. Dark Mode
- Otwórz dowolną stronę - wszystko jest ciemne
- GitHub-inspired color scheme
- Czytelny tekst, dobre kontrasty

### 2. Real-time Dashboard
```
1. Otwórz dashboard
2. Otwórz nową kartę i stwórz nową detekcję (lub poczekaj na automatyczną)
3. Wróć do dashboardu - w ciągu 3 sekund zobaczysz nową detekcję
```

### 3. Modal Gallery
```
1. Idź na /detections
2. Kliknij na dowolną kartę
3. Modal otwiera się z pełnym obrazem
4. Możesz pobrać obraz
5. Zamknij modal - smooth fade out
```

### 4. Hover Effects
- **Karty** - podnoszą się i świecą na niebiesko
- **Przyciski** - lift + gradient change
- **Nav linki** - kolor + slight lift
- **Obrazy w grid** - zoom in effect

---

## Responsywność

Zmień rozmiar okna przeglądarki - layout dostosowuje się:
- Desktop: 4 kolumny w grid
- Tablet: 3 kolumny
- Mobile: 1-2 kolumny

---

## Browser Console

Otwórz Developer Tools (F12) i zobacz:
- Brak błędów JavaScript
- Console logi dla AJAX requests
- Network tab pokazuje requests co 3 sekundy (`/api/dashboard-stats`)

---

## Troubleshooting

### Nie widać dark mode?
Upewnij się, że używasz Bootstrap 5.3+. Sprawdź w `base.html`:
```html
<html lang="en" data-bs-theme="dark">
```

### Dashboard się nie odświeża?
Sprawdź console. Endpoint `/api/dashboard-stats` powinien być wywoływany co 3s.

### Modal się nie otwiera?
Sprawdź, czy masz wykrycia w bazie. Jeśli nie ma wykryć, stwórz testowe.

---

## Performance

- **AJAX polling** - tylko 1 request co 3 sekundy
- **Modal** - lazy loading obrazów
- **CSS Animations** - GPU-accelerated transforms
- **JavaScript** - vanilla JS, brak ciężkich bibliotek

---

**Enjoy the new UI! 🎉**

