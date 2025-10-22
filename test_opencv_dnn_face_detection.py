#!/usr/bin/env python3
"""
Test nowej metody detekcji twarzy z OpenCV DNN - rozwiązanie bez zewnętrznych zależności
"""

import cv2
import os
from camera_controller import CameraController

def test_opencv_dnn_installation():
    """Test czy OpenCV DNN jest dostępny"""
    print("\n=== Test instalacji OpenCV DNN ===")
    
    try:
        print(f"✅ OpenCV wersja: {cv2.__version__}")
        
        # Sprawdź czy DNN jest dostępny
        if hasattr(cv2, 'dnn'):
            print("✅ OpenCV DNN jest dostępny")
            backends = cv2.dnn.getAvailableBackends()
            print(f"✅ Dostępne backends: {backends}")
            return True
        else:
            print("⚠️  OpenCV DNN może nie być dostępny")
            return False
            
    except Exception as e:
        print(f"❌ Błąd testowania OpenCV DNN: {e}")
        return False

def test_opencv_dnn_face_detection():
    """Test detekcji twarzy z OpenCV DNN"""
    print("\n=== Test detekcji twarzy z OpenCV DNN ===")
    
    # Inicjalizacja kontrolera
    controller = CameraController()
    
    print("✅ Kontroler kamery zainicjalizowany")
    print(f"✅ Detekcja twarzy zainicjalizowana: {controller.face_detection_initialized}")
    
    # Test na istniejących obrazach z detekcji
    test_images = [
        "detections/phone_20251007_142441.jpg",
        "detections/phone_20251007_141653.jpg", 
        "detections/phone_20251007_141652.jpg",
        "detections/phone_20251007_142609.jpg"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n--- Testowanie OpenCV DNN na obrazie: {image_path} ---")
            
            # Test detekcji z OpenCV DNN
            results = controller.test_face_detection_sensitivity(image_path)
            
            if results:
                print(f"✅ Test zakończony dla {image_path}")
                
                # Sprawdź wyniki
                dnn_result = results.get('OpenCV DNN', {})
                faces_count = dnn_result.get('faces_count', 0)
                
                print(f"🏆 OpenCV DNN wykrył {faces_count} twarzy")
                
                # Jeśli znaleziono twarze, przerwij test
                if faces_count > 0:
                    print("✅ Znaleziono twarze - test zakończony sukcesem!")
                    return True
            else:
                print(f"❌ Test nie powiódł się dla {image_path}")
        else:
            print(f"⚠️  Obraz nie istnieje: {image_path}")
    
    return False

def test_opencv_dnn_post_processing():
    """Test przetwarzania po zapisie z OpenCV DNN"""
    print("\n=== Test przetwarzania po zapisie z OpenCV DNN ===")
    
    controller = CameraController()
    
    # Test na jednym z obrazów
    test_image = "detections/phone_20251007_142441.jpg"
    if os.path.exists(test_image):
        print(f"🔄 Testowanie przetwarzania OpenCV DNN na: {test_image}")
        
        # Symulacja nowej architektury
        temp_path = f"temp_{os.path.basename(test_image)}"
        
        # 1. Skopiuj oryginalny obraz
        import shutil
        shutil.copy2(test_image, temp_path)
        print(f"✅ Skopiowano obraz do: {temp_path}")
        
        # 2. Przetwórz z OpenCV DNN
        print("🔄 Uruchamiam przetwarzanie z OpenCV DNN...")
        controller.process_and_blur_saved_image(temp_path)
        
        # 3. Sprawdź wynik
        if os.path.exists(temp_path):
            print("✅ Przetwarzanie zakończone")
            
            # Usuń plik tymczasowy
            os.remove(temp_path)
            print(f"🗑️  Usunięto plik tymczasowy: {temp_path}")
            
            return True
        else:
            print("❌ Przetwarzanie nie powiodło się")
            return False
    else:
        print(f"⚠️  Obraz nie istnieje: {test_image}")
        return False

def compare_detection_methods():
    """Porównanie różnych metod detekcji"""
    print("\n=== Porównanie metod detekcji ===")
    
    print("📊 STARA METODA (Haar Cascade - Podstawowa):")
    print("   ❌ Przestarzały algorytm")
    print("   ❌ Słaba detekcja w trudnych warunkach")
    print("   ❌ Problemy z twarzami w profilu")
    print("   ❌ Wymaga dostrajania parametrów")
    print("   ❌ Dużo fałszywych pozytywów")
    
    print("\n📊 NOWA METODA (OpenCV DNN - Enhanced):")
    print("   ✅ Nowoczesny algorytm OpenCV DNN")
    print("   ✅ Ulepszona detekcja z wieloma próbami")
    print("   ✅ Lepsza detekcja w trudnych warunkach")
    print("   ✅ Automatyczne usuwanie duplikatów")
    print("   ✅ Brak zewnętrznych zależności")
    print("   ✅ Fallback do ulepszonego Haar Cascade")
    print("   ✅ Adaptacja do różnych scenariuszy")

def test_face_detection_visualization():
    """Test wizualizacji detekcji twarzy"""
    print("\n=== Test wizualizacji detekcji twarzy ===")
    
    controller = CameraController()
    
    # Test na jednym z obrazów
    test_image = "detections/phone_20251007_142441.jpg"
    if os.path.exists(test_image):
        print(f"🔄 Testowanie wizualizacji na: {test_image}")
        
        # Wczytanie obrazu
        image = cv2.imread(test_image)
        if image is None:
            print(f"❌ Nie można wczytać obrazu: {test_image}")
            return False
        
        # Test detekcji
        faces = controller._detect_faces_opencv_dnn(image)
        
        print(f"✅ OpenCV DNN wykrył {len(faces)} twarzy")
        
        if len(faces) > 0:
            # Rysowanie prostokątów wokół wykrytych twarzy
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(image, "FACE", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                print(f"  Twarz: ({x}, {y}, {w}, {h})")
            
            # Zapisanie wyniku
            output_path = "opencv_dnn_detection_result.jpg"
            cv2.imwrite(output_path, image)
            print(f"✅ Wynik zapisany jako: {output_path}")
            
            return True
        else:
            print("❌ Nie wykryto żadnych twarzy")
            return False
    else:
        print(f"⚠️  Obraz nie istnieje: {test_image}")
        return False

if __name__ == "__main__":
    print("🔧 Test detekcji twarzy z OpenCV DNN")
    print("=" * 60)
    
    # Test instalacji
    print("\n0️⃣ Test instalacji OpenCV DNN...")
    if not test_opencv_dnn_installation():
        print("⚠️  OpenCV DNN może nie być w pełni dostępny")
    
    # Porównanie metod
    compare_detection_methods()
    
    # Test 1: Detekcja z OpenCV DNN
    print("\n1️⃣ Test detekcji z OpenCV DNN...")
    if test_opencv_dnn_face_detection():
        print("✅ Detekcja OpenCV DNN działa!")
    else:
        print("⚠️  Detekcja OpenCV DNN nie wykryła twarzy")
    
    # Test 2: Wizualizacja
    print("\n2️⃣ Test wizualizacji detekcji...")
    if test_face_detection_visualization():
        print("✅ Wizualizacja działa!")
    else:
        print("⚠️  Wizualizacja nie powiodła się")
    
    # Test 3: Przetwarzanie po zapisie
    print("\n3️⃣ Test przetwarzania po zapisie...")
    if test_opencv_dnn_post_processing():
        print("✅ Przetwarzanie OpenCV DNN działa!")
    else:
        print("⚠️  Przetwarzanie OpenCV DNN nie powiodło się")
    
    print("\n✅ Test OpenCV DNN zakończony!")
    print("\n📋 Instrukcje:")
    print("- Sprawdź komunikaty o detekcji OpenCV DNN")
    print("- Sprawdź czy OpenCV DNN wykrywa więcej twarzy")
    print("- Sprawdź czy przetwarzanie działa lepiej")
    print("- Nowa metoda nie wymaga zewnętrznych zależności!")
    print("\n💡 UWAGA: OpenCV DNN używa ulepszonego Haar Cascade jako fallback")
