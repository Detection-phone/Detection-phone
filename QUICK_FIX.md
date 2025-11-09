# 🔧 SZYBKA NAPRAWA - Błąd "no such column: settings.config"

## Problem
Baza danych nie ma nowej kolumny `config`, którą dodaliśmy do modelu.

## ✅ Rozwiązanie (3 proste kroki):

### 1️⃣ **Zatrzymaj aplikację**
W terminalu gdzie działa aplikacja, naciśnij:
```
Ctrl + C
```

### 2️⃣ **Usuń starą bazę danych**

W PowerShell:
```powershell
cd Detection-phone
Remove-Item instance\admin.db
```

LUB ręcznie usuń plik: `Detection-phone/instance/admin.db`

### 3️⃣ **Utwórz nową bazę i uruchom aplikację**

```powershell
python init_db.py
python app.py
```

## 🎉 Gotowe!

Aplikacja będzie teraz:
- ✅ Zapisywać ustawienia `blur_faces` do bazy danych
- ✅ Pamiętać te ustawienia po przeładowaniu strony
- ✅ Zachowywać ustawienia po restarcie aplikacji

## ℹ️ Uwaga
Ta operacja **usunie wszystkie wykrycia** (detections) z bazy danych.
Jeśli masz ważne wykrycia, skopiuj folder `detections/` przed usunięciem bazy.

