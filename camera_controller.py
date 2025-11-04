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
        self.last_frame = None
        
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
        
        # Import DEFAULT_SCHEDULE from models
        from models import DEFAULT_SCHEDULE
        
        self.settings = {
            # Weekly schedule (replaces camera_start_time and camera_end_time)
            'schedule': DEFAULT_SCHEDULE.copy(),
            'blur_faces': True,  # Kontroluje czy AnonymizerWorker działa (offline blur)
            'confidence_threshold': 0.2,
            'camera_index': self.camera_index,
            'camera_name': camera_name if camera_name else 'Camera 1',
            'sms_notifications': False,  # SMS notifications (Vonage + Cloudinary)
            'email_notifications': False,  # Email notifications (Yagmail + Cloudinary)
            'anonymization_percent': 50,
            # ROI as normalized [x1, y1, x2, y2] or None
            'roi_coordinates': None
        }
        self.detection_queue = Queue()
        
        # Uruchom AnonymizerWorker (offline anonimizacja + SMS notifications)
        # Przekaż referencję do settings, aby worker miał dostęp do 'sms_notifications'
        self.anonymizer_worker = AnonymizerWorker(self.detection_queue, self.settings)
        self.anonymizer_worker.start()
        print("✅ AnonymizerWorker uruchomiony w tle")
        # Manual stop guard – when True, scheduler must not auto-start the camera
        self.manual_stop_engaged = False
        
        # Initialize YOLO model
        try:
            print("Loading YOLO model...")
            self.model = YOLO('yolov8s.pt')
            print("YOLO model loaded successfully (yolov8s.pt - Small)")
            
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

        # Frame skipping configuration for performance optimization
        self.frame_counter = 0
        # Będziemy analizować co 10. klatkę (dla 30 FPS = 3 detekcje na sekundę)
        self.process_every_n_frame = 10
        print(f"Frame skipping enabled: processing every {self.process_every_n_frame} frames")

        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def _open_capture(self, index):
        """Open a cv2.VideoCapture STRICTLY for the selected index.

        Order:
        1) Default backend (MSMF on Windows) - preferred for virtual cams like Iriun
        2) DirectShow (CAP_DSHOW) as the only fallback for the SAME index
        No other indices or backends are attempted here.
        """
        # Try default backend first (MSMF on Windows)
        cap = cv2.VideoCapture(index)
        if cap is not None and cap.isOpened():
            return cap
        try:
            cap.release()
        except Exception:
            pass

        # Then try DirectShow for the SAME index
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

        return None

    def _get_camera_name_by_index(self, index):
        """Best-effort retrieval of camera device name for given index (Windows)."""
        try:
            cmd = (
                "powershell -Command \"Get-CimInstance Win32_PnPEntity | "
                "Where-Object { $_.PNPClass -eq 'Camera' } | "
                f"Select-Object -Index {index} | Select-Object -ExpandProperty Name\""
            )
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                name = result.stdout.strip()
                return name if name else None
        except Exception:
            pass
        return None

    def _capture_has_valid_frame(self, cap, warmup_reads=10, delay_s=0.1):
        """Read a few frames to ensure the capture delivers non-empty images.

        Some virtual cameras (e.g., Iriun) need a longer warm‑up before they
        start delivering non-empty frames. Increase warmup count and delay.
        """
        try:
            for _ in range(warmup_reads):
                ret, frame = cap.read()
                if ret and frame is not None and getattr(frame, 'size', 0) > 0:
                    return True
                time.sleep(delay_s)
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
        """Check if current time is within camera operation schedule (weekly)"""
        try:
            now = datetime.now()
            current_day = now.strftime('%A').lower()  # e.g., "monday"
            current_time = now.time()
            
            # Get schedule from settings
            schedule = self.settings.get('schedule', {})
            
            # Get today's schedule config
            today_schedule = schedule.get(current_day)
            
            # Check if enabled
            if not today_schedule or not today_schedule.get('enabled', False):
                print(f"\nSchedule check: {current_day.capitalize()} is disabled")
                return False
            
            # Parse start and end times
            start_time = datetime.strptime(today_schedule['start'], '%H:%M').time()
            end_time = datetime.strptime(today_schedule['end'], '%H:%M').time()
            
            print(f"\nChecking schedule:")
            print(f"Current day: {current_day.capitalize()}")
            print(f"Current time: {current_time}")
            print(f"Start time: {start_time}")
            print(f"End time: {end_time}")
            
            # Handle overnight logic (e.g., 22:00 - 06:00)
            if end_time < start_time:
                # Overnight schedule: current_time >= start_time OR current_time <= end_time
                is_within = (current_time >= start_time) or (current_time <= end_time)
            else:
                # Normal schedule: start_time <= current_time <= end_time
                is_within = start_time <= current_time <= end_time
            
            print(f"Within schedule: {is_within}")
            return is_within
        
        except Exception as e:
            print(f"Error checking schedule: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _check_schedule_start(self):
        """Thread to check when to start the camera based on schedule"""
        print("Starting schedule check thread...")
        while not self.is_running:
            within = self._is_within_schedule()
            if within:
                if not self.manual_stop_engaged:
                    print("Schedule start time reached, starting camera...")
                    self.start_camera()
                    break
            else:
                # Outside schedule – clear manual stop guard so next schedule can start
                self.manual_stop_engaged = False
            time.sleep(1)  # Check every second
        print("Schedule check thread ended")

    def start_camera(self):
        """Start the camera and detection process (STRICT selected index only)."""
        if self.is_running:
            print("Camera is already running")
            return
        
        try:
            # Reset manual stop flag on explicit manual start
            self.manual_stop_engaged = False
            # Resolve target by NAME first if provided (more stable than index mapping)
            desired_name = self.settings.get('camera_name')
            resolved_index = None
            if desired_name:
                try:
                    for cam in self.scan_available_cameras():
                        if desired_name.lower() in cam.get('name', '').lower():
                            resolved_index = int(cam['index'])
                            break
                except Exception:
                    resolved_index = None

            # Fall back to stored index if name not provided/found
            if resolved_index is None:
                resolved_index = int(self.settings.get('camera_index', self.camera_index))

            self.camera_index = resolved_index
            print(f"\nInitializing camera with STRICT index {self.camera_index} (desired='{desired_name}')...")

            self.camera = None
            last_error = None

            # Try default backend (MSMF) first, then DSHOW, for the SAME index
            for backend in ('default', 'dshow'):
                if backend == 'default':
                    cap = cv2.VideoCapture(self.camera_index)
                else:
                    cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

                if cap is not None and cap.isOpened() and self._capture_has_valid_frame(cap):
                    self.camera = cap
                    break

                # Release and record error
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
                last_error = f"Failed to open STRICT camera index {self.camera_index} using backend {backend}"

            # If still no camera, STOP and DO NOT attempt other indices
            if self.camera is None or not self.camera.isOpened():
                if last_error:
                    print(last_error)
                print("Strict mode: not falling back to any other camera index.")
                print("\n===============================================================")
                print(f"[BŁĄD KRYTYCZNY] Nie można otworzyć kamery (Index: {self.camera_index})!")
                print("PRZYCZYNA: Kamera jest prawdopodobnie UŻYWANA PRZEZ INNĄ APLIKACJĘ.")
                print("ROZWIĄZANIE: Zamknij WSZYSTKIE inne programy, które mogą używać tej kamery")
                print("(np. okno Ustawień Windows, klient Iriun, Zoom, OBS, Teams)")
                print("i zrestartuj serwer.")
                print("===============================================================\n")
                self.is_running = False
                self.camera = None
                return
            
            # Optional assertion: verify that the opened device corresponds to desired_name
            if desired_name:
                opened_name = self._get_camera_name_by_index(self.camera_index)
                if opened_name and desired_name.lower() not in opened_name.lower():
                    # Do NOT stop; align internal settings to actual opened device to prevent confusion
                    print(f"Device name mismatch: opened='{opened_name}', desired='{desired_name}'. Using opened device and updating settings.")
                    self.settings['camera_name'] = opened_name
            
            # Configure codec and resolution with validation
            try:
                # Many virtual cams prefer MJPG on Windows
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            except Exception:
                pass

            # Try preferred resolutions in order, accept first that yields valid frames
            preferred_res = [(1280, 720), (640, 480)]
            applied = None
            for w, h in preferred_res:
                try:
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                except Exception:
                    continue
                # short warm-up to validate
                if self._capture_has_valid_frame(self.camera, warmup_reads=5, delay_s=0.05):
                    applied = (w, h)
                    break

            # Read back properties
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            print(f"Camera initialized successfully: {width}x{height} @ {fps} FPS (requested={applied})")
            
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
        """Stop the camera and cleanup resources (GUI cleanup in main thread)."""
        print("\nStopping camera...")
        # Engage manual stop so scheduler won't auto-start within current schedule window
        self.manual_stop_engaged = True
        self.is_running = False
        
        # Ask the worker thread to finish and wait briefly (non-blocking join)
        if hasattr(self, 'camera_thread') and self.camera_thread is not None:
            try:
                self.camera_thread.join(timeout=1.0)
            except Exception:
                pass
        
        # Release capture if still open
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None
        
        # Destroy OpenCV windows from the caller (main) thread
        try:
            try:
                cv2.destroyWindow('Phone Detection')
            except Exception:
                cv2.destroyAllWindows()
            # Let GUI process window teardown
            # for _ in range(5):
            #     cv2.waitKey(1)
        except Exception:
            pass
        
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
        consecutive_failures = 0
        
        while self.is_running:
            try:
                # Check if we're still within schedule (weekly check)
                if not self._is_within_schedule():
                    print(f"Outside schedule, stopping camera (signal)")
                    self.is_running = False
                    break
                
                # Sprawdzenie, czy kamera jest otwarta
                if not self.camera or not self.camera.isOpened():
                    print("Camera is not opened, attempting to reopen...")
                    try:
                        if self.camera is not None:
                            self.camera.release()
                        self.camera = self._open_capture(self.camera_index)
                        if self.camera is None or not self.camera.isOpened():
                            print("Failed to reopen camera, waiting...")
                            time.sleep(1)
                            continue
                        # Reset properties after reopen
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        print("Camera reopened successfully")
                    except Exception as e:
                        print(f"Error reopening camera: {e}")
                        time.sleep(1)
                        continue
                
                ret, frame = self.camera.read()
                
                # KULODOODPORNY GUARD CLAUSE: Sprawdzenie MUSI być tutaj, BEZPOŚREDNIO po read()
                # Przed ustawieniem self.last_frame - zapobiega wyścigowi wątków
                # Sprawdzamy ret, None i rozmiar klatki (uszkodzone klatki z Iriun mogą mieć ret=True ale size=0)
                frame_is_invalid = False
                try:
                    # Sprawdź podstawowe warunki
                    if not ret or frame is None:
                        frame_is_invalid = True
                    else:
                        # Sprawdź czy klatka ma prawidłowy rozmiar (uszkodzone klatki mogą mieć size=0)
                        if not hasattr(frame, 'size') or frame.size == 0:
                            frame_is_invalid = True
                except Exception as e:
                    # Jeśli jakakolwiek walidacja się nie powiedzie, klatka jest nieprawidłowa
                    print(f"Błąd walidacji klatki (nieoczekiwany): {e}")
                    frame_is_invalid = True
                
                if frame_is_invalid:
                    print("Ostrzeżenie: Pusta lub uszkodzona klatka (ret=False, frame=None lub frame.size=0). Pomijanie.")
                    consecutive_failures += 1
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
                    # Daj kamerze chwilę na odzyskanie
                    time.sleep(0.1)
                    continue  # Przeskocz do następnej iteracji pętli - NIE ustawiamy last_frame!
                
                # Dopiero teraz klatka jest bezpieczna - ustawiamy last_frame PRZED wszystkimi innymi operacjami
                consecutive_failures = 0
                try:
                    self.last_frame = frame.copy()
                except Exception as e:
                    print(f"Error copying frame to last_frame: {e}")
                    time.sleep(0.1)
                    continue
                
                # Dodatkowa walidacja: sprawdź szczegółowe wymiary klatki (shape)
                # (Podstawowa walidacja size już została wykonana w guard clause powyżej)
                try:
                    # Validate frame dimensions (wysokość i szerokość)
                    h, w = frame.shape[:2]
                    if h == 0 or w == 0:
                        print("Błąd odczytu klatki (zerowe wymiary shape), pomijanie...")
                        time.sleep(0.1)
                        continue
                except (AttributeError, IndexError, TypeError) as e:
                    print(f"Błąd walidacji wymiarów klatki: {e}")
                    time.sleep(0.1)
                    continue
                
                # KLUCZOWE: NIE zamazuj twarzy w real-time!
                # Zamazywanie będzie robione OFFLINE przez AnonymizerWorker
                # Wyświetlamy ORYGINALNĄ klatkę bez zamazania
                try:
                    display_frame = frame.copy()
                except Exception as e:
                    print(f"Error copying frame for display: {e}")
                    time.sleep(0.1)
                    continue
                
                # Increment frame counter for skipping logic
                self.frame_counter += 1
                
                # --- KLUCZOWA LOGIKA POMIJANIA KLATEK ---
                # Jeśli to nie jest co 10. klatka, przeskocz do następnej iteracji
                # To pozwala na płynne działanie streamu, a detekcję wykonujemy tylko co 10. klatkę
                if self.frame_counter % self.process_every_n_frame != 0:
                    continue  # Pomiń detekcję dla tej klatki, ale stream działa normalnie
                
                # --- TEN KOD WYKONA SIĘ TERAZ TYLKO CO 10. KLATKĘ ---
                # (Zakładając 30 FPS = 3 detekcje na sekundę)
                if self.model is not None:
                    try:
                        # Validate display_frame exists and is valid before using
                        if display_frame is None or display_frame.size == 0:
                            continue
                            
                        results = self.model(frame, verbose=False)  # Używa ORYGINALNEJ klatki
                        # Read ROI once per batch
                        roi = self.settings.get('roi_coordinates')
                        frame_height, frame_width = frame.shape[:2]
                        
                        for result in results:
                            if result.boxes is None:
                                continue
                            boxes = result.boxes
                            for box in boxes:
                                # Validate box has valid xyxy data
                                if box.xyxy is None or len(box.xyxy) == 0 or len(box.xyxy[0]) < 4:
                                    continue
                                class_id = int(box.cls[0])
                                confidence = float(box.conf[0])
                                if class_id == self.phone_class_id and confidence >= self.settings['confidence_threshold']:
                                    # If ROI defined, filter by center point falling inside ROI (normalized)
                                    allow = True
                                    if roi and isinstance(roi, (list, tuple)) and len(roi) == 4:
                                        try:
                                            x1f, y1f, x2f, y2f = [float(v) for v in roi]
                                        except Exception:
                                            x1f, y1f, x2f, y2f = 0.0, 0.0, 1.0, 1.0
                                        bx1, by1, bx2, by2 = map(float, box.xyxy[0])
                                        center_x = (bx1 + bx2) / 2.0
                                        center_y = (by1 + by2) / 2.0
                                        norm_cx = center_x / max(1, frame_width)
                                        norm_cy = center_y / max(1, frame_height)
                                        allow = (x1f <= norm_cx <= x2f) and (y1f <= norm_cy <= y2f)
                                    if not allow:
                                        # Skip detection outside ROI
                                        continue

                                    print(f"📱 Phone detected with confidence: {confidence}")
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    
                                    # Validate and clamp coordinates to frame bounds
                                    x1 = max(0, min(x1, frame_width - 1))
                                    y1 = max(0, min(y1, frame_height - 1))
                                    x2 = max(0, min(x2, frame_width - 1))
                                    y2 = max(0, min(y2, frame_height - 1))
                                    
                                    # Ensure valid rectangle (x2 > x1, y2 > y1)
                                    if x2 > x1 and y2 > y1:
                                        try:
                                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                                            # Clamp text position to avoid negative y
                                            text_y = max(10, y1 - 10)
                                            cv2.putText(display_frame, f"Phone: {confidence:.2f}", (x1, text_y),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                        except Exception as draw_err:
                                            print(f"Error drawing phone box: {draw_err}")
                                    
                                    # ZAPISZ ORYGINALNĄ klatkę (bez zamazanych twarzy)
                                    try:
                                        self._handle_detection(frame.copy(), confidence)
                                    except Exception as copy_err:
                                        print(f"Error copying frame for detection: {copy_err}")
                                # Draw bounding box for person (tylko na wyświetlanej klatce)
                                if class_id == 0 and confidence >= 0.5:  # 0 is 'person' in COCO
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    
                                    # Validate and clamp coordinates to frame bounds
                                    x1 = max(0, min(x1, frame_width - 1))
                                    y1 = max(0, min(y1, frame_height - 1))
                                    x2 = max(0, min(x2, frame_width - 1))
                                    y2 = max(0, min(y2, frame_height - 1))
                                    
                                    # Ensure valid rectangle (x2 > x1, y2 > y1)
                                    if x2 > x1 and y2 > y1:
                                        try:
                                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                                            # Clamp text position to avoid negative y
                                            text_y = max(10, y1 - 10)
                                            cv2.putText(display_frame, f'Person: {confidence:.2f}', (x1, text_y),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                                        except Exception as draw_err:
                                            print(f"Error drawing person box: {draw_err}")
                    except Exception as e:
                        print(f"Error processing frame with YOLO: {e}")
                
                # Display disabled in server mode to avoid GUI blocking
                # cv2.imshow('Phone Detection', display_frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break
                
                # AnonymizerWorker przetwarza kolejkę automatycznie w tle
                
            except cv2.error as e:
                # Specjalna obsługa błędów OpenCV (np. cv::Mat::Mat)
                print(f"BŁĄD KRYTYCZNY OpenCV (cv::Mat::Mat?) w pętli kamery: {e}")
                print("Pominięcie klatki i kontynuacja...")
                time.sleep(0.5)  # Dłuższa pauza
                continue
            except Exception as e:
                # Łapanie wszystkich innych błędów
                print(f"Nieoczekiwany błąd w pętli kamery: {e}")
                time.sleep(1)
                continue
        
        # Cleanup only capture here (no GUI operations in worker thread)
        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
        except Exception:
            pass
        print("Camera loop ended")

    def get_current_frame_bytes(self):
        """Return the latest captured frame encoded as JPEG bytes, or None if unavailable."""
        try:
            if self.last_frame is None:
                return None
            # Encode to JPEG
            success, buffer = cv2.imencode('.jpg', self.last_frame)
            if not success:
                return None
            return buffer.tobytes()
        except Exception:
            return None

    def get_last_frame(self):
        """Return the latest raw frame (numpy array) or None if unavailable."""
        try:
            return self.last_frame
        except Exception:
            return None

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
    def _open_capture_static(index):
        """Static helper to open VideoCapture (same logic as instance method)"""
        # Try default backend first (MSMF on Windows)
        cap = cv2.VideoCapture(index)
        if cap is not None and cap.isOpened():
            return cap
        try:
            cap.release()
        except Exception:
            pass

        # Then try DirectShow for the SAME index
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

        return None

    @staticmethod
    def _capture_has_valid_frame_static(cap, warmup_reads=10, delay_s=0.1):
        """Static helper to check if capture delivers valid frames"""
        try:
            # Try to read at least one valid frame
            for attempt in range(warmup_reads):
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Check if frame has valid size
                    frame_size = getattr(frame, 'size', 0)
                    if frame_size > 0:
                        # Additional check: frame should have valid dimensions
                        try:
                            h, w = frame.shape[:2]
                            if h > 0 and w > 0:
                                return True
                        except (AttributeError, IndexError, TypeError):
                            pass
                if attempt < warmup_reads - 1:  # Don't sleep on last attempt
                    time.sleep(delay_s)
        except Exception as e:
            print(f"    ⚠️ Exception in _capture_has_valid_frame_static: {e}")
        return False

    @staticmethod
    def scan_available_cameras():
        """Scan and list all available camera devices and their indices"""
        available_cameras = []
        
        print("\n🔍 Starting camera scan...")
        
        # First, get all camera-like devices from Windows using PowerShell
        # Search for both Camera and Image device classes (Iriun may be in Image)
        all_camera_devices = []
        try:
            # Search for Camera class devices
            cmd = "powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | Select-Object Name, DeviceID, Manufacturer, Description, PNPClass | ConvertTo-Json\""
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                devices = json.loads(result.stdout)
                if not isinstance(devices, list):
                    devices = [devices]
                
                print(f"📋 Found {len(devices)} camera-like devices in Windows:")
                for device in devices:
                    device_name = device.get('Name', 'Unknown Device')
                    print(f"  - {device_name} (PNPClass: {device.get('PNPClass', 'Unknown')})")
                    all_camera_devices.append({
                        'name': device_name,
                        'pnpmclass': device.get('PNPClass', 'Unknown')
                    })
        except Exception as e:
            print(f"⚠️ Warning: Could not get camera list from Windows: {e}")
            import traceback
            traceback.print_exc()
        
        # Try to open cameras with indices 0-15 (increased range for virtual cameras)
        for index in range(16):
            cap = None
            # Use static helper method
            try:
                print(f"  🔍 Attempting to open camera index {index}...")
                cap = CameraController._open_capture_static(index)
                if cap is None:
                    print(f"    ❌ Camera {index} could not be opened (returned None)")
                    continue
                if not cap.isOpened():
                    print(f"    ❌ Camera {index} object created but isOpened() returned False")
                    try:
                        cap.release()
                    except:
                        pass
                    continue
                print(f"    ✅ Camera {index} opened successfully!")
            except Exception as e:
                print(f"    ⚠️ Exception opening camera {index}: {e}")
                import traceback
                traceback.print_exc()
                continue
            
            if cap is None or not cap.isOpened():
                continue
                
            if cap.isOpened():
                print(f"  📹 Testing camera index {index}...")
                
                # Get camera properties first (these should work even if frame reading is slow)
                try:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    # If width/height are 0, camera might not be initialized yet
                    if width == 0 or height == 0:
                        print(f"    ⚠️ Camera {index} opened but properties are 0x0, trying to read a frame...")
                        # Try to read a frame to initialize
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            width = test_frame.shape[1] if len(test_frame.shape) > 1 else 0
                            height = test_frame.shape[0] if len(test_frame.shape) > 0 else 0
                        else:
                            # Still try with default values - some cameras need to be actively used
                            width = 640
                            height = 480
                            print(f"    ⚠️ Using default resolution 640x480 for camera {index}")
                except Exception as e:
                    print(f"    ⚠️ Error getting camera properties: {e}, using defaults")
                    width = 640
                    height = 480
                    fps = 30
                
                # Try to verify frame reading (but don't be too strict - some cameras work even if this fails)
                has_valid_frame = False
                try:
                    has_valid_frame = CameraController._capture_has_valid_frame_static(cap, warmup_reads=3, delay_s=0.1)
                    if not has_valid_frame:
                        # Try one more time with longer delay for virtual cameras
                        time.sleep(0.3)
                        has_valid_frame = CameraController._capture_has_valid_frame_static(cap, warmup_reads=5, delay_s=0.15)
                except Exception as e:
                    print(f"    ⚠️ Frame validation error (non-critical): {e}")
                
                if not has_valid_frame:
                    print(f"    ⚠️ Camera {index} cannot deliver valid frames yet, but will include it anyway (may work when actively used)")
                    # Don't reject - include camera anyway, it might work when actively used
                
                print(f"    ✅ Camera {index} is working! ({width}x{height} @ {fps} FPS)")
                
                # Try to get camera name
                name = f"Camera {index}"
                
                # Try to match by querying Windows for this specific OpenCV index
                # Note: OpenCV index may not match Windows device index directly
                try:
                    # Approach 1: Try to get name using DirectShow backend property (if available)
                    try:
                        backend_name = cap.getBackendName()
                        print(f"    📷 Camera backend: {backend_name}")
                    except:
                        pass
                    
                    # Approach 2: If we have all_camera_devices list, try to match by index
                    # This is our primary method since we already have the list
                    if len(all_camera_devices) > 0:
                        if index < len(all_camera_devices):
                            name = all_camera_devices[index]['name']
                            print(f"    ✅ Using name from pre-scanned device list: {name}")
                        else:
                            # If index is beyond our list, try to find by searching all devices
                            # This handles cases where OpenCV index doesn't match Windows index order
                            print(f"    ⚠️ Camera index {index} beyond pre-scanned list, trying PowerShell query...")
                    
                    # Approach 3: Try PowerShell query for Camera class at this index (fallback)
                    if name == f"Camera {index}":  # If we still don't have a name
                        cmd = f"powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {{ $_.PNPClass -eq 'Camera' }} | Select-Object -Index {index} | Select-Object -ExpandProperty Name\""
                        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
                        if result.returncode == 0 and result.stdout.strip():
                            name = result.stdout.strip()
                            print(f"    ✅ Got name from Windows (Camera class): {name}")
                        else:
                            # Approach 4: Try Image class (for virtual cameras like Iriun)
                            cmd = f"powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {{ $_.PNPClass -eq 'Image' }} | Select-Object -Index {index} | Select-Object -ExpandProperty Name\""
                            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
                            if result.returncode == 0 and result.stdout.strip():
                                name = result.stdout.strip()
                                print(f"    ✅ Got name from Windows (Image class): {name}")
                    
                    # Approach 5: Search all_camera_devices for Iriun (in case index mismatch)
                    # This is especially useful for Iriun which might be on a different index
                    if "Iriun" not in name and "iriun" not in name.lower() and len(all_camera_devices) > 0:
                        for device in all_camera_devices:
                            if "Iriun" in device['name'] or "iriun" in device['name'].lower():
                                # Found Iriun in the list - if this is the only Iriun, assume it's this camera
                                name = device['name']
                                print(f"    ✅ Found Iriun in device list: {name}")
                                break
                                
                except Exception as e:
                    print(f"    ⚠️ Warning: Could not get name for camera index {index}: {e}")
                
                # Normalize Iriun Webcam name (case-insensitive)
                if "Iriun" in name or "iriun" in name.lower():
                    name = "Iriun Webcam"
                    print(f"    ✅ Normalized to: Iriun Webcam")
                
                # Try to get more detailed device information
                try:
                    cmd = f"powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {{ $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' }} | Select-Object -Index {index} | Select-Object -Property Name, DeviceID, Manufacturer, Description, PNPClass | ConvertTo-Json\""
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        device_info = json.loads(result.stdout)
                        print(f"    📷 Device info: {device_info}")
                except Exception as e:
                    pass  # Silently ignore errors in detailed info
                
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
        
        print(f"✅ Scan complete: Found {len(available_cameras)} available cameras")
        return available_cameras

    def find_camera_by_name(self, camera_name):
        """Find camera index by device name using Media Foundation API"""
        try:
            print(f"\n🔍 Searching for camera: {camera_name}")
            
            # First try to find by exact name match in both Camera and Image classes
            cmd = "powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | Select-Object Name, DeviceID, Manufacturer, Description, PNPClass | ConvertTo-Json\""
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Error getting camera list: {result.stderr}")
                # Fallback to scanning
                available_cameras = self.scan_available_cameras()
                for camera in available_cameras:
                    if camera_name.lower() in camera['name'].lower():
                        print(f"✅ Found camera '{camera_name}' at index {camera['index']} (via scan)")
                        return camera['index']
                return None
            
            # Parse the output to find matching camera
            devices = json.loads(result.stdout)
            if not isinstance(devices, list):
                devices = [devices]
            
            print(f"Found {len(devices)} camera-like devices in Windows")
            current_index = 0
            for device in devices:
                device_name = device.get('Name', '')
                print(f"  Checking device {current_index}: {device_name} (Class: {device.get('PNPClass', 'Unknown')})")
                
                # Case-insensitive search for Iriun
                search_name = camera_name.lower()
                if "iriun" in search_name or "iriun" in device_name.lower():
                    # Special handling for Iriun
                    if "iriun" in device_name.lower():
                        print(f"✅ Found Iriun Webcam at index {current_index}")
                        return current_index
                
                # General name matching
                if search_name in device_name.lower() or device_name.lower() in search_name:
                    print(f"✅ Found camera '{camera_name}' at index {current_index}")
                    return current_index
                
                # Increment index if this is a camera-like device
                if "Camera" in device_name or "Image" in device.get('PNPClass', ''):
                    current_index += 1
            
            # If not found by exact name, try scanning available cameras
            print("Camera not found by name, scanning available cameras...")
            available_cameras = self.scan_available_cameras()
            for camera in available_cameras:
                if camera_name.lower() in camera['name'].lower() or "iriun" in camera_name.lower() and "iriun" in camera['name'].lower():
                    print(f"✅ Found camera '{camera_name}' at index {camera['index']} (via scan)")
                    return camera['index']
            
            print(f"❌ Camera '{camera_name}' not found in device list")
            return None
            
        except Exception as e:
            print(f"Error finding camera by name: {e}")
            import traceback
            traceback.print_exc()
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
            self.model = YOLO('yolov8n.pt')
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
        
        # Inicjalizacja Email (yagmail) - przechowujemy tylko dane logowania
        print("📧 Inicjalizacja danych Email (Yagmail)...")
        try:
            # Pobierz dane logowania z zmiennych środowiskowych (.env)
            self.email_user = os.environ.get("GMAIL_USER")
            self.email_password = os.environ.get("GMAIL_APP_PASSWORD")
            self.email_recipient = os.environ.get("EMAIL_RECIPIENT")
            
            # Sprawdź czy wszystkie dane są dostępne
            if not all([self.email_user, self.email_password, self.email_recipient]):
                print("⚠️  Brak danych Email w zmiennych środowiskowych (.env)")
                print("   Wymagane: GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_RECIPIENT")
            else:
                # NIE tworzymy połączenia tutaj - będzie tworzone przy każdej wysyłce
                print("✅ Dane Email zainicjalizowane (połączenie będzie tworzone przy wysyłce).")
                print(f"   Wysyłka z: {self.email_user}")
                print(f"   Odbiorca: {self.email_recipient}")
        except Exception as e:
            print(f"❌ Błąd inicjalizacji danych Email: {e}")
    
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
        Tworzy nowe, świeże połączenie SMTP przy każdej wysyłce.
        
        Args:
            public_link: Link do pliku na Cloudinary
            filepath: Lokalna ścieżka do pliku (dla osadzenia i załącznika)
            confidence: Pewność detekcji
            location: Nazwa kamery/lokalizacji
            
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        # Sprawdź, czy dane email są dostępne
        if not all([self.email_user, self.email_password, self.email_recipient]):
            print("⚠️ Brak danych Email. Pomijam wysyłkę.")
            return False
        
        try:
            subject = f"Wykryto Telefon! ({location})"
            
            # --- Definicja Treści ---
            body_content = [
                "<b>Wykryto Telefon!</b>",
                "<hr>",
                f"<b>Lokalizacja:</b> {location}",
                 f"<b>Pewność detekcji:</b> {(confidence * 100):.1f}%",
                "<br>",
                "Zanonimizowany obraz (osadzony poniżej i w załączniku):",
                yagmail.inline(filepath)  # Osadzenie obrazu
            ]
            
            # Opcjonalnie: dodaj link do Cloudinary
            if public_link and public_link != "(Upload do Cloudinary nie powiódł się)":
                body_content.append(f'<br><a href="{public_link}">Link do obrazu w chmurze</a>')
            
            # --- Nowa Logika Połączenia ---
            # Tworzymy nowe, świeże połączenie przy każdej wysyłce
            with yagmail.SMTP(self.email_user, self.email_password) as yag_client:
                yag_client.send(
                    to=self.email_recipient,
                    subject=subject,
                    contents=body_content,
                    attachments=filepath
                )
            # Połączenie jest automatycznie zamykane po wyjściu z bloku "with"
            
            print(f"✅ Pomyślnie wysłano e-mail (z osadzonym obrazem) do {self.email_recipient}")
            return True
            
        except smtplib.SMTPDataError as e:
            # Specjalna obsługa "fałszywego" błędu 250 OK
            if e.smtp_code == 250:
                print(f"✅ E-mail prawdopodobnie wysłany (otrzymano kod 250 OK), ale wystąpił wyjątek: {e}")
                return True
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
                        
                        # Oblicz górną część ciała (konfigurowalny % od góry)
                        try:
                            percent = int(self.settings.get('anonymization_percent', 50))
                        except Exception:
                            percent = 50
                        ratio = max(0, min(100, percent)) / 100.0
                        upper_body_height = int(person_height * ratio)
                        
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
                            print(f"  ✓ Zanonimizowano osobę #{persons_found}: górne {int(ratio*100)}% ciała (conf: {confidence:.2f})")
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