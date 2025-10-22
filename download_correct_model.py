#!/usr/bin/env python3
"""
Pobieranie prawidłowego modelu DNN dla detekcji twarzy
"""

import os
import urllib.request
import sys

def download_correct_caffe_model():
    """Pobierz prawidłowy model Caffe"""
    print("Pobieranie prawidłowego modelu Caffe...")
    
    # Sprawdź czy folder models istnieje
    if not os.path.exists("models"):
        os.makedirs("models")
        print("Utworzono folder models")
    
    model_path = "models/res10_300x300_ssd_iter_140000.caffemodel"
    
    # Usuń stary plik jeśli istnieje
    if os.path.exists(model_path):
        os.remove(model_path)
        print("Usunięto stary plik modelu")
    
    # Lista alternatywnych źródeł dla modelu Caffe
    urls = [
        "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb",
        "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb",
        "https://github.com/opencv/opencv_3rdparty/raw/master/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb",
        "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/opencv_face_detector_uint8.pb"
    ]
    
    for i, url in enumerate(urls):
        try:
            print(f"Próba {i+1}: Pobieranie z {url}")
            
            # Pobierz plik
            urllib.request.urlretrieve(url, model_path)
            
            # Sprawdź rozmiar pliku
            file_size = os.path.getsize(model_path)
            print(f"Pobrany plik ma rozmiar: {file_size} bajtów ({file_size/1024/1024:.2f} MB)")
            
            # Sprawdź czy plik ma odpowiedni rozmiar (powinien być > 5MB)
            if file_size > 5000000:  # Więcej niż 5MB
                print(f"Model pobrany pomyślnie! Rozmiar: {file_size} bajtów ({file_size/1024/1024:.2f} MB)")
                return True
            else:
                print(f"Plik jest za mały ({file_size} bajtów), próbuję następne źródło...")
                os.remove(model_path)
                continue
                
        except Exception as e:
            print(f"Błąd podczas pobierania z {url}: {e}")
            if os.path.exists(model_path):
                os.remove(model_path)
            continue
    
    print("Nie udało się pobrać prawidłowego modelu z żadnego źródła")
    return False

def create_alternative_model():
    """Stwórz alternatywny model lub użyj tylko Haar Cascade"""
    print("Tworzenie alternatywnego rozwiązania...")
    
    # Usuń problematyczny plik
    model_path = "models/res10_300x300_ssd_iter_140000.caffemodel"
    if os.path.exists(model_path):
        os.remove(model_path)
        print("Usunięto problematyczny plik modelu")
    
    print("System będzie używał tylko ulepszonego Haar Cascade")
    print("To zapewnia najlepszą kompatybilność i wydajność")
    return True

if __name__ == "__main__":
    print("Naprawianie modelu DNN - pobieranie prawidłowego pliku")
    print("=" * 60)
    
    # Próba pobrania prawidłowego modelu
    if download_correct_caffe_model():
        print("Model DNN naprawiony!")
    else:
        print("Nie udało się pobrać modelu, używam alternatywnego rozwiązania...")
        create_alternative_model()
    
    # Sprawdź końcowy stan
    model_path = "models/res10_300x300_ssd_iter_140000.caffemodel"
    if os.path.exists(model_path):
        file_size = os.path.getsize(model_path)
        print(f"Model: {os.path.abspath(model_path)}")
        print(f"Rozmiar: {file_size} bajtów ({file_size/1024/1024:.2f} MB)")
        
        if file_size > 5000000:
            print("Model ma odpowiedni rozmiar!")
        else:
            print("Model jest za mały, ale może działać jako fallback")
    else:
        print("Model nie został utworzony - system użyje tylko Haar Cascade")
