#!/usr/bin/env python3
"""
Test rozmywania twarzy - sprawdza czy rozmywanie działa poprawnie
"""

import cv2
import os
from camera_controller import CameraController

def test_face_blur():
    """Test rozmywania twarzy na statycznym obrazie"""
    print("=== Test rozmywania twarzy ===")
    
    # Inicjalizacja kontrolera
    controller = CameraController()
    
    # Sprawdzenie czy klasyfikator jest załadowany
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
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
            print(f"\n--- Testowanie rozmywania na obrazie: {image_path} ---")
            
            # Wczytanie obrazu
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Nie można wczytać obrazu: {image_path}")
                continue
                
            print(f"✅ Wczytano obraz: {image.shape}")
            
            # Zastosowanie rozmywania twarzy
            blurred_image = controller._detect_and_blur_faces(image.copy())
            
            # Zapisanie wyniku
            output_path = f"blurred_{os.path.basename(image_path)}"
            cv2.imwrite(output_path, blurred_image)
            print(f"✅ Rozmyty obraz zapisany jako: {output_path}")
            
            # Sprawdzenie czy obraz się zmienił
            if not cv2.norm(image, blurred_image, cv2.NORM_L2) == 0:
                print("✅ Rozmywanie zostało zastosowane - obraz się zmienił")
                return True
            else:
                print("⚠️  Obraz nie został zmieniony - możliwe że nie wykryto twarzy")
        else:
            print(f"⚠️  Obraz nie istnieje: {image_path}")
    
    return False

def test_camera_face_blur():
    """Test rozmywania twarzy na żywo z kamery"""
    print("\n=== Test rozmywania twarzy na żywo ===")
    
    controller = CameraController()
    
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
        return False
    
    print("✅ Rozpoczynam test na żywo...")
    print("📹 Uruchamiam kamerę...")
    print("🔍 Szukam twarzy i rozmywam je...")
    print("📝 Sprawdź konsolę pod kątem komunikatów 'Rozmytą twarz w obszarze'")
    print("🔴 Rozmyte twarze powinny być widoczne jako rozmazane obszary")
    print("⏹️  Naciśnij 'q' aby zakończyć test")
    print("\n💡 TIP: Jeśli widzisz rozmazane twarze, rozmywanie działa!")
    
    # Uruchomienie kamery z rozmywaniem
    controller.start_camera()
    
    return True

if __name__ == "__main__":
    print("🔧 Test rozmywania twarzy")
    print("=" * 50)
    
    # Test 1: Sprawdzenie na statycznym obrazie
    print("\n1️⃣ Test na statycznym obrazie...")
    if test_face_blur():
        print("✅ Rozmywanie działa na statycznych obrazach!")
    else:
        print("⚠️  Rozmywanie może nie działać na statycznych obrazach")
    
    # Test 2: Test na żywo (opcjonalny)
    print("\n2️⃣ Czy chcesz przetestować rozmywanie na żywo z kamery? (y/n)")
    response = input().lower().strip()
    
    if response == 'y' or response == 'yes':
        test_camera_face_blur()
    else:
        print("⏭️  Pominięto test na żywo")
    
    print("\n✅ Test zakończony!")
    print("\n📋 Instrukcje:")
    print("- Jeśli widzisz rozmazane twarze: rozmywanie działa ✅")
    print("- Jeśli twarze są ostre: rozmywanie nie działa ❌")
    print("- Sprawdź komunikaty w konsoli pod kątem błędów")
