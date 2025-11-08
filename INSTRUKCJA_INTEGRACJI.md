# 📋 Instrukcja: Jak zaimplementować model Roboflow do innego projektu

## 🚀 Krok 1: Instalacja zależności

W swoim nowym projekcie zainstaluj bibliotekę Roboflow:

```bash
pip install roboflow
```

Lub jeśli masz problemy z uprawnieniami (Windows):
```bash
pip install --user roboflow
```

---

## 📦 Krok 2: Podstawowa implementacja

### Opcja A: Prosta funkcja (dla szybkiego użycia)

```python
from roboflow import Roboflow
import os

def init_roboflow_model(api_key="DAWQI4w1KCHH1MlWH7t4"):
    """
    Inicjalizuje model Roboflow do detekcji głów.
    
    Args:
        api_key: Twój klucz API Roboflow
    
    Returns:
        model: Zainicjalizowany model Roboflow
    """
    rf = Roboflow(api_key=api_key)
    
    try:
        # Próba bezpośredniego dostępu
        model = rf.model("heads-detection/1")
    except:
        try:
            # Standardowe podejście
            workspace = rf.workspace("heads-detection")
            project = workspace.project("heads-detection")
            model = project.version(1).model
        except:
            # Alternatywne podejście
            workspace = rf.workspace()
            project = workspace.project("heads-detection")
            model = project.version(1).model
    
    return model

def detect_heads(image_path, model, confidence=40, overlap=30):
    """
    Wykonuje detekcję głów na obrazie.
    
    Args:
        image_path: Ścieżka do obrazu
        model: Zainicjalizowany model Roboflow
        confidence: Próg pewności (0-100)
        overlap: Próg nakładania się (0-100)
    
    Returns:
        dict: Wyniki predykcji w formacie JSON
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Nie znaleziono pliku: {image_path}")
    
    prediction = model.predict(image_path, confidence=confidence, overlap=overlap)
    return prediction.json()

# Przykład użycia:
# model = init_roboflow_model()
# results = detect_heads("sciezka/do/obrazu.jpg", model)
# print(results)
```

---

### Opcja B: Klasa (dla większych projektów)

```python
from roboflow import Roboflow
import os
from typing import Dict, Optional

class RoboflowHeadDetector:
    """Klasa do obsługi detekcji głów za pomocą Roboflow."""
    
    def __init__(self, api_key: str = "DAWQI4w1KCHH1MlWH7t4"):
        """
        Inicjalizuje detektor.
        
        Args:
            api_key: Klucz API Roboflow
        """
        self.api_key = api_key
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Inicjalizuje model Roboflow."""
        rf = Roboflow(api_key=self.api_key)
        
        try:
            self.model = rf.model("heads-detection/1")
        except:
            try:
                workspace = rf.workspace("heads-detection")
                project = workspace.project("heads-detection")
                self.model = project.version(1).model
            except:
                workspace = rf.workspace()
                project = workspace.project("heads-detection")
                self.model = project.version(1).model
    
    def predict(self, image_path: str, confidence: int = 40, overlap: int = 30) -> Dict:
        """
        Wykonuje predykcję na obrazie.
        
        Args:
            image_path: Ścieżka do obrazu
            confidence: Próg pewności (0-100)
            overlap: Próg nakładania się (0-100)
        
        Returns:
            dict: Wyniki predykcji
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Nie znaleziono pliku: {image_path}")
        
        prediction = self.model.predict(image_path, confidence=confidence, overlap=overlap)
        return prediction.json()
    
    def predict_and_save(self, image_path: str, output_path: str, 
                        confidence: int = 40, overlap: int = 30) -> Dict:
        """
        Wykonuje predykcję i zapisuje wynik z zaznaczonymi detekcjami.
        
        Args:
            image_path: Ścieżka do obrazu wejściowego
            output_path: Ścieżka do zapisania wyniku
            confidence: Próg pewności (0-100)
            overlap: Próg nakładania się (0-100)
        
        Returns:
            dict: Wyniki predykcji
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Nie znaleziono pliku: {image_path}")
        
        prediction = self.model.predict(image_path, confidence=confidence, overlap=overlap)
        prediction.save(output_path)
        return prediction.json()
    
    def count_detections(self, image_path: str, confidence: int = 40, overlap: int = 30) -> int:
        """
        Zwraca liczbę wykrytych obiektów.
        
        Args:
            image_path: Ścieżka do obrazu
            confidence: Próg pewności (0-100)
            overlap: Próg nakładania się (0-100)
        
        Returns:
            int: Liczba wykrytych obiektów
        """
        results = self.predict(image_path, confidence, overlap)
        return len(results.get('predictions', []))

# Przykład użycia:
# detector = RoboflowHeadDetector()
# results = detector.predict("obraz.jpg")
# count = detector.count_detections("obraz.jpg")
# detector.predict_and_save("obraz.jpg", "wynik.jpg")
```

---

### Opcja C: Z użyciem zmiennych środowiskowych (najbezpieczniejsza)

**1. Utwórz plik `.env` w katalogu projektu:**
```
ROBOFLOW_API_KEY=DAWQI4w1KCHH1MlWH7t4
```

**2. Zainstaluj python-dotenv:**
```bash
pip install python-dotenv
```

**3. Kod:**
```python
from roboflow import Roboflow
from dotenv import load_dotenv
import os

# Załaduj zmienne środowiskowe
load_dotenv()

def get_roboflow_model():
    """Pobiera model Roboflow używając klucza API z .env"""
    api_key = os.getenv("ROBOFLOW_API_KEY")
    if not api_key:
        raise ValueError("ROBOFLOW_API_KEY nie został znaleziony w zmiennych środowiskowych!")
    
    rf = Roboflow(api_key=api_key)
    
    try:
        model = rf.model("heads-detection/1")
    except:
        try:
            workspace = rf.workspace("heads-detection")
            project = workspace.project("heads-detection")
            model = project.version(1).model
        except:
            workspace = rf.workspace()
            project = workspace.project("heads-detection")
            model = project.version(1).model
    
    return model

# Użycie:
# model = get_roboflow_model()
# prediction = model.predict("obraz.jpg")
```

---

## 🔧 Krok 3: Integracja z istniejącym kodem

### Przykład 1: Integracja z Flask (API webowe)

```python
from flask import Flask, request, jsonify
from roboflow import Roboflow
import os

app = Flask(__name__)

# Inicjalizuj model przy starcie aplikacji
rf = Roboflow(api_key="DAWQI4w1KCHH1MlWH7t4")
try:
    model = rf.model("heads-detection/1")
except:
    workspace = rf.workspace()
    project = workspace.project("heads-detection")
    model = project.version(1).model

@app.route('/detect', methods=['POST'])
def detect():
    """Endpoint do detekcji głów na przesłanym obrazie."""
    if 'image' not in request.files:
        return jsonify({'error': 'Brak obrazu'}), 400
    
    file = request.files['image']
    file_path = f"temp_{file.filename}"
    file.save(file_path)
    
    try:
        prediction = model.predict(file_path, confidence=40, overlap=30)
        results = prediction.json()
        return jsonify(results)
    finally:
        os.remove(file_path)  # Usuń tymczasowy plik

if __name__ == '__main__':
    app.run(debug=True)
```

---

### Przykład 2: Integracja z przetwarzaniem wielu obrazów

```python
from roboflow import Roboflow
import os
from pathlib import Path

def process_folder(folder_path, output_folder, model, confidence=40):
    """
    Przetwarza wszystkie obrazy w folderze.
    
    Args:
        folder_path: Ścieżka do folderu z obrazami
        output_folder: Folder na wyniki
        model: Model Roboflow
        confidence: Próg pewności
    """
    folder = Path(folder_path)
    output = Path(output_folder)
    output.mkdir(exist_ok=True)
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    
    for image_file in folder.iterdir():
        if image_file.suffix.lower() in image_extensions:
            print(f"Przetwarzanie: {image_file.name}")
            
            prediction = model.predict(str(image_file), confidence=confidence, overlap=30)
            output_path = output / f"result_{image_file.name}"
            prediction.save(str(output_path))
            
            results = prediction.json()
            print(f"  Wykryto {len(results['predictions'])} obiektów")

# Użycie:
# model = init_roboflow_model()  # z Opcji A
# process_folder("obrazy/", "wyniki/", model)
```

---

## 📝 Krok 4: Ważne informacje

### Parametry predykcji:
- **confidence** (0-100): Minimalna pewność detekcji. Wyższa wartość = mniej fałszywych alarmów, ale może przegapić słabe detekcje
- **overlap** (0-100): Maksymalne nakładanie się detekcji. Niższa wartość = mniej duplikatów

### Format wyniku:
```python
{
    'predictions': [
        {
            'x': 609,              # Pozycja X środka
            'y': 236,              # Pozycja Y środka
            'width': 318,          # Szerokość bounding box
            'height': 448,         # Wysokość bounding box
            'confidence': 0.83,    # Pewność (0-1)
            'class': 'person',     # Klasa obiektu
            'class_id': 0          # ID klasy
        }
    ],
    'image': {
        'width': '1280',
        'height': '720'
    }
}
```

### Bezpieczeństwo:
- ⚠️ **NIGDY** nie commituj klucza API do repozytorium Git!
- Używaj zmiennych środowiskowych (`.env`) lub plików konfiguracyjnych
- Dodaj `.env` do `.gitignore`

---

## 🎯 Szybki start (kopiuj-wklej)

```python
from roboflow import Roboflow
import os

# 1. Inicjalizacja
rf = Roboflow(api_key="TWÓJ_KLUCZ_API")
workspace = rf.workspace()
project = workspace.project("heads-detection")
model = project.version(1).model

# 2. Predykcja
prediction = model.predict("obraz.jpg", confidence=40, overlap=30)

# 3. Wyniki
results = prediction.json()
print(f"Wykryto {len(results['predictions'])} obiektów")

# 4. Zapis z zaznaczeniami
prediction.save("wynik.jpg")
```

---

## ❓ Rozwiązywanie problemów

**Problem:** `AttributeError: 'Roboflow' object has no attribute 'universe'`
- **Rozwiązanie:** Użyj `workspace()` zamiast `universe()`

**Problem:** `FileNotFoundError`
- **Rozwiązanie:** Sprawdź czy ścieżka do obrazu jest poprawna (używaj `/` lub `os.path.join()`)

**Problem:** Model nie ładuje się
- **Rozwiązanie:** Sprawdź czy klucz API jest poprawny i czy masz dostęp do modelu

---

## 📚 Dodatkowe zasoby

- Dokumentacja Roboflow: https://docs.roboflow.com/
- Python SDK: https://github.com/roboflow/roboflow-python

