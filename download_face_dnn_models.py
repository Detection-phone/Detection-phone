"""
Skrypt do pobierania modeli OpenCV DNN dla detekcji twarzy.

Te modele są opcjonalne - system działa z Haar Cascade jako fallback.
Modele DNN dają lepszą dokładność (~90% vs ~85% dla Haar).
"""

import urllib.request
import os

def download_file(url, filename):
    """Pobiera plik z URL"""
    print(f"Pobieranie {filename}...")
    try:
        urllib.request.urlretrieve(url, filename)
        print(f"✅ Pobrano: {filename}")
        return True
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return False

def main():
    print("="*60)
    print("POBIERANIE MODELI DNN DLA DETEKCJI TWARZY")
    print("="*60)
    print()
    print("Te modele są OPCJONALNE:")
    print("- System działa z Haar Cascade jako fallback")
    print("- Modele DNN dają lepszą dokładność (~90% vs ~85%)")
    print()
    
    # Sprawdź czy pliki już istnieją
    proto_file = "deploy.prototxt"
    model_file = "res10_300x300_ssd_iter_140000.caffemodel"
    
    if os.path.exists(proto_file) and os.path.exists(model_file):
        print("⚠️  Modele już istnieją!")
        response = input("Czy chcesz pobrać ponownie? (y/n): ")
        if response.lower() != 'y':
            print("Anulowano.")
            return
    
    # URLe do modeli
    proto_url = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
    model_url = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
    
    print("\nPobieranie plików...")
    print("-" * 60)
    
    # Pobierz prototxt
    success1 = download_file(proto_url, proto_file)
    
    # Pobierz model
    success2 = download_file(model_url, model_file)
    
    print("-" * 60)
    
    if success1 and success2:
        print("\n✅ SUKCES! Modele DNN zostały pobrane.")
        print()
        print("Pliki:")
        print(f"  - {proto_file}")
        print(f"  - {model_file}")
        print()
        print("System będzie używał OpenCV DNN dla anonimizacji twarzy.")
    else:
        print("\n❌ Nie udało się pobrać wszystkich plików.")
        print("System będzie używał Haar Cascade jako fallback.")

if __name__ == "__main__":
    main()

