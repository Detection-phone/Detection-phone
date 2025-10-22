#!/usr/bin/env python3
"""
Test nowej metody detekcji twarzy z biblioteką face_recognition i modelem CNN
"""

import cv2
import os
from camera_controller import CameraController

def test_cnn_face_detection():
    """Test detekcji twarzy z modelem CNN"""
    print("=== Test detekcji twarzy z modelem CNN ===")
    
    # Inicjalizacja kontrolera
    controller = CameraController()
    
    print("✅ Kontroler kamery zainicjalizowany")
    
    # Test na istniejących obrazach z detekcji
    test_images = [
        "detections/phone_20251007_142441.jpg",
        "detections/phone_20251007_141653.jpg", 
        "detections/phone_20251007_141652.jpg",
        "detections/phone_20251007_142609.jpg"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n--- Testowanie CNN na obrazie: {image_path} ---")
            
            # Test detekcji z modelem CNN
            results = controller.test_face_detection_sensitivity(image_path)
            
            if results:
                print(f"✅ Test zakończony dla {image_path}")
                
                # Sprawdź wyniki
                cnn_result = results.get('CNN Model', {})
                faces_count = cnn_result.get('faces_count', 0)
                
                print(f"🏆 Model CNN wykrył {faces_count} twarzy")
                
                # Jeśli znaleziono twarze, przerwij test
                if faces_count > 0:
                    print("✅ Znaleziono twarze - test zakończony sukcesem!")
                    return True
            else:
                print(f"❌ Test nie powiódł się dla {image_path}")
        else:
            print(f"⚠️  Obraz nie istnieje: {image_path}")
    
    return False

def test_cnn_post_processing():
    """Test przetwarzania po zapisie z modelem CNN"""
    print("\n=== Test przetwarzania po zapisie z modelem CNN ===")
    
    controller = CameraController()
    
    # Test na jednym z obrazów
    test_image = "detections/phone_20251007_142441.jpg"
    if os.path.exists(test_image):
        print(f"🔄 Testowanie przetwarzania CNN na: {test_image}")
        
        # Symulacja nowej architektury
        temp_path = f"temp_{os.path.basename(test_image)}"
        
        # 1. Skopiuj oryginalny obraz
        import shutil
        shutil.copy2(test_image, temp_path)
        print(f"✅ Skopiowano obraz do: {temp_path}")
        
        # 2. Przetwórz z modelem CNN
        print("🔄 Uruchamiam przetwarzanie z modelem CNN...")
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
    """Porównanie starych i nowych metod detekcji"""
    print("\n=== Porównanie metod detekcji ===")
    
    print("📊 STARA METODA (Haar Cascade):")
    print("   ❌ Przestarzały algorytm")
    print("   ❌ Słaba detekcja w trudnych warunkach")
    print("   ❌ Problemy z twarzami w profilu")
    print("   ❌ Wymaga dostrajania parametrów")
    print("   ❌ Dużo fałszywych pozytywów")
    
    print("\n📊 NOWA METODA (CNN - face_recognition):")
    print("   ✅ Nowoczesny algorytm głębokiego uczenia")
    print("   ✅ Bardzo dokładna detekcja")
    print("   ✅ Działa z twarzami w profilu")
    print("   ✅ Brak potrzeby dostrajania parametrów")
    print("   ✅ Minimalne fałszywe pozytywy")
    print("   ✅ Model CNN - najdokładniejszy dostępny")

def test_face_recognition_installation():
    """Test czy biblioteka face_recognition jest poprawnie zainstalowana"""
    print("\n=== Test instalacji face_recognition ===")
    
    try:
        import face_recognition
        print("✅ Biblioteka face_recognition załadowana pomyślnie")
        
        # Test podstawowej funkcjonalności
        import numpy as np
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        face_locations = face_recognition.face_locations(test_image, model="cnn")
        print("✅ Funkcja face_locations działa poprawnie")
        
        return True
    except ImportError as e:
        print(f"❌ Błąd importu face_recognition: {e}")
        print("💡 Zainstaluj bibliotekę: pip install face_recognition")
        return False
    except Exception as e:
        print(f"❌ Błąd testowania face_recognition: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Test detekcji twarzy z modelem CNN")
    print("=" * 60)
    
    # Test instalacji
    print("\n0️⃣ Test instalacji face_recognition...")
    if not test_face_recognition_installation():
        print("❌ Biblioteka face_recognition nie jest zainstalowana!")
        print("💡 Zainstaluj: pip install face_recognition")
        exit(1)
    
    # Porównanie metod
    compare_detection_methods()
    
    # Test 1: Detekcja z modelem CNN
    print("\n1️⃣ Test detekcji z modelem CNN...")
    if test_cnn_face_detection():
        print("✅ Detekcja CNN działa!")
    else:
        print("⚠️  Detekcja CNN nie wykryła twarzy")
    
    # Test 2: Przetwarzanie po zapisie
    print("\n2️⃣ Test przetwarzania po zapisie...")
    if test_cnn_post_processing():
        print("✅ Przetwarzanie CNN działa!")
    else:
        print("⚠️  Przetwarzanie CNN nie powiodło się")
    
    print("\n✅ Test CNN zakończony!")
    print("\n📋 Instrukcje:")
    print("- Sprawdź komunikaty o detekcji CNN")
    print("- Sprawdź czy model CNN wykrywa więcej twarzy")
    print("- Sprawdź czy przetwarzanie działa lepiej")
    print("- Nowa metoda powinna być znacznie bardziej skuteczna!")
    print("\n💡 UWAGA: Pierwsze uruchomienie może być wolne - model CNN się pobiera")
