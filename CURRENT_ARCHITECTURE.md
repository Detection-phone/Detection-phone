# Architektura Systemu Wykrywania Smartfonów w Szkołach

## Cel Projektu

System został zaprojektowany do automatycznego wykrywania telefonów komórkowych podczas zajęć lekcyjnych w szkołach podstawowych. Głównym celem jest pomoc nauczycielom w monitorowaniu problemu nieodpowiedniego korzystania ze smartfonów przez uczniów, przy jednoczesnym zachowaniu prywatności uczniów poprzez automatyczną anonimizację ich wizerunków.

## Architektura - Wzorzec Producer-Consumer

System wykorzystuje wzorzec Producer-Consumer, gdzie główny wątek (Producer) zajmuje się detekcją telefonów w czasie rzeczywistym, a osobny wątek workera (Consumer) przetwarza obrazy asynchronicznie, wykonując anonimizację głów uczniów.

### 1. WĄTEK GŁÓWNY (Producer) - Detekcja Telefonów w Czasie Rzeczywistym

Technologia:
- YOLOv8 (model: `yolov8m.pt` z fallbackiem na `yolov8s.pt`)
- Klasa: `CameraController` w `camera_controller.py`

Przepływ działania:
```
Kamera (OpenCV VideoCapture)
    ↓
YOLOv8 wykrywa telefony (class_id = 67)
    ↓
Telefon wykryty? (confidence ≥ threshold, domyślnie 0.2)
    ↓
Zapisz ORYGINALNĄ klatkę do ./detections/phone_YYYYMMDD_HHMMSS.jpg
    ↓
Dodaj do Queue (filepath, confidence, should_blur, zone_name)
    ↓
Kontynuuj pętlę (20-30 FPS)
```

Kluczowe szczegóły:
- Przetwarza co 3. klatkę (frame skipping dla wydajności)
- Zapisuje ORYGINALNĄ klatkę (bez żadnej modyfikacji!)
- Nie blokuje się na anonimizacji - działa w czasie rzeczywistym
- Obsługuje ROI zones (Region of Interest) - można definiować konkretne miejsca w klasie
- Wykorzystuje preprocessing obrazu (CLAHE, unsharp masking) dla lepszej detekcji

Preprocessing dla lepszej detekcji:
System stosuje kilka technik poprawy jakości obrazu przed detekcją:
- CLAHE (Contrast Limited Adaptive Histogram Equalization) - poprawa kontrastu
- Unsharp masking - wyostrzenie obrazu
- Opcjonalne zwiększenie rozdzielczości dla małych obrazów

### 2. WĄTEK WORKERA (Consumer) - Anonimizacja Głów Offline

Technologia:
- Roboflow AI (model: `heads-detection/1`)
- Klasa: `AnonymizerWorker` w `camera_controller.py`

Przepływ działania:
```
Pobierz zadanie z Queue
    ↓
Wczytaj obraz z dysku (cv2.imread)
    ↓
Roboflow API - wykryj głowy (confidence ≥ 40%)
    ↓
Dla każdej wykrytej głowy:
    - Pobierz bounding box (x, y, width, height)
    - Wytnij region głowy (ROI)
    - Zastosuj Gaussian Blur (99x99, sigma=30)
    - Wklej zamazany region z powrotem
    ↓
NADPISZ oryginalny plik zanonimizowaną wersją
    ↓
Zapisz do bazy danych (tylko zanonimizowane!)
    ↓
Wyślij powiadomienia (Email/SMS) jeśli włączone
    ↓
Zadanie zakończone
```

Kluczowe szczegóły:
- Działa asynchronicznie (nie blokuje głównej pętli)
- Roboflow zwraca format: `{x: center_x, y: center_y, width, height}`
- Konwersja do OpenCV: `x1 = center_x - width/2`, `y1 = center_y - height/2`
- Gaussian blur jest nieodwracalny - zapewnia pełną anonimizację
- Baza danych NIGDY nie zawiera oryginalnych klatek

## Technologie i Modele

### Detekcja Telefonów (YOLOv8)

```python
GLOBAL_YOLO_MODEL_DETECTION = YOLO('yolov8m.pt')

self.phone_class_id = 67
```

Szczegóły:
- Model: YOLOv8m (średni rozmiar, dobry balans szybkość/dokładność)
- Klasa: 67 (cell phone w datasecie COCO)
- Confidence threshold: konfigurowalne (domyślnie 0.2)
- Model został wybrany jako kompromis między dokładnością a szybkością - ważne w kontekście szkolnym, gdzie system musi działać przez cały dzień

### Detekcja Głów (Roboflow AI)

```python
rf = Roboflow(api_key="DAWQI4w1KCHH1MlWH7t4")
GLOBAL_YOLO_MODEL_ANONYMIZATION = rf.model("heads-detection/1")

prediction = self.model.predict(image_path, confidence=40, overlap=30)
```

Szczegóły:
- Model: `heads-detection/1` z Roboflow
- Confidence: 40% (0.4) - wystarczająco niski, aby wykryć większość głów, ale na tyle wysoki, aby uniknąć fałszywych alarmów
- Overlap: 30% (dla NMS - Non-Maximum Suppression)
- Format wyniku: JSON z `predictions` array
- Każda predykcja: `{x, y, width, height, confidence, class}`

Dlaczego Roboflow?
Roboflow został wybrany ze względu na wysoką dokładność wykrywania głów (ponad 90%) oraz łatwość integracji. Model został wytrenowany na dużej bazie danych i dobrze radzi sobie z różnymi kątami widzenia i oświetleniem, co jest ważne w środowisku szkolnym.

### Anonimizacja (OpenCV Gaussian Blur)

```python
blur = cv2.GaussianBlur(roi, (99, 99), 30)
```

Szczegóły:
- Kernel size: 99x99 (bardzo silne rozmycie)
- Sigma: 30 (standardowe odchylenie)
- Nieodwracalne (nie można odzyskać oryginalnego obrazu)

Dlaczego takie parametry?
Parametry zostały dobrane eksperymentalnie, aby zapewnić pełną anonimizację uczniów przy jednoczesnym zachowaniu możliwości identyfikacji telefonu. Rozmiar kernela 99x99 jest wystarczająco duży, aby zamazać całą głowę, a sigma=30 zapewnia płynne przejście między zamazanym a normalnym obszarem.

## Przepływ Danych - Krok po Kroku

### Przykład: Wykryto telefon o 14:30:15 w klasie

1. Wątek Główny (0.03s):
```
14:30:15.000 - Kamera: odczyt klatki
14:30:15.010 - Preprocessing obrazu (CLAHE, unsharp masking)
14:30:15.015 - YOLOv8: detekcja (30ms)
14:30:15.020 - Wykryto telefon! Confidence: 0.85
14:30:15.025 - Sprawdzenie ROI zones - telefon w strefie "Ławka 3"
14:30:15.030 - Zapisano: ./detections/phone_20251123_143015.jpg
14:30:15.035 - Dodano do Queue: {
    'filepath': './detections/phone_20251123_143015.jpg',
    'confidence': 0.85,
    'should_blur': True,
    'zone_name': 'Ławka 3'
}
14:30:15.040 - Kontynuuj pętlę...
```

2. Wątek Workera (1-2s, asynchronicznie):
```
14:30:15.100 - Pobrano z Queue
14:30:15.150 - Wczytano obraz (cv2.imread)
14:30:15.200 - Roboflow API: wysłano request
14:30:15.800 - Roboflow: otrzymano wynik (3 głowy wykryte)
14:30:15.850 - Głowa #1: blur (99x99) - uczeń przy ławce 3
14:30:15.900 - Głowa #2: blur (99x99) - uczeń w tle
14:30:15.950 - Głowa #3: blur (99x99) - uczeń przy sąsiedniej ławce
14:30:16.000 - Nadpisano plik zanonimizowaną wersją
14:30:16.050 - Zapisano do bazy danych
14:30:16.100 - Upload na Cloudinary...
14:30:16.500 - Wysłano Email notification do nauczyciela
14:30:16.600 - Wysłano SMS notification
14:30:16.650 - Zadanie zakończone
```

Ważne: Główna pętla NIE CZEKA na worker thread! To oznacza, że system może wykrywać telefony z prędkością 20-30 FPS, niezależnie od tego, jak długo trwa anonimizacja.

## Struktura Bazy Danych

### Model: `Detection`

```python
class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    location = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    image_path = db.Column(db.String(200))
    status = db.Column(db.String(20))
    user_id = db.Column(db.Integer)
```

Kluczowe:
- `image_path` zawiera tylko nazwę pliku, nie pełną ścieżkę
- Plik w `./detections/` jest ZAWSZE zanonimizowany przed zapisem do DB
- `location` może być nazwą strefy ROI (np. "Ławka 3") lub nazwą kamery
- `status` pozwala nauczycielom oznaczać detekcje jako sprawdzone

### Model: `Settings`

```python
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule = db.Column(JSON)
    roi_zones = db.Column(JSON)
    config = db.Column(JSON)
```

### Struktura `config`:

```json
{
  "blur_faces": true,
  "confidence_threshold": 0.2,
  "camera_index": 0,
  "camera_name": "Camera 1",
  "email_notifications": false,
  "sms_notifications": false,
  "anonymization_percent": 50,
  "roi_coordinates": null
}
```

Uwaga: Ustawienie nazywa się `blur_faces` (legacy), ale faktycznie kontroluje zamazywanie głów, nie twarzy!

## ROI Zones (Strefy Detekcji)

### Struktura:

```json
[
  {
    "name": "Ławka 1",
    "coords": {
      "x": 0.1,
      "y": 0.1,
      "w": 0.2,
      "h": 0.2
    }
  },
  {
    "name": "Ławka 2",
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
self.alert_mute_until = {}
self.mute_duration = timedelta(minutes=5)
```

Jak działa:
1. Telefon wykryty w "Ławka 1" → Wyślij alert
2. Ustaw wyciszenie dla "Ławka 1" na 5 minut
3. Kolejne detekcje w "Ławka 1" są ignorowane przez 5 minut
4. Detekcje w "Ławka 2" działają normalnie (osobne wyciszenie)

Dlaczego 5 minut?
Czas został wybrany eksperymentalnie - jest wystarczająco długi, aby uniknąć spamu alertów, gdy uczeń ciągle używa telefonu, ale na tyle krótki, aby nauczyciel mógł zareagować na powtarzające się wykrycia.

## Powiadomienia

### Email (Yagmail):

```python
with yagmail.SMTP(self.email_user, self.email_password) as yag_client:
    yag_client.send(
        to=self.email_recipient,
        subject=f"Wykryto Telefon! ({location})",
        contents=[
            "<b>Wykryto Telefon!</b>",
            f"<b>Lokalizacja:</b> {location}",
            f"<b>Pewność detekcji:</b> {confidence * 100:.1f}%",
            yagmail.inline(filepath)
        ],
        attachments=filepath
    )
```

### SMS (Vonage):

```python
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
response = cloudinary.uploader.upload(
    filepath,
    folder="phone_detections",
    public_id=os.path.splitext(filename)[0],
    resource_type="image",
    overwrite=True
)
secure_url = response.get('secure_url')
```

## Bezpieczeństwo i Prywatność

### Gwarancje:

1. Oryginalne klatki są zapisywane lokalnie (./detections/)
2. Głowy są wykrywane przez Roboflow AI (90%+ accuracy)
3. Głowy są zamazywane PRZED zapisem do DB (Gaussian 99x99)
4. Oryginalny plik jest NADPISYWANY zanonimizowaną wersją
5. Baza danych zawiera TYLKO zanonimizowane obrazy
6. Gaussian blur jest nieodwracalny

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

NIGDY nie wysyłamy oryginalnych klatek do bazy!

To jest kluczowe dla ochrony prywatności uczniów - nawet jeśli ktoś uzyska dostęp do bazy danych, nie będzie mógł zidentyfikować uczniów na zdjęciach.

## Frontend (React + TypeScript)

### Struktura:

```
src/
├── components/
│   └── Layout.tsx
├── contexts/
│   └── AuthContext.tsx
├── pages/
│   ├── Dashboard.tsx
│   ├── Detections.tsx
│   ├── Settings.tsx
│   └── Login.tsx
└── App.tsx
```

### Technologie:

- React 18 + TypeScript
- Material-UI (MUI) - komponenty UI
- React Router - routing
- Recharts - wykresy
- Axios - HTTP client

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

## Zależności

### Backend (Python):

```
Flask==3.0.0
flask-cors==4.0.0
flask-login==0.6.3
flask-migrate==4.0.5
SQLAlchemy==2.0.23
opencv-python==4.8.1.78
ultralytics==8.0.196
roboflow==1.1.9
cloudinary==1.36.0
vonage==3.5.1
yagmail==0.15.293
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

## Podsumowanie - Co Jest Używane?

### Używane:

1. YOLOv8 (`yolov8m.pt`) - Detekcja telefonów
2. Roboflow AI (`heads-detection/1`) - Detekcja głów
3. OpenCV - Gaussian blur, przetwarzanie obrazu
4. Flask - Backend API
5. React + TypeScript - Frontend
6. SQLite - Baza danych
7. Cloudinary - Cloud storage
8. Vonage - SMS notifications
9. Yagmail - Email notifications

## Kluczowe Pliki

1. `app.py` - Flask server, API endpoints, inicjalizacja globalnych zasobów
2. `camera_controller.py` - Główna logika, CameraController + AnonymizerWorker
3. `models.py` - Modele bazy danych (User, Detection, Settings)
4. `src/pages/Settings.tsx` - UI dla ustawień (harmonogram, ROI zones, powiadomienia)
5. `src/pages/Detections.tsx` - Galeria detekcji
6. `src/pages/Dashboard.tsx` - Statystyki i wykresy
