# 📋 Aktualna Architektura Projektu - Szczegółowy Opis

## 🎯 Co Projekt Robi?

System wykrywa **telefony** w czasie rzeczywistym i **anonimizuje głowy** osób na zdjęciach przed zapisaniem do bazy danych.

---

## 🏗️ Architektura - Producer-Consumer Pattern

### 1️⃣ **MAIN THREAD (Producer)** - Detekcja Telefonów w Czasie Rzeczywistym

**Technologia:**
- **YOLOv8** (model: `yolov8s.pt`)
- **Klasa:** `CameraController` w `camera_controller.py`

**Przepływ:**
```
📷 Kamera (OpenCV VideoCapture)
    ↓
🔍 YOLOv8 wykrywa telefony (class_id = 67)
    ↓
✅ Telefon wykryty? (confidence ≥ threshold, domyślnie 0.2)
    ↓
💾 Zapisz ORYGINALNĄ klatkę do ./detections/phone_YYYYMMDD_HHMMSS.jpg
    ↓
📤 Dodaj do Queue (filepath, confidence, should_blur, zone_name)
    ↓
🔄 Kontynuuj pętlę (20-30 FPS)
```

**Kluczowe szczegóły:**
- Przetwarza co 5. klatkę (frame skipping dla wydajności)
- Zapisuje **ORYGINALNĄ** klatkę (bez żadnej modyfikacji!)
- Nie blokuje się na anonimizacji
- Obsługuje ROI zones (Region of Interest)

---

### 2️⃣ **WORKER THREAD (Consumer)** - Anonimizacja Głów Offline

**Technologia:**
- **Roboflow AI** (model: `heads-detection/1`)
- **Klasa:** `AnonymizerWorker` w `camera_controller.py`

**Przepływ:**
```
📥 Pobierz zadanie z Queue
    ↓
📂 Wczytaj obraz z dysku (cv2.imread)
    ↓
🤖 Roboflow API - wykryj głowy (confidence ≥ 40%)
    ↓
👁️ Dla każdej wykrytej głowy:
    - Pobierz bounding box (x, y, width, height)
    - Wytnij region głowy (ROI)
    - Zastosuj Gaussian Blur (99x99, sigma=30)
    - Wklej zamazany region z powrotem
    ↓
💾 NADPISZ oryginalny plik zanonimizowaną wersją
    ↓
💾 Zapisz do bazy danych (tylko zanonimizowane!)
    ↓
📧 Wyślij powiadomienia (Email/SMS) jeśli włączone
    ↓
✅ Zadanie zakończone
```

**Kluczowe szczegóły:**
- Działa asynchronicznie (nie blokuje głównej pętli)
- Roboflow zwraca format: `{x: center_x, y: center_y, width, height}`
- Konwersja do OpenCV: `x1 = center_x - width/2`, `y1 = center_y - height/2`
- Gaussian blur jest **nieodwracalny**
- Baza danych **NIGDY** nie zawiera oryginalnych klatek

---

## 🔧 Technologie i Modele

### Detekcja Telefonów (YOLOv8)
```python
# app.py, linia 73
GLOBAL_YOLO_MODEL_DETECTION = YOLO('yolov8s.pt')

# camera_controller.py, linia 129-138
self.phone_class_id = 67  # COCO class ID dla "cell phone"
```

**Szczegóły:**
- Model: YOLOv8s (średni rozmiar, dobry balans szybkość/dokładność)
- Klasa: 67 (cell phone w datasecie COCO)
- Confidence threshold: konfigurowalne (domyślnie 0.2)

---

### Detekcja Głów (Roboflow AI)
```python
# app.py, linia 83-95
rf = Roboflow(api_key="DAWQI4w1KCHH1MlWH7t4")
GLOBAL_YOLO_MODEL_ANONYMIZATION = rf.model("heads-detection/1")

# camera_controller.py, linia 2080
prediction = self.model.predict(image_path, confidence=40, overlap=30)
```

**Szczegóły:**
- Model: `heads-detection/1` z Roboflow
- Confidence: 40% (0.4)
- Overlap: 30% (dla NMS - Non-Maximum Suppression)
- Format wyniku: JSON z `predictions` array
- Każda predykcja: `{x, y, width, height, confidence, class}`

---

### Anonimizacja (OpenCV Gaussian Blur)
```python
# camera_controller.py, linia 2119
blur = cv2.GaussianBlur(roi, (99, 99), 30)
```

**Szczegóły:**
- Kernel size: 99x99 (bardzo silne rozmycie)
- Sigma: 30 (standardowe odchylenie)
- Nieodwracalne (nie można odzyskać oryginalnego obrazu)

---

## 📊 Przepływ Danych - Krok po Kroku

### Przykład: Wykryto telefon o 14:30:15

**1. Main Thread (0.03s):**
```
14:30:15.000 - Kamera: odczyt klatki
14:30:15.010 - YOLOv8: detekcja (30ms)
14:30:15.015 - Wykryto telefon! Confidence: 0.85
14:30:15.020 - Zapisano: ./detections/phone_20251123_143015.jpg
14:30:15.025 - Dodano do Queue: {
    'filepath': './detections/phone_20251123_143015.jpg',
    'confidence': 0.85,
    'should_blur': True,  # Zamrożona wartość z ustawień
    'zone_name': 'bench 1'  # Jeśli w ROI zone
}
14:30:15.030 - Kontynuuj pętlę...
```

**2. Worker Thread (1-2s, asynchronicznie):**
```
14:30:15.100 - Pobrano z Queue
14:30:15.150 - Wczytano obraz (cv2.imread)
14:30:15.200 - Roboflow API: wysłano request
14:30:15.800 - Roboflow: otrzymano wynik (3 głowy wykryte)
14:30:15.850 - Głowa #1: blur (99x99)
14:30:15.900 - Głowa #2: blur (99x99)
14:30:15.950 - Głowa #3: blur (99x99)
14:30:16.000 - Nadpisano plik zanonimizowaną wersją
14:30:16.050 - Zapisano do bazy danych
14:30:16.100 - Upload na Cloudinary...
14:30:16.500 - Wysłano Email notification
14:30:16.600 - Wysłano SMS notification
14:30:16.650 - Zadanie zakończone
```

**Główna pętla NIE CZEKA na worker thread!**

---

## 🗂️ Struktura Bazy Danych

### Model: `Detection`
```python
# models.py
class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(100))  # Nazwa strefy lub kamery
    confidence = db.Column(db.Float)      # Pewność detekcji telefonu
    image_path = db.Column(db.String(200)) # Nazwa pliku (tylko nazwa!)
    status = db.Column(db.String(20))     # 'Pending', 'Reviewed', etc.
    user_id = db.Column(db.Integer)
```

**Kluczowe:**
- `image_path` zawiera **tylko nazwę pliku**, nie pełną ścieżkę
- Plik w `./detections/` jest **ZAWSZE zanonimizowany** przed zapisem do DB
- `location` może być nazwą strefy ROI (np. "bench 1") lub nazwą kamery

---

## 🎛️ Ustawienia Systemu

### Model: `Settings`
```python
# models.py
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule = db.Column(JSON)      # Harmonogram tygodniowy
    roi_zones = db.Column(JSON)     # Lista stref ROI
    config = db.Column(JSON)        # Główne ustawienia
```

### Struktura `config`:
```json
{
  "blur_faces": true,              // Czy zamazywać głowy (UWAGA: nazwa legacy!)
  "confidence_threshold": 0.2,     // Próg dla detekcji telefonów
  "camera_index": 0,               // Indeks kamery
  "camera_name": "Camera 1",       // Nazwa kamery
  "email_notifications": false,    // Powiadomienia email
  "sms_notifications": false,      // Powiadomienia SMS
  "anonymization_percent": 50,     // Nieużywane (legacy)
  "roi_coordinates": null          // Nieużywane (zastąpione przez roi_zones)
}
```

**UWAGA:** Ustawienie nazywa się `blur_faces` (legacy), ale faktycznie kontroluje zamazywanie **głów**, nie twarzy!

---

## 🌐 ROI Zones (Strefy Detekcji)

### Struktura:
```json
[
  {
    "name": "bench 1",
    "coords": {
      "x": 0.1,      // Znormalizowane (0.0-1.0)
      "y": 0.1,
      "w": 0.2,      // Szerokość
      "h": 0.2       // Wysokość
    }
  },
  {
    "name": "bench 2",
    "coords": {
      "x": 0.5,
      "y": 0.3,
      "w": 0.25,
      "h": 0.25
    }
  }
]
```

### Throttling (Wyciszanie Alertów):
```python
# camera_controller.py, linia 728-752
self.alert_mute_until = {}  # {'bench 1': datetime, 'bench 2': datetime}
self.mute_duration = timedelta(minutes=5)  # 5 minut wyciszenia
```

**Jak działa:**
1. Telefon wykryty w "bench 1" → Wyślij alert
2. Ustaw wyciszenie dla "bench 1" na 5 minut
3. Kolejne detekcje w "bench 1" są ignorowane przez 5 minut
4. Detekcje w "bench 2" działają normalnie (osobne wyciszenie)

---

## 📧 Powiadomienia

### Email (Yagmail):
```python
# camera_controller.py, linia 1907-1974
with yagmail.SMTP(self.email_user, self.email_password) as yag_client:
    yag_client.send(
        to=self.email_recipient,
        subject=f"Wykryto Telefon! ({location})",
        contents=[
            "<b>Wykryto Telefon!</b>",
            f"<b>Lokalizacja:</b> {location}",
            f"<b>Pewność detekcji:</b> {confidence * 100:.1f}%",
            yagmail.inline(filepath)  # Osadzony obraz
        ],
        attachments=filepath
    )
```

### SMS (Vonage):
```python
# camera_controller.py, linia 1829-1905
sms_message = SmsMessage(
    to=to_number,
    from_=self.vonage_from_number,
    text=f"Phone Detection Alert!\n"
         f"Time: {timestamp}\n"
         f"Location: {location}\n"
         f"Confidence: {confidence:.2%}\n"
         f"Image: {public_link}"
)
response = self.vonage_sms.send(sms_message)
```

### Cloudinary (Upload):
```python
# camera_controller.py, linia 1788-1827
response = cloudinary.uploader.upload(
    filepath,
    folder="phone_detections",
    public_id=os.path.splitext(filename)[0],
    resource_type="image",
    overwrite=True
)
secure_url = response.get('secure_url')
```

---

## 🔐 Bezpieczeństwo i Prywatność

### Gwarancje:
1. ✅ **Oryginalne klatki są zapisywane lokalnie** (./detections/)
2. ✅ **Głowy są wykrywane przez Roboflow AI** (90%+ accuracy)
3. ✅ **Głowy są zamazywane PRZED zapisem do DB** (Gaussian 99x99)
4. ✅ **Oryginalny plik jest NADPISYWANY** zanonimizowaną wersją
5. ✅ **Baza danych zawiera TYLKO zanonimizowane obrazy**
6. ✅ **Gaussian blur jest nieodwracalny**

### Przepływ bezpieczeństwa:
```
1. Telefon wykryty → Zapisz ORYGINAŁ do ./detections/
2. Worker pobiera ścieżkę z Queue
3. Worker wykrywa głowy (Roboflow API)
4. Worker zamazuje głowy (Gaussian blur)
5. Worker NADPISUJE plik zanonimizowaną wersją
6. Worker dodaje do bazy danych
7. Baza zawiera TYLKO zanonimizowane
```

**NIGDY nie wysyłamy oryginalnych klatek do bazy!**

---

## 🚀 Frontend (React + TypeScript)

### Struktura:
```
src/
├── components/
│   └── Layout.tsx           # Nawigacja, sidebar
├── contexts/
│   └── AuthContext.tsx      # Autentykacja JWT
├── pages/
│   ├── Dashboard.tsx        # Statystyki, wykresy
│   ├── Detections.tsx       # Lista detekcji, galeria
│   ├── Settings.tsx         # Ustawienia kamery, harmonogram, ROI
│   └── Login.tsx            # Logowanie
└── App.tsx                  # Routing
```

### Technologie:
- **React 18** + **TypeScript**
- **Material-UI (MUI)** - komponenty UI
- **React Router** - routing
- **Recharts** - wykresy
- **Axios** - HTTP client

### API Endpoints:
```
POST   /api/login
GET    /api/logout
GET    /api/detections
DELETE /api/detections/:id
DELETE /api/detections/batch
GET    /api/dashboard-stats
GET    /api/stats/detections_over_time
GET    /api/settings
POST   /api/settings
POST   /api/camera/start
POST   /api/camera/stop
GET    /api/camera/status
GET    /detections/:filename
GET    /video_feed (MJPEG stream)
```

---

## 📦 Zależności

### Backend (Python):
```
Flask==3.0.0
flask-cors==4.0.0
flask-login==0.6.3
flask-migrate==4.0.5
SQLAlchemy==2.0.23
opencv-python==4.8.1.78
ultralytics==8.0.196  # YOLOv8
roboflow==1.1.9       # Roboflow API
cloudinary==1.36.0
vonage==3.5.1         # SMS
yagmail==0.15.293     # Email
python-dotenv==1.0.0
```

### Frontend (Node.js):
```json
{
  "react": "^18.2.0",
  "typescript": "^4.9.5",
  "@mui/material": "^5.15.10",
  "@mui/icons-material": "^5.15.10",
  "react-router-dom": "^6.22.1",
  "recharts": "^2.10.3",
  "axios": "^1.6.7",
  "chart.js": "^4.4.1"
}
```

---

## 🎯 Podsumowanie - Co Jest Używane?

### ✅ UŻYWANE:
1. **YOLOv8** (`yolov8s.pt`) - Detekcja telefonów
2. **Roboflow AI** (`heads-detection/1`) - Detekcja głów
3. **OpenCV** - Gaussian blur, przetwarzanie obrazu
4. **Flask** - Backend API
5. **React + TypeScript** - Frontend
6. **SQLite** - Baza danych
7. **Cloudinary** - Cloud storage
8. **Vonage** - SMS notifications
9. **Yagmail** - Email notifications

---

## 🔍 Kluczowe Pliki

1. **`app.py`** (1006 linii) - Flask server, API endpoints, inicjalizacja globalnych zasobów
2. **`camera_controller.py`** (2184 linie) - Główna logika, CameraController + AnonymizerWorker
3. **`models.py`** - Modele bazy danych (User, Detection, Settings)
4. **`src/pages/Settings.tsx`** - UI dla ustawień (harmonogram, ROI zones, powiadomienia)
5. **`src/pages/Detections.tsx`** - Galeria detekcji
6. **`src/pages/Dashboard.tsx`** - Statystyki i wykresy

---

