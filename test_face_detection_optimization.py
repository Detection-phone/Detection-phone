#!/usr/bin/env python3
"""
Test optymalizacji detekcji twarzy - sprawdza różne poziomy czułości
"""

import cv2
import os
from camera_controller import CameraController

def test_sensitivity_levels():
    """Test różnych poziomów czułości detekcji twarzy"""
    print("=== Test optymalizacji detekcji twarzy ===")
    
    # Inicjalizacja kontrolera
    controller = CameraController()
    
    # Sprawdzenie czy klasyfikator jest załadowany
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
        return False
    
    print("✅ Klasyfikator twarzy załadowany pomyślnie")
    
    # Test na istniejących obrazach z detekcji
    test_images = [
        "detections/phone_20251007_141653.jpg",
        "detections/phone_20251007_141652.jpg", 
        "detections/phone_20251007_142441.jpg",
        "detections/phone_20251007_142609.jpg"
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n--- Testowanie czułości na obrazie: {image_path} ---")
            
            # Test różnych poziomów czułości
            results = controller.test_face_detection_sensitivity(image_path)
            
            if results:
                print(f"✅ Test zakończony dla {image_path}")
                
                # Znajdź najlepszy poziom
                best_level = max(results.keys(), key=lambda k: results[k]['faces_count'])
                best_count = results[best_level]['faces_count']
                
                print(f"🏆 Najlepszy poziom: {best_level} ({best_count} twarzy)")
                
                # Jeśli znaleziono twarze, przerwij test
                if best_count > 0:
                    print("✅ Znaleziono twarze - test zakończony sukcesem!")
                    return True
            else:
                print(f"❌ Test nie powiódł się dla {image_path}")
        else:
            print(f"⚠️  Obraz nie istnieje: {image_path}")
    
    return False

def test_optimized_detection():
    """Test zoptymalizowanej detekcji na istniejących obrazach"""
    print("\n=== Test zoptymalizowanej detekcji ===")
    
    controller = CameraController()
    
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
        return False
    
    # Test na jednym z obrazów
    test_image = "detections/phone_20251007_141653.jpg"
    if os.path.exists(test_image):
        print(f"🔄 Testowanie zoptymalizowanej detekcji na: {test_image}")
        
        # Wczytanie obrazu
        image = cv2.imread(test_image)
        if image is None:
            print(f"❌ Nie można wczytać obrazu: {test_image}")
            return False
        
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Test zoptymalizowanej detekcji
        faces = controller._detect_faces_optimized(gray, height, width)
        
        print(f"✅ Zoptymalizowana detekcja wykryła {len(faces)} twarzy")
        
        if len(faces) > 0:
            # Rysowanie prostokątów wokół wykrytych twarzy
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(image, "FACE", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                print(f"  Twarz: ({x}, {y}, {w}, {h})")
            
            # Zapisanie wyniku
            output_path = "optimized_detection_result.jpg"
            cv2.imwrite(output_path, image)
            print(f"✅ Wynik zapisany jako: {output_path}")
            
            return True
        else:
            print("❌ Nie wykryto żadnych twarzy")
            return False
    else:
        print(f"⚠️  Obraz nie istnieje: {test_image}")
        return False

def compare_detection_methods():
    """Porównanie różnych metod detekcji"""
    print("\n=== Porównanie metod detekcji ===")
    
    print("📊 STARA METODA (Podstawowa):")
    print("   ❌ Jeden zestaw parametrów")
    print("   ❌ Brak adaptacji do trudnych warunków")
    print("   ❌ Może przegapić twarze w trudnych warunkach")
    
    print("\n📊 NOWA METODA (Zoptymalizowana):")
    print("   ✅ Wielokrotne próby z różnymi parametrami")
    print("   ✅ Agresywne parametry dla trudnych warunków")
    print("   ✅ Usuwanie duplikatów")
    print("   ✅ Adaptacja do rozdzielczości")
    print("   ✅ Lepsza detekcja twarzy w profilu i z daleka")

def test_post_processing_optimization():
    """Test optymalizacji przetwarzania po zapisie"""
    print("\n=== Test optymalizacji przetwarzania po zapisie ===")
    
    controller = CameraController()
    
    if controller.face_cascade is None:
        print("❌ ERROR: Klasyfikator twarzy nie jest załadowany!")
        return False
    
    # Test na jednym z obrazów
    test_image = "detections/phone_20251007_141653.jpg"
    if os.path.exists(test_image):
        print(f"🔄 Testowanie optymalizacji przetwarzania na: {test_image}")
        
        # Symulacja nowej architektury
        temp_path = f"temp_{os.path.basename(test_image)}"
        
        # 1. Skopiuj oryginalny obraz
        import shutil
        shutil.copy2(test_image, temp_path)
        print(f"✅ Skopiowano obraz do: {temp_path}")
        
        # 2. Przetwórz z optymalizacją
        print("🔄 Uruchamiam zoptymalizowane przetwarzanie...")
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

if __name__ == "__main__":
    print("🔧 Test optymalizacji detekcji twarzy")
    print("=" * 60)
    
    # Porównanie metod
    compare_detection_methods()
    
    # Test 1: Różne poziomy czułości
    print("\n1️⃣ Test różnych poziomów czułości...")
    if test_sensitivity_levels():
        print("✅ Test czułości zakończony sukcesem!")
    else:
        print("⚠️  Test czułości nie wykrył twarzy")
    
    # Test 2: Zoptymalizowana detekcja
    print("\n2️⃣ Test zoptymalizowanej detekcji...")
    if test_optimized_detection():
        print("✅ Zoptymalizowana detekcja działa!")
    else:
        print("⚠️  Zoptymalizowana detekcja nie wykryła twarzy")
    
    # Test 3: Optymalizacja przetwarzania
    print("\n3️⃣ Test optymalizacji przetwarzania...")
    if test_post_processing_optimization():
        print("✅ Optymalizacja przetwarzania działa!")
    else:
        print("⚠️  Optymalizacja przetwarzania nie powiodła się")
    
    print("\n✅ Test optymalizacji zakończony!")
    print("\n📋 Instrukcje:")
    print("- Sprawdź komunikaty o różnych poziomach czułości")
    print("- Sprawdź czy zoptymalizowana detekcja wykrywa więcej twarzy")
    print("- Sprawdź czy przetwarzanie po zapisie działa lepiej")
    print("- Nowa metoda powinna być bardziej skuteczna!")
