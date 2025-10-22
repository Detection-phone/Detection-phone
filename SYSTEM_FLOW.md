# 🔄 Przepływ Danych - Jak Dokładnie Działa System

## ✅ **KLUCZOWA ZASADA:**

**NIGDY nie zamazuj twarzy w real-time!**

---

## 📊 Szczegółowy przepływ:

### **1. Real-Time Loop (Main Thread)**

```
┌─────────────────────────────────────────────────┐
│  KROK 1: Odczyt klatki                          │
│  ret, frame = camera.read()                     │
│  → frame = ORYGINAŁ (bez zamazań)              │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 2: Kopia dla wyświetlania                 │
│  display_frame = frame.copy()                   │
│  → display_frame = ORYGINAŁ (bez zamazań)      │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 3: Detekcja telefonu (YOLO)              │
│  results = model(frame)  ← ORYGINALNY frame    │
│  if phone_detected:                             │
│    cv2.rectangle(display_frame, ...)  ← ramka  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 4: Zapis ORYGINALNEJ klatki              │
│  self._handle_detection(frame.copy(), conf)    │
│  → cv2.imwrite('./detections/phone_xxx.jpg',   │
│                 frame)  ← ORYGINALNY            │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 5: Dodanie do kolejki                     │
│  queue.put({                                    │
│    'filepath': './detections/phone_xxx.jpg',   │
│    'confidence': 0.95                           │
│  })                                             │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 6: Wyświetlenie ORYGINALNEJ klatki       │
│  cv2.imshow('Phone Detection', display_frame)  │
│  → display_frame = ORYGINAŁ (bez zamazań)      │
└─────────────────────────────────────────────────┘
```

**⚠️ WAŻNE:** W tym momencie:
- ✅ Plik na dysku: `./detections/phone_xxx.jpg` = **ORYGINAŁ**
- ✅ Wyświetlane okno: **ORYGINAŁ** (bez zamazań)
- ✅ Baza danych: **PUSTA** (jeszcze nie dodano)

---

### **2. Offline Anonymization (Worker Thread)**

```
┌─────────────────────────────────────────────────┐
│  KROK 1: Pobranie z kolejki                     │
│  task = queue.get()                             │
│  filepath = task['filepath']                    │
│  → './detections/phone_xxx.jpg' (ORYGINAŁ)     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 2: Wczytanie ORYGINALNEGO obrazu         │
│  image = cv2.imread(filepath)                   │
│  → image = ORYGINAŁ (z twarzami)               │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 3: Detekcja twarzy (OpenCV DNN/Haar)     │
│  faces = detect_faces(image)                    │
│  → Lista współrzędnych twarzy                   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 4: Zamazanie KAŻDEJ twarzy               │
│  for (x, y, w, h) in faces:                    │
│    face_roi = image[y:y+h, x:x+w]             │
│    blurred = GaussianBlur(face_roi, 99, 30)   │
│    image[y:y+h, x:x+w] = blurred              │
│  → image = ZANONIMIZOWANY                      │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 5: NADPISANIE pliku                      │
│  cv2.imwrite(filepath, image)                   │
│  → './detections/phone_xxx.jpg' teraz          │
│     zawiera ZANONIMIZOWANY obraz               │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  KROK 6: Zapis do bazy danych                   │
│  Detection(image_path='phone_xxx.jpg')         │
│  db.session.add(detection)                      │
│  → Baza zawiera TYLKO zanonimizowane           │
└─────────────────────────────────────────────────┘
```

**⚠️ WAŻNE:** W tym momencie:
- ✅ Plik na dysku: `./detections/phone_xxx.jpg` = **ZANONIMIZOWANY**
- ✅ Baza danych: **ZANONIMIZOWANY** obraz
- ✅ Oryginał: **NADPISANY** (nie istnieje już)

---

## 🎬 Timeline przykładowej detekcji:

```
T=0.000s  Camera odczytuje klatkę (ORYGINAŁ)
T=0.001s  Kopia dla display (ORYGINAŁ)
T=0.030s  YOLO wykrywa telefon
T=0.031s  Zapis do ./detections/phone_143022.jpg (ORYGINAŁ)
T=0.032s  Dodanie do queue
T=0.033s  Wyświetlenie na ekranie (ORYGINAŁ)
          ↓
          [Użytkownik widzi ORYGINAŁ na ekranie]
          ↓
T=1.500s  Worker pobiera z queue
T=1.501s  Worker wczytuje ./detections/phone_143022.jpg (ORYGINAŁ)
T=1.700s  Worker wykrywa 2 twarze (OpenCV DNN)
T=1.850s  Worker zamazuje obie twarze
T=1.900s  Worker NADPISUJE ./detections/phone_143022.jpg (ZANONIMIZOWANY)
T=1.910s  Worker zapisuje do bazy danych
          ↓
          [Plik teraz zawiera ZANONIMIZOWANY obraz]
```

---

## ⚠️ Co użytkownik widzi:

### **W oknie kamery (cv2.imshow):**
```
┌─────────────────────────────────┐
│  Phone Detection                 │
│                                  │
│  👤 👤  <- ORYGINALNE TWARZE    │
│    📱  <- TELEFON (czerwona ramka)│
│                                  │
└─────────────────────────────────┘
```
**BEZ zamazania!**

### **Na serwerze (http://localhost:5000/detections):**
```
┌─────────────────────────────────┐
│  Detections History              │
│                                  │
│  [Photo]                         │
│  🔒🔒  <- ZAMAZANE TWARZE       │
│    📱  <- TELEFON                │
│                                  │
└─────────────────────────────────┘
```
**Z zamazaniem!**

---

## 📁 Stan plików:

### **Moment T=0.033s (po zapisie, przed workerem):**
```
./detections/phone_143022.jpg  ← ORYGINAŁ (z twarzami)
Database: PUSTE
```

### **Moment T=1.910s (po workerze):**
```
./detections/phone_143022.jpg  ← ZANONIMIZOWANY (zamazane twarze)
Database: phone_143022.jpg ← link do ZANONIMIZOWANEGO
```

---

## ✅ Weryfikacja poprawności:

### **Test 1: Sprawdź wyświetlane okno**
```bash
python app.py
# Pokaż telefon przed kamerą
# OCZEKIWANE: Widzisz ORYGINALNE twarze (bez zamazania)
```

### **Test 2: Sprawdź plik zaraz po detekcji**
```bash
# Otwórz ./detections/phone_xxx.jpg NATYCHMIAST po detekcji
# OCZEKIWANE: ORYGINAŁ (z twarzami)
```

### **Test 3: Sprawdź plik po 2 sekundach**
```bash
# Otwórz ./detections/phone_xxx.jpg PO 2 sekundach
# OCZEKIWANE: ZANONIMIZOWANY (zamazane twarze)
```

### **Test 4: Sprawdź bazę danych**
```bash
# Otwórz http://localhost:5000/detections
# OCZEKIWANE: Wszystkie zdjęcia ZANONIMIZOWANE
```

---

## 🔒 Bezpieczeństwo:

✅ **Okno kamery:** ORYGINAŁ (prywatność użytkownika w pomieszczeniu)  
✅ **Plik przez ~2s:** ORYGINAŁ (lokalnie, nie wysłany)  
✅ **Plik po 2s:** ZANONIMIZOWANY (nadpisany)  
✅ **Baza danych:** TYLKO zanonimizowane  
✅ **Serwer:** TYLKO zanonimizowane  

---

## 🎯 Podsumowanie:

**KAMERA → Wykrywa telefon → Zapisuje ORYGINAŁ → Wyświetla ORYGINAŁ**

**(w tle asynchronicznie)**

**Worker → Zamazuje twarze → Nadpisuje plik → Zapisuje do DB**

**Rezultat:**
- Użytkownik przy kamerze: widzi ORYGINALNE twarze
- Użytkownik na serwerze: widzi ZAMAZANE twarze
- Baza danych: TYLKO zamazane

**NIGDY nie zamazuj w real-time! ✅**

