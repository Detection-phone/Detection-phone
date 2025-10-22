#!/usr/bin/env python3
"""
DEBUG: Skrypt testowy do debugowania detekcji twarzy
Uruchom ten skrypt, aby przetestować czy detekcja twarzy w ogóle działa.
"""

import cv2
import os
from camera_controller import CameraController

def test_face_detection():
    """Test podstawowej detekcji twarzy"""
    print("=== DEBUG: Test detekcji twarzy ===")
    
    # Inicjalizacja kontrolera
    controller = CameraController()
    
    # Sprawdzenie czy klasyfikator jest załadowany
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
        print("Sprawdź czy OpenCV jest poprawnie zainstalowany")
        return False
    
    print("✅ Klasyfikator twarzy załadowany pomyślnie")
    
    # Test na jednym z istniejących obrazów z detekcji
    test_images = [
        "detections/phone_20251001_173931.jpg",
        "detections/phone_20251001_173832.jpg", 
        "detections/phone_20250531_200454.jpg"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n--- Testowanie na obrazie: {image_path} ---")
            success = controller.test_face_detection_static(image_path)
            if success:
                print(f"✅ Detekcja twarzy działa na {image_path}")
                break
            else:
                print(f"❌ Brak wykrytych twarzy na {image_path}")
        else:
            print(f"⚠️  Obraz nie istnieje: {image_path}")
    
    return True

def test_camera_face_detection():
    """Test detekcji twarzy na żywo z kamery"""
    print("\n=== DEBUG: Test detekcji twarzy na żywo ===")
    
    controller = CameraController()
    
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
        return False
    
    print("✅ Rozpoczynam test na żywo...")
    print("📹 Uruchamiam kamerę...")
    print("🔍 Szukam twarzy w strumieniu wideo...")
    print("📝 Sprawdź konsolę pod kątem komunikatów 'DEBUG: Znaleziono twarz!'")
    print("🔴 Czerwone prostokąty powinny pojawić się wokół wykrytych twarzy")
    print("📊 System automatycznie dostosuje parametry do rozdzielczości kamery")
    print("⏹️  Naciśnij 'q' aby zakończyć test")
    print("\n💡 TIP: Jeśli używasz Iriun Webcam, system wykryje wysoką rozdzielczość")
    print("   i automatycznie użyje większych parametrów minSize (150x150)")
    
    # Uruchomienie kamery z debugowaniem
    controller.start_camera()
    
    return True

if __name__ == "__main__":
    print("🔧 DEBUG: Test detekcji twarzy")
    print("=" * 50)
    
    # Test 1: Sprawdzenie czy klasyfikator działa
    print("\n1️⃣ Test podstawowy...")
    if not test_face_detection():
        print("❌ Test podstawowy nie przeszedł!")
        exit(1)
    
    # Test 2: Test na żywo (opcjonalny)
    print("\n2️⃣ Czy chcesz przetestować detekcję na żywo z kamery? (y/n)")
    response = input().lower().strip()
    
    if response == 'y' or response == 'yes':
        test_camera_face_detection()
    else:
        print("⏭️  Pominięto test na żywo")
    
    print("\n✅ Debug zakończony!")
    print("\n📋 Instrukcje:")
    print("- Jeśli widzisz czerwone prostokąty wokół twarzy: detekcja działa ✅")
    print("- Jeśli NIE widzisz prostokątów: problem z detekcją ❌")
    print("- Sprawdź komunikaty w konsoli pod kątem błędów")
