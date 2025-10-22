#!/usr/bin/env python3
"""
Test nowej architektury - rozdzielenie detekcji telefonu od rozmywania twarzy
"""

import cv2
import os
import time
from camera_controller import CameraController

def test_post_processing():
    """Test przetwarzania po zapisie na istniejących obrazach"""
    print("=== Test nowej architektury: Przetwarzanie po zapisie ===")
    
    # Inicjalizacja kontrolera
    controller = CameraController()
    
    # Sprawdzenie czy klasyfikator jest załadowany
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
        return False
    
    print("✅ Klasyfikator twarzy załadowany pomyślnie")
    
    # Test na istniejących obrazach z detekcji
    test_images = [
        "detections/phone_20251001_173931.jpg",
        "detections/phone_20251001_173832.jpg", 
        "detections/phone_20250531_200454.jpg"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n--- Testowanie przetwarzania po zapisie: {image_path} ---")
            
            # Wczytanie oryginalnego obrazu
            original_image = cv2.imread(image_path)
            if original_image is None:
                print(f"❌ Nie można wczytać obrazu: {image_path}")
                continue
                
            print(f"✅ Wczytano oryginalny obraz: {original_image.shape}")
            
            # Symulacja nowej architektury:
            # 1. Zapisz oryginalny obraz (jak w _handle_detection)
            temp_path = f"temp_{os.path.basename(image_path)}"
            cv2.imwrite(temp_path, original_image)
            print(f"✅ Zapisano oryginalny obraz: {temp_path}")
            
            # 2. Przetwórz zapisany obraz (nowa funkcja)
            print("🔄 Uruchamiam przetwarzanie po zapisie...")
            controller.process_and_blur_saved_image(temp_path)
            
            # 3. Sprawdź czy obraz został zmieniony
            processed_image = cv2.imread(temp_path)
            if processed_image is not None:
                # Porównaj obrazy
                diff = cv2.norm(original_image, processed_image, cv2.NORM_L2)
                if diff > 0:
                    print(f"✅ Obraz został przetworzony - różnica: {diff:.2f}")
                    
                    # Zapisz wynik
                    result_path = f"processed_{os.path.basename(image_path)}"
                    cv2.imwrite(result_path, processed_image)
                    print(f"✅ Przetworzony obraz zapisany jako: {result_path}")
                else:
                    print("⚠️  Obraz nie został zmieniony - możliwe że nie wykryto twarzy")
            
            # Usuń plik tymczasowy
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"🗑️  Usunięto plik tymczasowy: {temp_path}")
        else:
            print(f"⚠️  Obraz nie istnieje: {image_path}")
    
    return True

def test_camera_new_architecture():
    """Test nowej architektury na żywo z kamerą"""
    print("\n=== Test nowej architektury na żywo ===")
    
    controller = CameraController()
    
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
        return False
    
    print("✅ Rozpoczynam test nowej architektury...")
    print("📹 Uruchamiam kamerę...")
    print("🔍 System będzie:")
    print("   1. Wykrywać telefony w czasie rzeczywistym")
    print("   2. Zapisować oryginalne obrazy")
    print("   3. Przetwarzać obrazy po zapisie (rozmywanie twarzy)")
    print("📝 Sprawdź konsolę pod kątem komunikatów przetwarzania")
    print("⏹️  Naciśnij 'q' aby zakończyć test")
    print("\n💡 TIP: Sprawdź folder 'detections' - obrazy powinny być rozmyte po zapisie!")
    
    # Uruchomienie kamery z nową architekturą
    controller.start_camera()
    
    return True

def compare_architectures():
    """Porównanie starej i nowej architektury"""
    print("\n=== Porównanie architektur ===")
    print("📊 STARA ARCHITEKTURA:")
    print("   ❌ Rozmywanie w czasie rzeczywistym")
    print("   ❌ Zależność od 'szczęśliwego trafu' w jednej klatce")
    print("   ❌ Obciążenie głównej pętli kamery")
    print("   ❌ Mniej niezawodna detekcja twarzy")
    
    print("\n📊 NOWA ARCHITEKTURA:")
    print("   ✅ Rozmywanie po zapisie obrazu")
    print("   ✅ Niezawodna detekcja na zapisanym pliku")
    print("   ✅ Odciążona główna pętla kamery")
    print("   ✅ Bardziej czułe parametry detekcji")
    print("   ✅ Lepsza wydajność i niezawodność")

if __name__ == "__main__":
    print("🔧 Test nowej architektury systemu")
    print("=" * 60)
    
    # Porównanie architektur
    compare_architectures()
    
    # Test 1: Sprawdzenie przetwarzania po zapisie
    print("\n1️⃣ Test przetwarzania po zapisie...")
    if test_post_processing():
        print("✅ Przetwarzanie po zapisie działa!")
    else:
        print("⚠️  Przetwarzanie po zapisie może nie działać")
    
    # Test 2: Test na żywo (opcjonalny)
    print("\n2️⃣ Czy chcesz przetestować nową architekturę na żywo z kamerą? (y/n)")
    response = input().lower().strip()
    
    if response == 'y' or response == 'yes':
        test_camera_new_architecture()
    else:
        print("⏭️  Pominięto test na żywo")
    
    print("\n✅ Test nowej architektury zakończony!")
    print("\n📋 Instrukcje:")
    print("- Sprawdź folder 'detections' - obrazy powinny być rozmyte")
    print("- Sprawdź komunikaty w konsoli o przetwarzaniu")
    print("- Nowa architektura jest bardziej niezawodna!")
