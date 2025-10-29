import threading
import time
from datetime import datetime, time as dt_time
import cv2
from ultralytics import YOLO
import os
from flask import current_app
from models import db, Detection, User
from queue import Queue
import json
import subprocess
import re
import numpy as np
import textwrap
from dotenv import load_dotenv

# Load environment variables from .env file (Email, Cloudinary, Vonage)
load_dotenv()

# MediaPipe nie wspiera Python 3.13 - używamy OpenCV DNN jako alternatywy

# Imports for SMS notifications and Cloudinary
from vonage import Auth
from vonage_sms import Sms
from vonage_sms.requests import SmsMessage
from vonage_http_client import HttpClient
import cloudinary
import cloudinary.uploader
import cloudinary.api
import yagmail
import smtplib

class CameraController:
    def __init__(self, camera_index=0, camera_name=None):
        self.camera = None
        self.is_running = False
        self.thread = None
        
        # If camera_name is provided, try to find its index
        if camera_name:
            print(f"\nAttempting to find camera by name: {camera_name}")
            self.camera_index = self.find_camera_by_name(camera_name)
            if self.camera_index is None:
                print(f"Warning: Camera '{camera_name}' not found, using default index {camera_index}")
                self.camera_index = camera_index
        else:
            self.camera_index = camera_index
            
        print(f"Using camera index: {self.camera_index}")
        
        # Verify camera availability
        self._verify_camera()
        
        self.settings = {
            'camera_start_time': '00:00',
            'camera_end_time': '23:59',
            'blur_faces': True,  # Kontroluje czy AnonymizerWorker działa (offline blur)
            'confidence_threshold': 0.2,
            'camera_index': self.camera_index,
            'camera_name': camera_name if camera_name else 'Camera 1',
            'sms_notifications': False,  # SMS notifications (Vonage + Cloudinary)
            'email_notifications': False  # Email notifications (Yagmail + Cloudinary)
        }
        self.detection_queue = Queue()
        
        # Uruchom AnonymizerWorker (offline anonimizacja + SMS notifications)
        # Przekaż referencję do settings, aby worker miał dostęp do 'sms_notifications'
        self.anonymizer_worker = AnonymizerWorker(self.detection_queue, self.settings)
        self.anonymizer_worker.start()
        print("✅ AnonymizerWorker uruchomiony w tle")
        
        # Initialize YOLO model
        try:
            print("Loading YOLO model...")
            self.model = YOLO('yolov8m.pt')
            print("YOLO model loaded successfully")
            
            # Find phone class ID
            self.phone_class_id = None
            for class_id, class_name in self.model.names.items():
                if 'phone' in class_name.lower() or 'cell' in class_name.lower():
                    self.phone_class_id = class_id
                    print(f"Found phone class ID: {class_id}")
                    break
            
            if self.phone_class_id is None:
                self.phone_class_id = 67  # Default COCO class ID for cell phone
                print(f"Using default phone class ID: {self.phone_class_id}")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None

        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def _open_capture(self, index):
        """Open a cv2.VideoCapture with robust backend fallbacks.

        On Windows, prefer DirectShow to avoid MSMF grabFrame errors.
        Fallback order: CAP_DSHOW -> default (MSMF on Win) -> CAP_V4L2 (for WSL/Linux).
        """
        cap = None
        # Try DirectShow first (Windows)
        try:
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap is not None and cap.isOpened():
                return cap
            if cap is not None:
                cap.release()
        except Exception:
            try:
                cap.release()
            except Exception:
                pass

        # Try default backend (MSMF on Windows)
        cap = cv2.VideoCapture(index)
        if cap is not None and cap.isOpened():
            return cap
        try:
            cap.release()
        except Exception:
            pass

        # Try V4L2 (mainly Linux)
        try:
            cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
            if cap is not None and cap.isOpened():
                return cap
            if cap is not None:
                cap.release()
        except Exception:
            try:
                cap.release()
            except Exception:
                pass

        return None

    def _capture_has_valid_frame(self, cap, warmup_reads=5):
        """Read a few frames to ensure the capture delivers non-empty images."""
        try:
            for _ in range(warmup_reads):
                ret, frame = cap.read()
                if ret and frame is not None and getattr(frame, 'size', 0) > 0:
                    return True
                time.sleep(0.05)
        except Exception:
            pass
        return False

    def _verify_camera(self):
        """Verify if the selected camera is available and working"""
        print(f"\nVerifying camera with index {self.camera_index}...")
        try:
            cap = self._open_capture(self.camera_index)
            if not cap.isOpened():
                print(f"Error: Could not open camera with index {self.camera_index}")
                # Try to find alternative camera
                print("Scanning for available cameras...")
                available_cameras = self.scan_available_cameras()
                if available_cameras:
                    print("Available cameras:")
                    for cam in available_cameras:
                        print(f"- Index {cam['index']}: {cam['name']} ({cam['resolution']}, {cam['fps']} FPS)")
                    # Use the first available camera as fallback
                    self.camera_index = available_cameras[0]['index']
                    print(f"Falling back to camera index {self.camera_index}")
                else:
                    print("No cameras found!")
            else:
                # Get camera properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                print(f"Camera opened successfully: {width}x{height} @ {fps} FPS")
            cap.release()
        except Exception as e:
            print(f"Error verifying camera: {e}")

    def update_settings(self, settings):
        """Update camera settings and handle camera state"""
        print("\nUpdating camera settings...")
        print(f"Current settings: {self.settings}")
        print(f"New settings: {settings}")
        
        # Check if camera index changed
        if 'camera_index' in settings and settings['camera_index'] != self.settings['camera_index']:
            print(f"Camera index changed from {self.settings['camera_index']} to {settings['camera_index']}")
            self.camera_index = settings['camera_index']
            self._verify_camera()
        
        # Chroń camera_name przed nadpisaniem na None
        new_camera_name = settings.get('camera_name')
        
        if new_camera_name:
            # Jeśli jest nowa nazwa, użyj jej
            self.settings['camera_name'] = new_camera_name
        elif 'camera_name' not in self.settings:
            # Jeśli nie ma nowej i nie ma starej, ustaw domyślną
            self.settings['camera_name'] = 'Camera 1'
        # Jeśli nie ma nowej, ale jest stara, NIE RÓB NIC (zostaw starą)
        
        # Zaktualizuj resztę ustawień, pomijając camera_name (już obsłużone)
        settings_to_update = {k: v for k, v in settings.items() if k != 'camera_name'}
        self.settings.update(settings_to_update)
        
        print(f"Updated settings: {self.settings}")
        
        # Check schedule and update camera state
        is_within_schedule = self._is_within_schedule()
        print(f"Within schedule: {is_within_schedule}")
        print(f"Camera running: {self.is_running}")
        
        if is_within_schedule:
            if not self.is_running:
                print("Starting camera...")
                self.start_camera()
        else:
            if self.is_running:
                print("Stopping camera...")
                self.stop_camera()
            else:
                # Start a thread to check for schedule start
                if not hasattr(self, 'schedule_check_thread') or not self.schedule_check_thread.is_alive():
                    self.schedule_check_thread = threading.Thread(target=self._check_schedule_start)
                    self.schedule_check_thread.daemon = True
                    self.schedule_check_thread.start()
                    print("Started schedule check thread")

    def _is_within_schedule(self):
        """Check if current time is within camera operation schedule"""
        try:
            current_time = datetime.now().time()
            start_time = datetime.strptime(self.settings['camera_start_time'], '%H:%M').time()
            end_time = datetime.strptime(self.settings['camera_end_time'], '%H:%M').time()
            
            print(f"\nChecking schedule:")
            print(f"Current time: {current_time}")
            print(f"Start time: {start_time}")
            print(f"End time: {end_time}")
            
            # Convert times to minutes for easier comparison
            current_minutes = current_time.hour * 60 + current_time.minute
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            
            # Simple check: if current time is past end time, stop the camera
            if current_minutes > end_minutes:
                print("Current time is past end time, stopping camera")
                return False
            
            # Check if we're within the schedule
            is_within = start_minutes <= current_minutes <= end_minutes
            print(f"Within schedule: {is_within}")
            return is_within
        
        except Exception as e:
            print(f"Error checking schedule: {e}")
            return False

    def _check_schedule_start(self):
        """Thread to check when to start the camera based on schedule"""
        print("Starting schedule check thread...")
        while not self.is_running:
            if self._is_within_schedule():
                print("Schedule start time reached, starting camera...")
                self.start_camera()
                break
            time.sleep(1)  # Check every second
        print("Schedule check thread ended")

    def start_camera(self):
        """Start the camera and detection process"""
        if self.is_running:
            print("Camera is already running")
            return
        
        try:
            print(f"\nInitializing camera with index {self.camera_index}...")
            # Try multiple times with fallback backends and alternative indices
            attempts = 0
            last_error = None
            self.camera = None
            candidate_indices = [self.camera_index]
            try:
                alt = [c['index'] for c in self.scan_available_cameras() if c['index'] != self.camera_index]
                candidate_indices.extend(alt)
            except Exception:
                pass

            for idx in candidate_indices:
                attempts = 0
                while attempts < 3:
                    cap = self._open_capture(idx)
                    if cap is not None and cap.isOpened() and self._capture_has_valid_frame(cap):
                        self.camera_index = idx
                        self.camera = cap
                        attempts = 99
                        break
                    if cap is not None:
                        try:
                            cap.release()
                        except Exception:
                            pass
                    attempts += 1
                    last_error = f"Failed to open camera index {idx} on attempt {attempts}"
                    time.sleep(0.3)
                if self.camera is not None:
                    break

            if self.camera is None or not self.camera.isOpened():
                if last_error:
                    print(last_error)
                raise Exception(f"Failed to open camera with index {self.camera_index}")
            
            # Set higher resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Verify camera properties
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            print(f"Camera initialized successfully: {width}x{height} @ {fps} FPS")
            
            self.is_running = True
            print(f"Camera started successfully with index {self.camera_index}")
            
            # Start camera loop in a separate thread
            self.camera_thread = threading.Thread(target=self._camera_loop)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            print("Camera thread started")
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            self.is_running = False
            if self.camera is not None:
                self.camera.release()
                self.camera = None

    def stop_camera(self):
        """Stop the camera and cleanup resources"""
        print("\nStopping camera...")
        self.is_running = False
        
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        
        cv2.destroyAllWindows()
        print("Camera stopped")
        
        # Start schedule check thread for next schedule
        if not hasattr(self, 'schedule_check_thread') or not self.schedule_check_thread.is_alive():
            self.schedule_check_thread = threading.Thread(target=self._check_schedule_start)
            self.schedule_check_thread.daemon = True
            self.schedule_check_thread.start()
            print("Started schedule check thread for next schedule")

    def _handle_detection(self, frame, confidence):
        """
        Obsługuje wykrycie telefonu:
        1. Zapisuje ORYGINALNĄ klatkę (bez zamazanych twarzy!)
        2. Dodaje do kolejki dla AnonymizerWorker z ZAMROŻONĄ konfiguracją blur
        3. Worker zamaże twarze (jeśli włączone) i doda do DB
        """
        try:
            # Create detections directory if it doesn't exist
            os.makedirs('detections', exist_ok=True)
            
            # Save ORIGINAL image (without blurred faces!)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'phone_{timestamp}.jpg'
            filepath = os.path.join('detections', filename)
            
            success = cv2.imwrite(filepath, frame)
            if not success:
                raise Exception("Failed to save detection image")
            
            print(f"💾 Zapisano ORYGINALNĄ klatkę: {filepath}")
            
            # KLUCZOWE: Zamroź konfigurację blur w momencie detekcji
            # Ta wartość zostanie przekazana do workera razem z zadaniem
            should_blur = self.settings.get('blur_faces', True)
            
            # Dodaj do kolejki dla AnonymizerWorker
            # Worker zamaże twarze (jeśli should_blur=True) i zapisze do DB
            detection_data = {
                'filepath': filepath,  # Pełna ścieżka
                'confidence': confidence,
                'should_blur': should_blur  # Pipe the setting!
            }
            self.detection_queue.put(detection_data)
            blur_status = "z zamazaniem" if should_blur else "BEZ zamazania"
            print(f"📤 Dodano do kolejki anonimizacji {blur_status} (rozmiar: {self.detection_queue.qsize()})")
            
        except Exception as e:
            print(f"❌ Błąd zapisu detekcji: {e}")
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)

    # USUNIĘTE: process_detection_queue() - teraz robi to AnonymizerWorker asynchronicznie

    def _camera_loop(self):
        """Main camera loop for capturing and processing frames"""
        print("Starting camera loop...")
        frame_count = 0
        consecutive_failures = 0
        
        while self.is_running:
            try:
                # Get current time and end time
                current_time = datetime.now().time()
                end_time = datetime.strptime(self.settings['camera_end_time'], '%H:%M').time()
                
                # If current time is past end time, stop the camera
                if current_time > end_time:
                    print(f"End time reached: {end_time}, stopping camera")
                    self.stop_camera()
                    break
                
                ret, frame = self.camera.read()
                if (not ret) or (frame is None) or (getattr(frame, 'size', 0) == 0):
                    consecutive_failures += 1
                    print("Error reading frame")
                    # Try to recover by re-opening the camera after a few failures
                    if consecutive_failures >= 5:
                        print("Too many read failures, attempting to reopen camera...")
                        try:
                            if self.camera is not None:
                                self.camera.release()
                            self.camera = self._open_capture(self.camera_index)
                            if self.camera is None or not self.camera.isOpened() or not self._capture_has_valid_frame(self.camera):
                                print("Reopen failed; will retry shortly")
                                time.sleep(1)
                                continue
                            # Reset properties after reopen
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            consecutive_failures = 0
                            print("Camera reopened successfully")
                        except Exception as e:
                            print(f"Error while reopening camera: {e}")
                            time.sleep(1)
                            continue
                    else:
                        time.sleep(1)
                        continue
                else:
                    consecutive_failures = 0
                
                # KLUCZOWE: NIE zamazuj twarzy w real-time!
                # Zamazywanie będzie robione OFFLINE przez AnonymizerWorker
                # Wyświetlamy ORYGINALNĄ klatkę bez zamazania
                display_frame = frame.copy()
                
                # Run detection every 5 frames
                frame_count += 1
                if frame_count % 5 == 0 and self.model is not None:
                    try:
                        results = self.model(frame, verbose=False)  # Używa ORYGINALNEJ klatki
                        for result in results:
                            boxes = result.boxes
                            for box in boxes:
                                class_id = int(box.cls[0])
                                confidence = float(box.conf[0])
                                if class_id == self.phone_class_id and confidence >= self.settings['confidence_threshold']:
                                    print(f"📱 Phone detected with confidence: {confidence}")
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                                    cv2.putText(display_frame, f"Phone: {confidence:.2f}", (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                    # ZAPISZ ORYGINALNĄ klatkę (bez zamazanych twarzy)
                                    self._handle_detection(frame.copy(), confidence)
                                # Draw bounding box for person (tylko na wyświetlanej klatce)
                                if class_id == 0 and confidence >= 0.5:  # 0 is 'person' in COCO
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                                    cv2.putText(display_frame, f'Person: {confidence:.2f}', (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    except Exception as e:
                        print(f"Error processing frame with YOLO: {e}")
                
                # Display frame (ORYGINALNA klatka bez zamazanych twarzy)
                cv2.imshow('Phone Detection', display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # AnonymizerWorker przetwarza kolejkę automatycznie w tle
                
            except Exception as e:
                print(f"Error in camera loop: {e}")
                time.sleep(1)
        
        print("Camera loop ended")

    def __del__(self):
        """Czysty shutdown - zatrzymaj kamerę i workera"""
        self.stop_camera()
        
        # Zatrzymaj AnonymizerWorker
        if hasattr(self, 'anonymizer_worker'):
            print("🛑 Zatrzymywanie AnonymizerWorker...")
            self.detection_queue.put(None)  # Sygnał zakończenia
            self.anonymizer_worker.stop()
            self.anonymizer_worker.join(timeout=5)

    @staticmethod
    def scan_available_cameras():
        """Scan and list all available camera devices and their indices"""
        available_cameras = []
        
        # Try to open cameras with indices 0-9
        for index in range(10):
            cap = None
            controller_like = CameraController
            # Use the same robust opener
            try:
                cap = controller_like._open_capture(controller_like, index)  # call as unbound method
            except Exception:
                cap = cv2.VideoCapture(index)
            if cap is None:
                continue
            if cap.isOpened():
                # Ensure it can deliver a valid frame
                if not controller_like._capture_has_valid_frame(controller_like, cap):
                    try:
                        cap.release()
                    except Exception:
                        pass
                    continue
                # Get camera properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                # Try to get camera name using PowerShell
                try:
                    cmd = f"powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {{ $_.PNPClass -eq 'Camera' }} | Select-Object -Index {index} | Select-Object -ExpandProperty Name\""
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                    name = result.stdout.strip() if result.returncode == 0 else f"Camera {index}"
                    
                    # Additional check for Iriun Webcam
                    if "Iriun" in name:
                        print(f"Found Iriun Webcam at index {index}")
                        name = "Iriun Webcam"
                except:
                    name = f"Camera {index}"
                
                # Try to get more detailed device information
                try:
                    cmd = f"powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {{ $_.PNPClass -eq 'Camera' }} | Select-Object -Index {index} | Select-Object -Property Name, DeviceID, Manufacturer, Description | ConvertTo-Json\""
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                    if result.returncode == 0:
                        device_info = json.loads(result.stdout)
                        print(f"Device info for index {index}: {device_info}")
                except Exception as e:
                    print(f"Error getting device info for index {index}: {e}")
                
                available_cameras.append({
                    'index': index,
                    'name': name,
                    'resolution': f"{width}x{height}",
                    'fps': fps
                })
                
                cap.release()
            else:
                try:
                    cap.release()
                except Exception:
                    pass
        
        return available_cameras

    def find_camera_by_name(self, camera_name):
        """Find camera index by device name using Media Foundation API"""
        try:
            print(f"\nSearching for camera: {camera_name}")
            
            # First try to find by exact name match
            cmd = "powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' } | Select-Object Name, DeviceID, Manufacturer, Description | ConvertTo-Json\""
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                print(f"Error getting camera list: {result.stderr}")
                return None
            
            # Parse the output to find matching camera
            devices = json.loads(result.stdout)
            if not isinstance(devices, list):
                devices = [devices]
            
            current_index = 0
            for device in devices:
                print(f"Checking device: {device}")
                if camera_name.lower() in device['Name'].lower():
                    print(f"Found camera '{camera_name}' at index {current_index}")
                    return current_index
                if "Camera" in device['Name']:
                    current_index += 1
            
            # If not found by exact name, try scanning available cameras
            print("Camera not found by name, scanning available cameras...")
            available_cameras = self.scan_available_cameras()
            for camera in available_cameras:
                if camera_name.lower() in camera['name'].lower():
                    print(f"Found camera '{camera_name}' at index {camera['index']}")
                    return camera['index']
            
            print(f"Camera '{camera_name}' not found in device list")
            return None
            
        except Exception as e:
            print(f"Error finding camera by name: {e}")
            return None


class AnonymizerWorker(threading.Thread):
    """
    Worker thread do offline anonimizacji osób (górna część ciała).
    
    Używa YOLOv8 do wykrywania osób, zamazuje tylko głowę i ramiona.
    Działa asynchronicznie - nie blokuje głównej pętli kamery.
    Obsługuje również powiadomienia SMS przez Twilio i Google Drive.
    """
    
    def __init__(self, detection_queue, settings, blur_kernel_size=99, blur_sigma=30, upper_body_ratio=0.50):
        super().__init__(daemon=True)
        self.detection_queue = detection_queue
        self.settings = settings  # Referencja do settings z CameraController
        self.blur_kernel_size = blur_kernel_size
        self.blur_sigma = blur_sigma
        self.upper_body_ratio = upper_body_ratio  # Jaki procent górnej części bbox osoby zamazać
        self.is_running = True
        
        # Statystyki
        self.tasks_processed = 0
        self.persons_anonymized = 0
        
        # Inicjalizacja YOLOv8 dla detekcji osób
        print("📷 Inicjalizacja YOLOv8 dla detekcji osób (anonimizacja)...")
        
        try:
            # Załaduj model YOLOv8 (ten sam, który wykrywa telefony)
            self.model = YOLO('yolov8m.pt')
            print("✅ YOLOv8 zainicjalizowany dla anonimizacji")
            print(f"   Zamazywanie górnych {int(self.upper_body_ratio * 100)}% ciała osoby")
        except Exception as e:
            print(f"❌ Błąd ładowania YOLOv8: {e}")
            self.model = None
        
        # Inicjalizacja klienta Vonage (Nexmo) dla SMS
        print("📱 Inicjalizacja klienta Vonage...")
        try:
            self.vonage_api_key = os.getenv('VONAGE_API_KEY')
            self.vonage_api_secret = os.getenv('VONAGE_API_SECRET')
            self.vonage_from_number = os.getenv('VONAGE_FROM_NUMBER', 'PhoneDetection')
            self.vonage_to_number = os.getenv('VONAGE_TO_NUMBER')
            
            if all([self.vonage_api_key, self.vonage_api_secret, self.vonage_to_number]):
                # Vonage v4+ używa Auth → HttpClient → Sms
                vonage_auth = Auth(api_key=self.vonage_api_key, api_secret=self.vonage_api_secret)
                vonage_http_client = HttpClient(vonage_auth)
                self.vonage_sms = Sms(vonage_http_client)
                print("✅ Klient Vonage zainicjalizowany")
            else:
                self.vonage_sms = None
                print("⚠️  Brak danych Vonage w zmiennych środowiskowych")
        except Exception as e:
            print(f"❌ Błąd inicjalizacji Vonage: {e}")
            self.vonage_sms = None
        
        # Inicjalizacja Cloudinary
        print("☁️  Inicjalizacja Cloudinary...")
        try:
            cloudinary_cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
            cloudinary_api_key = os.getenv('CLOUDINARY_API_KEY')
            cloudinary_api_secret = os.getenv('CLOUDINARY_API_SECRET')
            
            if all([cloudinary_cloud_name, cloudinary_api_key, cloudinary_api_secret]):
                cloudinary.config(
                    cloud_name=cloudinary_cloud_name,
                    api_key=cloudinary_api_key,
                    api_secret=cloudinary_api_secret,
                    secure=True
                )
                self.cloudinary_enabled = True
                print("✅ Cloudinary zainicjalizowane")
                print(f"   Cloud Name: {cloudinary_cloud_name}")
            else:
                self.cloudinary_enabled = False
                print("⚠️  Brak danych Cloudinary w zmiennych środowiskowych")
        except Exception as e:
            print(f"❌ Błąd inicjalizacji Cloudinary: {e}")
            self.cloudinary_enabled = False
        
        # Inicjalizacja Email (yagmail)
        print("📧 Inicjalizacja Yagmail (Email)...")
        try:
            # Pobierz dane logowania z zmiennych środowiskowych (.env)
            self.email_user = os.environ.get("GMAIL_USER")
            self.email_password = os.environ.get("GMAIL_APP_PASSWORD")
            self.email_recipient = os.environ.get("EMAIL_RECIPIENT")
            
            # Sprawdź czy wszystkie dane są dostępne
            if not all([self.email_user, self.email_password, self.email_recipient]):
                print("⚠️  Brak danych Email w zmiennych środowiskowych (.env)")
                print("   Wymagane: GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_RECIPIENT")
                self.yag_client = None
            else:
                # Inicjalizuj klienta Yagmail
                self.yag_client = yagmail.SMTP(self.email_user, self.email_password)
                print("✅ Klient Yagmail (Email) zainicjalizowany.")
                print(f"   Wysyłka z: {self.email_user}")
                print(f"   Odbiorca: {self.email_recipient}")
        except Exception as e:
            print(f"❌ Błąd inicjalizacji Yagmail: {e}")
            self.yag_client = None
    
    def run(self):
        """Główna pętla workera - przetwarza zadania z kolejki"""
        print("🔄 AnonymizerWorker uruchomiony")
        
        while self.is_running:
            try:
                # Pobierz zadanie z kolejki (blokujące z timeout)
                try:
                    task_data = self.detection_queue.get(timeout=1)
                except:
                    continue  # Timeout - sprawdź is_running i próbuj ponownie
                
                if task_data is None:
                    # Sygnał zakończenia
                    self.detection_queue.task_done()
                    break
                
                filepath = task_data.get('filepath')
                confidence = task_data.get('confidence', 0.0)
                # KLUCZOWE: Odczytaj flagę should_blur (domyślnie True dla bezpieczeństwa)
                should_blur = task_data.get('should_blur', True)
                
                print(f"🔄 Przetwarzanie: {filepath} (blur: {should_blur})")
                
                # Wykonaj anonimizację TYLKO jeśli should_blur = True
                if should_blur:
                    success = self._anonymize_faces(filepath)
                    
                    if success:
                        print(f"✅ Zanonimizowano: {filepath}")
                        self.tasks_processed += 1
                    else:
                        print(f"❌ Błąd anonimizacji: {filepath}")
                else:
                    # Blur wyłączony - pomiń anonimizację całkowicie
                    print(f"⏭️  Pomijam anonimizację (blur wyłączony): {filepath}")
                    self.tasks_processed += 1
                
                # ZAWSZE zapisz do bazy danych (niezależnie od blur)
                # Jeśli blur=False, zapisujemy oryginalny plik
                # Jeśli blur=True, zapisujemy zanonimizowany plik
                self._save_to_database(filepath, confidence)
                
                # KLUCZOWY WARUNEK: Sprawdź czy KTÓRYKOLWIEK rodzaj powiadomień jest włączony
                sms_enabled = self.settings.get('sms_notifications', False)
                email_enabled = self.settings.get('email_notifications', False)
                
                if sms_enabled or email_enabled:
                    notification_types = []
                    if sms_enabled:
                        notification_types.append("SMS")
                    if email_enabled:
                        notification_types.append("Email")
                    
                    print(f"📲 Powiadomienia włączone ({', '.join(notification_types)}) - uruchamiam wysyłkę w tle")
                    # Uruchom w osobnym wątku aby nie blokować pętli run
                    notification_thread = threading.Thread(
                        target=self._handle_cloud_notification,
                        args=(filepath, confidence),
                        daemon=True
                    )
                    notification_thread.start()
                else:
                    print(f"📵 Powiadomienia (Email/SMS) wyłączone - pomijam wysyłkę")
                
                self.detection_queue.task_done()
                
            except Exception as e:
                print(f"❌ Błąd w AnonymizerWorker: {e}")
                try:
                    self.detection_queue.task_done()
                except:
                    pass
        
        print(f"🛑 AnonymizerWorker zakończył (zadania: {self.tasks_processed}, osoby: {self.persons_anonymized})")
    
    def _upload_to_cloudinary(self, filepath):
        """
        Wysyła plik na Cloudinary i zwraca publiczny link.
        
        Args:
            filepath: Ścieżka do pliku
            
        Returns:
            secure_url (str) lub None jeśli błąd
        """
        try:
            if not self.cloudinary_enabled:
                print("❌ Cloudinary nie jest zainicjalizowane")
                return None
            
            filename = os.path.basename(filepath)
            
            print(f"☁️  Wysyłanie {filename} na Cloudinary...")
            
            # Upload pliku na Cloudinary
            response = cloudinary.uploader.upload(
                filepath,
                folder="phone_detections",  # Folder w Cloudinary
                public_id=os.path.splitext(filename)[0],  # Nazwa bez rozszerzenia
                resource_type="image",
                overwrite=True
            )
            
            # Pobierz secure URL (HTTPS)
            secure_url = response.get('secure_url')
            public_id = response.get('public_id')
            
            print(f"✅ Plik wysłany na Cloudinary: {public_id}")
            print(f"🔗 Link (publiczny): {secure_url}")
            
            return secure_url
            
        except Exception as e:
            print(f"❌ Błąd wysyłania na Cloudinary: {e}")
            return None
    
    def _send_sms_notification(self, public_link, confidence):
        """
        Wysyła powiadomienie SMS przez Vonage (Nexmo).
        
        Args:
            public_link: Link do pliku na Google Drive (lub None jeśli upload się nie powiódł)
            confidence: Pewność detekcji
            
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            if self.vonage_sms is None:
                print("❌ Klient Vonage nie jest zainicjalizowany")
                return False
            
            # Przygotuj treść wiadomości
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if public_link:
                message_body = (
                    f"Phone Detection Alert!\n"
                    f"Time: {timestamp}\n"
                    f"Location: Camera 1\n"
                    f"Confidence: {confidence:.2%}\n"
                    f"Image: {public_link}\n"
                    f"---"  # Padding dla Vonage demo - chroni link przed [FREE SMS DEMO...]
                )
            else:
                # Wyślij SMS bez linku jeśli Cloudinary zawiódł
                message_body = (
                    f"Phone Detection Alert!\n"
                    f"Time: {timestamp}\n"
                    f"Location: Camera 1\n"
                    f"Confidence: {confidence:.2%}\n"
                    f"(Image upload failed)\n"
                    f"---"  # Padding dla Vonage demo
                )
            
            # Vonage wymaga numeru bez '+' i jako string
            to_number = self.vonage_to_number.replace('+', '')
            
            print(f"📱 Wysyłanie SMS na +{to_number}...")
            
            # Stwórz obiekt SmsMessage (Vonage v4 API)
            sms_message = SmsMessage(
                to=to_number,
                from_=self.vonage_from_number,
                text=message_body
            )
            
            # Wyślij SMS przez Vonage v4
            response = self.vonage_sms.send(sms_message)
            
            # Sprawdź odpowiedź
            if response and hasattr(response, 'messages'):
                if response.messages[0].status == '0':
                    message_id = response.messages[0].message_id
                    print(f"✅ SMS wysłany: {message_id}")
                    return True
                else:
                    error = getattr(response.messages[0], 'error_text', 'Unknown error')
                    print(f"❌ Błąd Vonage: {error}")
                    return False
            else:
                print(f"❌ Nieprawidłowa odpowiedź Vonage: {response}")
                return False
            
        except Exception as e:
            print(f"❌ Błąd wysyłania SMS: {e}")
            return False
    
    def _send_email_notification(self, public_link, filepath, confidence, location):
        """
        Wysyła powiadomienie e-mail przez Yagmail z osadzonym obrazem.
        
        Args:
            public_link: Link do pliku na Cloudinary
            filepath: Lokalna ścieżka do pliku (dla osadzenia i załącznika)
            confidence: Pewność detekcji
            location: Nazwa kamery/lokalizacji
            
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        if not self.yag_client:
            print("⚠️ Klient Yagmail nie jest skonfigurowany. Pomijam e-mail.")
            return False
        
        # Sprawdź, czy adresat e-mail jest ustawiony (zapobiega błędowi RCPT first)
        if not self.email_recipient:
            print("⚠️ Brak adresata e-mail. Pomijam wysyłkę.")
            return False
        
        try:
            subject = f"Wykryto Telefon! ({location})"
            
            # --- Tworzenie treści z osadzonym obrazem ---
            # yagmail.inline(filepath) stworzy tag <img> z obrazem osadzonym w e-mailu
            
            # Użyjemy listy stringów dla yagmail - automatycznie doda formatowanie
            body_content = [
                "<b>Wykryto Telefon!</b>",
                "<hr>",
                f"<b>Lokalizacja:</b> {location}",
                f"<b>Pewność detekcji:</b> {confidence:.1f}%",
                "<br>",
                "Zanonimizowany obraz (osadzony poniżej i w załączniku):",
                yagmail.inline(filepath)  # <-- Kluczowy element do osadzenia obrazu
            ]
            
            # Opcjonalnie: dodaj link do Cloudinary
            if public_link and public_link != "(Upload do Cloudinary nie powiódł się)":
                body_content.append(f'<br><a href="{public_link}">Link do obrazu w chmurze</a>')
            
            # --- Koniec treści ---
            
            # Wysyłamy listę stringów - yagmail sam połączy je w HTML
            self.yag_client.send(
                to=self.email_recipient,
                subject=subject,
                contents=body_content,  # Wysyłamy listę
                attachments=filepath  # Nadal wysyłamy jako oddzielny załącznik
            )
            # Log sukcesu
            print(f"✅ Pomyślnie wysłano e-mail (z osadzonym obrazem) do {self.email_recipient}")
            return True
            
        except smtplib.SMTPDataError as e:
            # Specjalna obsługa "fałszywego" błędu 250 OK
            if e.smtp_code == 250:
                print(f"✅ E-mail prawdopodobnie wysłany (otrzymano kod 250 OK), ale wystąpił wyjątek: {e}")
                return True  # Traktuj jako sukces
            else:
                print(f"❌ Błąd krytyczny wysyłania e-mail (Yagmail SMTPDataError): {e}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:
            # Inne błędy
            print(f"❌ Błąd krytyczny wysyłania e-mail (Yagmail): {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_cloud_notification(self, filepath, confidence):
        """
        Orkiestrator powiadomień - upload na Cloudinary i wysyłka SMS/Email.
        
        Args:
            filepath: Ścieżka do pliku
            confidence: Pewność detekcji
        """
        try:
            print(f"🚀 Rozpoczynam wysyłkę powiadomienia dla: {filepath}")
            
            # 1. Próbuj upload na Cloudinary (opcjonalnie)
            public_link = self._upload_to_cloudinary(filepath)
            
            if public_link:
                print(f"✅ Plik wysłany na Cloudinary")
                
                # 2. Wyślij SMS jeśli włączony
                if self.settings.get('sms_notifications', False):
                    print("📱 SMS notifications włączone - wysyłanie...")
                    success = self._send_sms_notification(public_link, confidence)
                    if success:
                        print(f"✅ SMS wysłany z linkiem do zdjęcia!")
                    else:
                        print(f"❌ Nie udało się wysłać SMS")
                else:
                    print("📵 SMS notifications wyłączone - pomijam SMS")
                
                # 3. Wyślij Email jeśli włączony
                if self.settings.get('email_notifications', False):
                    print("📧 Email notifications włączone - wysyłanie...")
                    location = self.settings.get('camera_name', 'Camera 1')
                    self._send_email_notification(
                        public_link,
                        filepath,
                        confidence,
                        location
                    )
                else:
                    print("📭 Email notifications wyłączone - pomijam e-mail")
            else:
                # Cloudinary zawiodło - wyślij powiadomienia bez linku
                print("⚠️  Nie udało się wysłać na Cloudinary")
                
                if self.settings.get('sms_notifications', False):
                    print("   ale wyślę SMS bez linku")
                    success = self._send_sms_notification(None, confidence)
                    if success:
                        print(f"✅ SMS wysłany (bez linku)")
                    else:
                        print(f"❌ Nie udało się wysłać SMS")
                
                # Email z informacją o braku linku
                if self.settings.get('email_notifications', False):
                    print("📧 Email notifications włączone - wysyłanie (bez linku Cloudinary)...")
                    location = self.settings.get('camera_name', 'Camera 1')
                    # Wyślij z tekstem zamiast linku
                    self._send_email_notification(
                        "(Upload do Cloudinary nie powiódł się)",
                        filepath,
                        confidence,
                        location
                    )
                
        except Exception as e:
            print(f"❌ Błąd w _handle_cloud_notification: {e}")
    
    def _anonymize_faces(self, image_path):
        """
        Anonimizuje górną część ciała osób (głowa + ramiona) używając YOLOv8.
        
        Strategia:
        - Wykrywa osoby (klasa 0) za pomocą YOLOv8
        - Dla każdej osoby zamazuje tylko górną część bbox (30-40%)
        - Jeśli brak osób - zapisuje oryginał bez zmian
        
        Args:
            image_path: Ścieżka do obrazu
            
        Returns:
            True jeśli sukces
        """
        try:
            # Sprawdź czy model jest dostępny
            if self.model is None:
                print("⚠️  Model YOLOv8 niedostępny, zapisuję oryginał")
                return True  # Brak modelu = zapisz oryginał
            
            # Wczytaj obraz
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Nie można wczytać: {image_path}")
                return False
            
            # Pobierz wymiary obrazu
            img_h, img_w = image.shape[:2]
            
            # Wykryj osoby za pomocą YOLOv8
            results = self.model(image, verbose=False)
            
            persons_found = 0
            
            # Przetwórz wyniki
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    # Szukamy tylko klasy 'person' (0 w COCO)
                    if class_id == 0 and confidence >= 0.5:
                        persons_found += 1
                        
                        # Pobierz pełny bounding box osoby
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Oblicz wysokość bbox osoby
                        person_height = y2 - y1
                        
                        # Oblicz górną część ciała (upper_body_ratio % wysokości od góry)
                        upper_body_height = int(person_height * self.upper_body_ratio)
                        
                        # Definiuj ROI dla górnej części ciała
                        # X: cały bbox osoby (lewa-prawa)
                        # Y: tylko górna część
                        roi_x1 = x1
                        roi_y1 = y1
                        roi_x2 = x2
                        roi_y2 = y1 + upper_body_height
                        
                        # Walidacja granic obrazu
                        roi_x1 = max(0, roi_x1)
                        roi_y1 = max(0, roi_y1)
                        roi_x2 = min(img_w, roi_x2)
                        roi_y2 = min(img_h, roi_y2)
                        
                        # Sprawdź czy ROI ma sens
                        if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
                            print(f"⚠️  Nieprawidłowy ROI osoby: ({roi_x1},{roi_y1})-({roi_x2},{roi_y2}), pomijam")
                            continue
                        
                        # Wytnij ROI górnej części ciała
                        upper_body_roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
                        
                        # Zastosuj silny Gaussian blur
                        if upper_body_roi.size > 0:
                            blurred_upper_body = cv2.GaussianBlur(
                                upper_body_roi,
                                (self.blur_kernel_size, self.blur_kernel_size),
                                self.blur_sigma
                            )
                            image[roi_y1:roi_y2, roi_x1:roi_x2] = blurred_upper_body
                            self.persons_anonymized += 1
                            print(f"  ✓ Zanonimizowano osobę #{persons_found}: górne {upper_body_height}px z {person_height}px (conf: {confidence:.2f})")
                        else:
                            print(f"⚠️  Pusty ROI dla osoby, pomijam")
            
            if persons_found == 0:
                print(f"ℹ️  Brak osób na obrazie - zapisuję oryginał bez zmian")
            else:
                print(f"👤 Zanonimizowano {persons_found} osób (tylko górna część ciała)")
            
            # Nadpisz oryginalny plik (zanonimizowanym lub oryginalnym jeśli brak osób)
            success = cv2.imwrite(image_path, image)
            
            if not success:
                print(f"❌ Nie udało się zapisać: {image_path}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd anonimizacji: {e}")
            return False
    
    def _save_to_database(self, filepath, confidence):
        """Zapisuje wykrycie do bazy danych (tylko zanonimizowany obraz)"""
        try:
            from app import app
            filename = os.path.basename(filepath)
            
            with app.app_context():
                admin_user = User.query.filter_by(username='admin').first()
                if admin_user:
                    detection = Detection(
                        location='Camera 1',
                        confidence=confidence,
                        image_path=filename,
                        status='Pending',
                        user_id=admin_user.id
                    )
                    db.session.add(detection)
                    db.session.commit()
                    print(f"💾 Zapisano do DB: {filename}")
                else:
                    print("❌ Brak użytkownika admin")
        except Exception as e:
            print(f"❌ Błąd zapisu do DB: {e}")
    
    def stop(self):
        """Zatrzymuje workera"""
        self.is_running = False


# Przykład użycia
if __name__ == "__main__":
    cameras = CameraController.scan_available_cameras()
    for camera in cameras:
        print(f"Camera {camera['index']}: {camera['name']} ({camera['resolution']}, {camera['fps']} FPS)")