# 🔄 Instrukcje Aktualizacji Bazy Danych

## Problem został naprawiony! ✅

Dodano pole `config` do tabeli `settings` w bazie danych, które **trwale przechowuje** ustawienia:
- ✅ `blur_faces` - włączenie/wyłączenie zamazywania głów
- ✅ `confidence_threshold` - próg pewności detekcji
- ✅ `camera_index` - indeks wybranej kamery
- ✅ `camera_name` - nazwa kamery
- ✅ `email_notifications` - powiadomienia email
- ✅ `sms_notifications` - powiadomienia SMS

## 🚀 Jak zaktualizować bazę danych?

Wybierz jedną z poniższych metod:

---

### **Metoda 1: Szybki Reset (ZALECANE - jeśli nie masz ważnych detekcji)**

1. **Zatrzymaj aplikację** (Ctrl+C w terminalu)

2. **Usuń stary plik bazy danych:**
   ```bash
   cd Detection-phone
   rm instance/admin.db
   # LUB na Windows:
   del instance\admin.db
   ```

3. **Utwórz nową bazę z nowymi polami:**
   ```bash
   python init_db.py
   ```

4. **Uruchom aplikację ponownie:**
   ```bash
   python app.py
   ```

✅ **Gotowe!** Wszystkie ustawienia będą teraz trwale zapisywane.

---

### **Metoda 2: Aktualizacja bez utraty danych (jeśli masz ważne detekcje)**

1. **Zatrzymaj aplikację** (Ctrl+C)

2. **Uruchom skrypt aktualizacji:**
   ```bash
   cd Detection-phone
   python upgrade_db.py
   ```

3. **Uruchom aplikację ponownie:**
   ```bash
   python app.py
   ```

✅ **Gotowe!** Twoje detekcje zostały zachowane.

---

### **Metoda 3: Migracja Alembic (dla zaawansowanych)**

1. **Zatrzymaj aplikację**

2. **Uruchom migrację:**
   ```bash
   cd Detection-phone
   flask db upgrade
   ```

3. **Uruchom aplikację ponownie**

---

## 🧪 Jak przetestować?

1. Przejdź do **Settings** → **Privacy Settings**
2. **Wyłącz** przełącznik "Enable anonymization (blur)"
3. Kliknij **"Save Settings"**
4. Przejdź do **Detections**
5. Wróć do **Settings**
6. ✅ Przełącznik powinien **pozostać wyłączony**!

## 📝 Co się zmieniło?

### Wcześniej:
- ❌ Ustawienia były tylko w pamięci
- ❌ Po przeładowaniu strony wracały do domyślnych (`blur_faces = True`)
- ❌ Przy każdym restarcie aplikacji: reset do domyślnych wartości

### Teraz:
- ✅ Ustawienia są **trwale zapisywane** w bazie danych
- ✅ Po przeładowaniu strony: **ustawienia są pamiętane**
- ✅ Po restarcie aplikacji: **ustawienia są zachowane**

## ❓ Problemy?

Jeśli coś nie działa:

1. Sprawdź logi w terminalu - zobaczysz komunikaty DEBUG:
   ```
   🔧 DEBUG: Zapisuję do DB config['blur_faces'] = False
   ✅ Zapisano ustawienia do bazy danych (config): {...}
   ```

2. Jeśli widzisz błąd `no such column: settings.config`:
   - Uruchom **Metodę 1** (reset bazy danych)

3. Jeśli nadal nie działa:
   - Sprawdź czy plik `instance/admin.db` istnieje
   - Sprawdź uprawnienia do zapisu w katalogu `instance/`

---

## 🎉 Gotowe!

System teraz **poprawnie zapisuje i odczytuje** wszystkie ustawienia z bazy danych!

