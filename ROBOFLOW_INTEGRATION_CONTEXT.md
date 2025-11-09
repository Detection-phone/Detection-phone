# 🔄 Kontekst zmian: Integracja modelu Roboflow head-detection

## 📋 Podsumowanie zmian

Projekt został zaktualizowany z **ultralytics YOLO** na **Roboflow API** do wykrywania głów w celu anonimizacji. Zmiana była konieczna, ponieważ:
- Poprzedni model (YOLO) wykrywał całe osoby i zamazywał procentowo (50% górnej części), co błędnie zamazywało podniesione ręce
- Nowy model Roboflow wykrywa **tylko głowy** i zamazuje **cały bounding box głowy** - precyzyjniej i dokładniej

---

## 🔧 Zmiany techniczne

### 1. **Nowa biblioteka: `roboflow`**

**Przed:**
```python
from ultralytics import YOLO
GLOBAL_YOLO_MODEL_ANONYMIZATION = YOLO("yolov8n.pt")
```

**Po:**
```python
from roboflow import Roboflow

rf = Roboflow(api_key="DAWQI4w1KCHH1MlWH7t4")
try:
    GLOBAL_YOLO_MODEL_ANONYMIZATION = rf.model("heads-detection/1")
except:
    try:
        workspace = rf.workspace("heads-detection")
        project = workspace.project("heads-detection")
        GLOBAL_YOLO_MODEL_ANONYMIZATION = project.version(1).model
    except:
        workspace = rf.workspace()
        project = workspace.project("heads-detection")
        GLOBAL_YOLO_MODEL_ANONYMIZATION = project.version(1).model
```

**Lokalizacja:** `app.py` linie 79-102

---

### 2. **Zmiana formatu danych detekcji**

**Przed (YOLO ultralytics):**
```python
results = model(frame, verbose=False)
for result in results:
    boxes = result.boxes
    for box in boxes:
        class_id = int(box.cls[0])  # 0 = person
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)  # Gotowe współrzędne
```

**Po (Roboflow):**
```python
prediction = model.predict(image_path, confidence=40, overlap=30)
results = prediction.json()

for det in results.get('predictions', []):
    confidence = det.get('confidence', 0)  # 0-1 (nie 0-100)
    center_x = int(det['x'])      # Środek X
    center_y = int(det['y'])      # Środek Y
    width = int(det['width'])     # Szerokość
    height = int(det['height'])   # Wysokość
    
    # Konwersja na (x1, y1, x2, y2)
    x1 = center_x - width // 2
    y1 = center_y - height // 2
    x2 = center_x + width // 2
    y2 = center_y + height // 2
```

**Kluczowe różnice:**
- Roboflow zwraca **środek + wymiary** zamiast bezpośrednio (x1, y1, x2, y2)
- Confidence jest w zakresie **0-1** (nie 0-100)
- Model wykrywa **tylko głowy** (nie trzeba filtrować po `class_id`)
- API wymaga **ścieżki do pliku** (nie numpy array)

---

### 3. **Zmiana logiki anonimizacji**

**Przed (procentowe rozmycie):**
```python
# Oblicz górną część ciała (50% od góry)
person_height = y2 - y1
upper_body_height = int(person_height * 0.50)
roi_y2 = y1 + upper_body_height

# Zamazuj tylko górną część
roi = frame[y1:roi_y2, x1:x2]
```

**Po (cała głowa):**
```python
# Zamazuj cały bounding box głowy
roi = frame[y1:y2, x1:x2]
blur = cv2.GaussianBlur(roi, (99, 99), 30)
frame[y1:y2, x1:x2] = blur
```

**Efekt:** Zamazywanie jest teraz **precyzyjne** - tylko głowa, bez rąk i innych części ciała.

---

### 4. **Obsługa tymczasowych plików**

Roboflow API wymaga **ścieżki do pliku**, nie numpy array. Dodano konwersję:

```python
import tempfile

# Zapisz klatkę tymczasowo
with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
    temp_path = tmp.name
    cv2.imwrite(temp_path, frame)

try:
    # Wykryj głowy
    prediction = model.predict(temp_path, confidence=40, overlap=30)
    results = prediction.json()
    # ... przetwarzanie ...
finally:
    # Usuń tymczasowy plik
    os.remove(temp_path)
```

**Lokalizacje:**
- `app.py`: funkcja `anonymize_frame()` (linie 839-895)
- `camera_controller.py`: metoda `anonymize_frame_logic()` (linie 1130-1180)

---

## 📁 Zmienione pliki

### **app.py**
1. **Import:** Dodano `from roboflow import Roboflow` (linia 27)
2. **Inicjalizacja modelu:** Sekcja "2. YOLO Model dla anonimizacji" (linie 79-102)
   - Zmieniono z `YOLO("yolov8n.pt")` na `Roboflow().model("heads-detection/1")`
3. **Funkcja `anonymize_frame()`:** (linie 817-903)
   - Zmieniono format danych z YOLO na Roboflow
   - Dodano obsługę tymczasowych plików
   - Usunięto logikę procentowego rozmycia

### **camera_controller.py**
1. **Klasa `AnonymizerWorker`:**
   - **Docstring:** Zaktualizowano opis (linie 1518-1525)
   - **`__init__`:** Usunięto parametr `upper_body_ratio` (linia 1527-1530)
   - **Komunikaty:** Zmieniono z "górne X% ciała" na "cała głowa" (linia 1525-1526)

2. **Metoda `_anonymize_faces()`:** (linie 1933-2028)
   - Zmieniono z YOLO API na Roboflow API
   - Zmieniono format danych (środek + wymiary → x1, y1, x2, y2)
   - Usunięto logikę procentowego rozmycia
   - Zamazuje teraz całą głowę

3. **Metoda `anonymize_frame_logic()`:** (linie 1102-1189)
   - Zmieniono z YOLO API na Roboflow API
   - Dodano obsługę tymczasowych plików
   - Zmieniono format danych
   - Zamazuje teraz całą głowę

### **requirements.txt**
- Dodano: `roboflow` (bez pinowania wersji, aby użyć najnowszej kompatybilnej z Python 3.13)

---

## 🔑 Parametry modelu Roboflow

```python
prediction = model.predict(
    image_path, 
    confidence=40,  # 0-100: Minimalna pewność detekcji (40%)
    overlap=30      # 0-100: Maksymalne nakładanie się detekcji (30%)
)
```

**Format wyniku JSON:**
```json
{
    "predictions": [
        {
            "x": 609,              # Pozycja X środka
            "y": 236,              # Pozycja Y środka
            "width": 318,          # Szerokość bounding box
            "height": 448,         # Wysokość bounding box
            "confidence": 0.83,    # Pewność (0-1)
            "class": "head",       # Klasa obiektu
            "class_id": 0          # ID klasy
        }
    ],
    "image": {
        "width": "1280",
        "height": "720"
    }
}
```

---

## 🎯 Model Roboflow

- **Workspace:** `heads-detection`
- **Projekt:** `heads-detection`
- **Wersja:** `1`
- **API Key:** `DAWQI4w1KCHH1MlWH7t4` (hardcoded w `app.py` linia 83)
- **Typ:** Head detection (wykrywa tylko głowy, nie całe osoby)

---

## ⚠️ Ważne uwagi

1. **API Key:** Obecnie hardcoded w kodzie. W produkcji powinien być w zmiennych środowiskowych:
   ```python
   api_key = os.getenv("ROBOFLOW_API_KEY", "DAWQI4w1KCHH1MlWH7t4")
   ```

2. **Tymczasowe pliki:** Kod tworzy i usuwa tymczasowe pliki dla każdej klatki. W przypadku dużej liczby klatek może to wpłynąć na wydajność.

3. **Wydajność:** Roboflow API może być wolniejsze niż lokalny model YOLO, ponieważ:
   - Wymaga zapisu/odczytu plików
   - Może używać API online (zależnie od konfiguracji)

4. **Fallback:** Kod ma 3 poziomy fallbacku przy ładowaniu modelu, aby obsłużyć różne warianty API Roboflow.

---

## 📊 Porównanie: Przed vs Po

| Aspekt | Przed (YOLO) | Po (Roboflow) |
|--------|--------------|---------------|
| **Wykrywanie** | Całe osoby (klasa 0) | Tylko głowy |
| **Rozmycie** | 50% górnej części ciała | Cała głowa |
| **Format danych** | (x1, y1, x2, y2) bezpośrednio | Środek (x, y) + width, height |
| **Confidence** | 0-1 (float) | 0-1 (float) |
| **Input** | numpy array | Ścieżka do pliku |
| **Biblioteka** | `ultralytics` | `roboflow` |
| **Precyzja** | Niska (zamazuje ręce) | Wysoka (tylko głowa) |

---

## 🚀 Instalacja

```bash
pip install roboflow
```

Lub zaktualizować wszystkie zależności:
```bash
pip install -r requirements.txt
```

**Wersja:** Najnowsza kompatybilna z Python 3.13 (obecnie `roboflow==1.2.11`)

---

## 📝 Przykład użycia

```python
from roboflow import Roboflow
import cv2
import tempfile
import os

# Inicjalizacja
rf = Roboflow(api_key="DAWQI4w1KCHH1MlWH7t4")
model = rf.model("heads-detection/1")

# Wykrywanie na obrazie
image = cv2.imread("obraz.jpg")

# Zapisz tymczasowo
with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
    temp_path = tmp.name
    cv2.imwrite(temp_path, image)

try:
    # Predykcja
    prediction = model.predict(temp_path, confidence=40, overlap=30)
    results = prediction.json()
    
    # Przetwarzanie wyników
    for det in results.get('predictions', []):
        if det['confidence'] >= 0.4:
            center_x = int(det['x'])
            center_y = int(det['y'])
            width = int(det['width'])
            height = int(det['height'])
            
            x1 = center_x - width // 2
            y1 = center_y - height // 2
            x2 = center_x + width // 2
            y2 = center_y + height // 2
            
            # Zamazuj głowę
            roi = image[y1:y2, x1:x2]
            blur = cv2.GaussianBlur(roi, (99, 99), 30)
            image[y1:y2, x1:x2] = blur
finally:
    os.remove(temp_path)
```

---

## 🔍 Główne funkcje używające modelu

1. **`app.py::anonymize_frame()`** - Anonimizacja klatek dla config snapshot
2. **`camera_controller.py::_anonymize_faces()`** - Offline anonimizacja zapisanych obrazów
3. **`camera_controller.py::anonymize_frame_logic()`** - Anonimizacja klatek w czasie rzeczywistym

Wszystkie trzy funkcje zostały zaktualizowane do używania API Roboflow.

---

## ✅ Status

- ✅ Model Roboflow zintegrowany
- ✅ Wszystkie funkcje anonimizacji zaktualizowane
- ✅ Biblioteka dodana do requirements.txt
- ✅ Kompatybilność z Python 3.13
- ✅ Testy instalacji zakończone pomyślnie

**Data zmian:** 2025-01-XX
**Wersja modelu:** heads-detection/1
**Biblioteka:** roboflow==1.2.11

