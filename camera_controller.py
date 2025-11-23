import threading
import time
from datetime import datetime, timedelta, time as dt_time
import cv2
from ultralytics import YOLO
import os
from models import db, Detection, User
from queue import Queue
import json
import subprocess
import re
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file (Email, Cloudinary, Vonage)
load_dotenv()



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
    def __init__(self, camera_index=0, camera_name=None, 
                 yolo_model_detection=None, yolo_model_anonymization=None,
                 vonage_sms=None, cloudinary_enabled=False,
                 email_user=None, email_password=None, email_recipient=None,
                 available_cameras_list=None):
        self.camera = None
        self.is_running = False
        self.thread = None
        self.last_frame = None
        self.frame_lock = threading.Lock()  # Lock dla bezpiecznego dostępu do last_frame
        
        # If camera_name is provided, try to find its index
        if camera_name:
            print(f"\nAttempting to find camera by name: {camera_name}")
            self.camera_index = self.find_camera_by_name(camera_name)
            if self.camera_index is None:
                print(f"Warning: Camera '{camera_name}' not found, using default index {camera_index}")
                self.camera_index = camera_index
        else:
            self.camera_index = camera_index
        
        # Indeks kamery, który został wybrany w Ustawieniach (przypisany do monitorowania)
        self.assigned_camera_index = self.camera_index
            
        print(f"Using camera index: {self.camera_index}")
        print(f"Assigned camera index: {self.assigned_camera_index}")
            
        # Verify camera availability
        self._verify_camera()
        
        # Import DEFAULT_SCHEDULE from models
        from models import DEFAULT_SCHEDULE
        
        # Przechowuj ustawienia jako bezpośrednie zmienne członkowskie (bezpośrednie źródło prawdy)
        self.schedule = DEFAULT_SCHEDULE.copy()  # Harmonogram tygodniowy
        self.assigned_camera_index = self.camera_index
        self.camera_name = camera_name if camera_name else 'Camera 1'
        self.blur_faces = True  # Kontroluje czy AnonymizerWorker działa (offline blur)
        self.confidence_threshold = 0.2
        self.sms_notifications = False  # SMS notifications (Vonage + Cloudinary)
        self.email_notifications = False  # Email notifications (Yagmail + Cloudinary)
        # Wewnętrzne zmienne do przechowywania stanu powiadomień (aktualizowalne w locie)
        self.email_enabled = False
        self.sms_enabled = False
        self.anonymization_percent = 50
        self.roi_coordinates = None  # ROI as normalized [x1, y1, x2, y2] or None
        
        # ROI zones for per-zone throttling
        self.roi_zones = []  # Lista słowników, np. [{'name': 'ławka 1', 'coords': {'x': 0.1, 'y': 0.1, 'w': 0.2, 'h': 0.2}}]
        
        # Zachowaj słownik settings dla kompatybilności z AnonymizerWorker (który używa self.settings)
        self.settings = {
            'schedule': self.schedule,
            'blur_faces': self.blur_faces,
            'confidence_threshold': self.confidence_threshold,
            'camera_index': self.assigned_camera_index,
            'camera_name': self.camera_name,
            'sms_notifications': self.sms_notifications,
            'email_notifications': self.email_notifications,
            'anonymization_percent': self.anonymization_percent,
            'roi_coordinates': self.roi_coordinates
        }
        
        self.detection_queue = Queue()
        
        # Per-zone throttling infrastructure
        self.alert_mute_until = {}  # Słownik: {'nazwa_strefy': datetime_obiekt}
        self.mute_duration = timedelta(minutes=5)
        self.alert_lock = threading.Lock()  # Zabezpieczenie słownika
        
        # Uruchom AnonymizerWorker (offline anonimizacja + SMS notifications)
        # Przekaż referencję do settings oraz globalne zasoby
        self.anonymizer_worker = AnonymizerWorker(
            detection_queue=self.detection_queue,
            settings=self.settings,
            yolo_model=yolo_model_anonymization,
            vonage_sms=vonage_sms,
            cloudinary_enabled=cloudinary_enabled,
            email_user=email_user,
            email_password=email_password,
            email_recipient=email_recipient
        )
        self.anonymizer_worker.start()
        print("✅ AnonymizerWorker uruchomiony w tle")
        # Manual stop guard – when True, scheduler must not auto-start the camera
        # PRZY STARCIE SERWERA: Zawsze blokuj auto-start (kamera startuje wyłączona)
        self.manual_stop_engaged = True  # Domyślnie zablokowane - użytkownik musi ręcznie włączyć
        self.was_within_schedule = False  # NOWA ZMIENNA do śledzenia stanu z poprzedniej pętli
        self.camera_was_manually_started = False  # Flaga: czy użytkownik ręcznie włączył kamerę w tej sesji
        
        # Użyj przekazanego modelu YOLO (lub None jeśli nie przekazano)
        self.model = yolo_model_detection
        if self.model is not None:
            print("✅ Używam przekazanego modelu YOLO (detection)")
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
        else:
            print("⚠️  Brak modelu YOLO (detection) - detekcja telefonów będzie wyłączona")
            self.phone_class_id = 67

        # Frame skipping configuration for performance optimization
        self.frame_counter = 0
        # Zmniejszono z 5 do 3 dla częstszej detekcji (dla 30 FPS = 10 detekcji na sekundę)
        # To poprawia wykrywanie szybko poruszających się telefonów
        self.process_every_n_frame = 3
        print(f"Frame skipping enabled: processing every {self.process_every_n_frame} frames")
        
        # Użyj przekazanej listy kamer (lub pusta lista jeśli nie przekazano)
        if available_cameras_list is not None:
            self.available_cameras_list = available_cameras_list
            print(f"INFO: Używam przekazanej listy kamer: {len(self.available_cameras_list)} kamer.")
        else:
            self.available_cameras_list = []
            print("INFO: Brak przekazanej listy kamer - używam pustej listy.")
        
        # Uruchom główną pętlę kontrolera (która zarządza harmonogramem)
        self.camera_thread = threading.Thread(target=self._camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        print("INFO: Główna pętla kontrolera (_camera_loop) uruchomiona")

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
                available_cameras = self.get_available_cameras()
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

    def update_settings(self, settings_model):
        """
        Przyjmuje obiekt modelu 'Settings' z app.py i aktualizuje
        wewnętrzny stan kontrolera. TO JEST JEDYNE ŹRÓDŁO PRAWDY.
        """
        print("INFO: Kontroler kamery otrzymał nowe ustawienia.")
        
        # Aktualizuj harmonogram
        if hasattr(settings_model, 'schedule') and settings_model.schedule:
            self.schedule = settings_model.schedule.copy()
            print(f"INFO: Zaktualizowano harmonogram: {list(self.schedule.keys())}")
        
        # Aktualizuj ROI zones
        if hasattr(settings_model, 'roi_zones') and settings_model.roi_zones is not None:
            self.roi_zones = settings_model.roi_zones.copy() if isinstance(settings_model.roi_zones, list) else []
            print(f"INFO: Zaktualizowano ROI zones: {len(self.roi_zones)} stref")
        
        # Aktualizuj camera_index (jeśli jest w modelu)
        if hasattr(settings_model, 'camera_index') and settings_model.camera_index is not None:
            self.assigned_camera_index = int(settings_model.camera_index)
            print(f"INFO: Zaktualizowano przypisany indeks kamery: {self.assigned_camera_index}")
        
        # Aktualizuj blur_faces (KRYTYCZNE!)
        if hasattr(settings_model, 'blur_faces'):
            self.blur_faces = bool(settings_model.blur_faces)
            print(f"INFO: Zaktualizowano blur_faces: {self.blur_faces}")
        
        # Aktualizuj confidence_threshold
        if hasattr(settings_model, 'confidence_threshold'):
            self.confidence_threshold = float(settings_model.confidence_threshold)
            print(f"INFO: Zaktualizowano confidence_threshold: {self.confidence_threshold}")
        
        email_value = None
        sms_value = None
        
        if hasattr(settings_model, 'email_notifications'):
            email_value = settings_model.email_notifications
        elif hasattr(settings_model, 'email_enabled'):
            email_value = settings_model.email_enabled
        elif isinstance(settings_model, dict) and 'email_notifications' in settings_model:
            email_value = settings_model['email_notifications']
        
        if email_value is not None:
            self.email_enabled = bool(email_value)
            self.email_notifications = bool(email_value)
        
        if hasattr(settings_model, 'sms_notifications'):
            sms_value = settings_model.sms_notifications
        elif hasattr(settings_model, 'sms_enabled'):
            sms_value = settings_model.sms_enabled
        elif isinstance(settings_model, dict) and 'sms_notifications' in settings_model:
            sms_value = settings_model['sms_notifications']
        
        if sms_value is not None:
            self.sms_enabled = bool(sms_value)
            self.sms_notifications = bool(sms_value)
        
        # Zaktualizuj słownik settings dla kompatybilności z AnonymizerWorker
        self.settings['email_notifications'] = self.email_enabled
        self.settings['sms_notifications'] = self.sms_enabled
        self.settings['blur_faces'] = self.blur_faces  # KRYTYCZNE: Zaktualizuj słownik!
        self.settings['confidence_threshold'] = self.confidence_threshold
        if hasattr(settings_model, 'camera_name'):
            self.settings['camera_name'] = settings_model.camera_name
        
        self.settings.update({
            'schedule': self.schedule,
            'camera_index': self.assigned_camera_index,
        })
        
        if hasattr(self, 'anonymizer_worker') and self.anonymizer_worker is not None:
            self.anonymizer_worker.update_worker_settings(self)
    
    def _is_within_schedule(self):
        """Check if current time is within camera operation schedule (weekly)"""
        try:
            # WYRZUĆ wszystkie wywołania Settings.query.first() - używaj tylko self.schedule
            if not self.schedule:
                return False  # Nie ma harmonogramu
            
            now = datetime.now()
            current_day = now.strftime('%A').lower()  # e.g., "monday"
            current_time = now.time()
            
            # Get today's schedule config (używaj bezpośrednio self.schedule)
            today_schedule = self.schedule.get(current_day)
            
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
            self.camera_was_manually_started = True  # Oznacz, że użytkownik ręcznie włączył kamerę
            # Użyj przypisanego indeksu kamery (nie skanuj!)
            self.camera_index = self.assigned_camera_index
            print(f"\nInitializing camera with STRICT index {self.camera_index} (assigned camera)...")

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
                print(f"[BŁĄD KRYTYCZNY] Nie można otworzyć kamery (Index: {self.assigned_camera_index})!")
                print("PRZYCZYNA: Kamera jest prawdopodobnie UŻYWANA PRZEZ INNĄ APLIKACJĘ.")
                print("ROZWIĄZANIE: Zamknij WSZYSTKIE inne programy, które mogą używać tej kamery")
                print("(np. okno Ustawień Windows, klient Iriun, Zoom, OBS, Teams)")
                print("i zrestartuj serwer.")
                print("===============================================================\n")
                self.is_running = False
                self.camera = None
                return
            
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
            # UWAGA: Nie tworzymy tutaj nowego wątku - _camera_loop już działa od startu (w __init__)
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            self.is_running = False
            if self.camera is not None:
                self.camera.release()
                self.camera = None

    def _open_camera_for_loop(self):
        """Otwiera kamerę bez tworzenia nowego wątku (używane z wewnątrz _camera_loop)."""
        try:
            # Użyj przypisanego indeksu kamery
            self.camera_index = self.assigned_camera_index
            print(f"Otwieranie kamery o indeksie {self.camera_index}...")
            
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
                last_error = f"Failed to open camera index {self.camera_index} using backend {backend}"
            
            # If still no camera, don't set is_running
            if self.camera is None or not self.camera.isOpened():
                if last_error:
                    print(last_error)
                print(f"Nie można otworzyć kamery o indeksie {self.assigned_camera_index}")
                return False
            
            # Configure codec and resolution
            try:
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            except Exception:
                pass
            
            # Try preferred resolutions
            preferred_res = [(1280, 720), (640, 480)]
            for w, h in preferred_res:
                try:
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                except Exception:
                    continue
                if self._capture_has_valid_frame(self.camera, warmup_reads=5, delay_s=0.05):
                    break
            
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            print(f"Kamera otwarta pomyślnie: {width}x{height} @ {fps} FPS")
            
            self.is_running = True
            return True
            
        except Exception as e:
            print(f"Błąd podczas otwierania kamery: {e}")
            self.is_running = False
            if self.camera is not None:
                try:
                    self.camera.release()
                except:
                    pass
                self.camera = None
            return False

    def _stop_camera_for_loop(self):
        """Zatrzymuje kamerę bez czekania na wątek (używane z wewnątrz _camera_loop)."""
        print("Zatrzymywanie kamery...")
        self.is_running = False
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception as e:
                print(f"Błąd podczas zamykania kamery: {e}")
            self.camera = None
        print("Kamera zatrzymana.")

    def stop_camera(self):
        """Stop the camera and cleanup resources (GUI cleanup in main thread)."""
        print("\nStopping camera...")
        # UWAGA: Ta funkcja NIE ustawia manual_stop_engaged - to robi tylko endpoint API
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

    def set_assigned_camera(self, index):
        """Ustawia, który indeks kamery ma być monitorowany."""
        if index == self.assigned_camera_index:
            # Indeks się nie zmienił, NIE RESTARTUJ kamery.
            print(f"INFO: Indeks kamery się nie zmienił ({index}), pomijam restart.")
            return
        
        # Indeks się zmienił, zrestartuj
        print(f"Kontroler przypisany do nowej kamery: {index} (poprzedni: {self.assigned_camera_index})")
        self.assigned_camera_index = index
        if self.is_running:
            print("Kamera jest uruchomiona. Zatrzymywanie, aby zastosować nowy indeks...")
            self.stop_camera()  # To już nie ustawi manual_stop_engaged
            # Opcjonalnie: można automatycznie uruchomić kamerę z nowym indeksem
            # self._open_camera_for_loop()

    def update_roi_zones(self, new_zones_list):
        """Publiczna metoda do aktualizacji stref ROI z zewnątrz (np. z app.py)."""
        print(f"Aktualizowanie stref ROI. Załadowano {len(new_zones_list)} stref.")
        self.roi_zones = new_zones_list

    def find_matching_zone(self, center_x, center_y, frame_width, frame_height):
        """Sprawdza, czy punkt (x, y) detekcji wpada w którąś ze zdefiniowanych stref ROI."""
        # Znormalizuj współrzędne detekcji (0.0 do 1.0)
        norm_x = center_x / frame_width
        norm_y = center_y / frame_height

        for zone in self.roi_zones:
            # Zakładamy, że 'coords' to {'x': 0.1, 'y': 0.1, 'w': 0.2, 'h': 0.2} w formacie znormalizowanym
            coords = zone.get('coords', {})
            if not isinstance(coords, dict):
                continue
            
            x = coords.get('x', 0)
            y = coords.get('y', 0)
            w = coords.get('w', 0)
            h = coords.get('h', 0)
            
            # Oblicz x2 i y2 (prawy dolny róg)
            x2 = x + w
            y2 = y + h

            if x <= norm_x <= x2 and y <= norm_y <= y2:
                return zone.get('name')  # Zwróć nazwę strefy (np. "ławka 1")

        return None  # Nie znaleziono dopasowania

    def trigger_throttled_notification(self, zone_name, frame, confidence):
        """Sprawdza wyciszenie i wysyła powiadomienie dla danej strefy."""
        now = datetime.now()

        with self.alert_lock:
            # 1. Sprawdź, czy strefa jest wyciszona
            if zone_name in self.alert_mute_until:
                if now < self.alert_mute_until[zone_name]:
                    # JEST WYCISZONA. Ignoruj.
                    mute_until_str = self.alert_mute_until[zone_name].strftime('%H:%M:%S')
                    print(f"🔇 Strefa '{zone_name}' jest wyciszona do {mute_until_str}. Pomijam alert.")
                    return
                else:
                    # Czas wyciszenia minął
                    self.alert_mute_until.pop(zone_name, None)

            # 2. NIE JEST WYCISZONA. Wyślij alerty.
            print(f"📱 WYKRYTO TELEFON w strefie '{zone_name}'. Wysyłanie alertów...")

            # Wywołaj _handle_detection z informacją o strefie
            self._handle_detection(frame, confidence, zone_name)

            # 3. Ustaw nowe wyciszenie dla TEJ STREFY
            print(f"⏰ Ustawiam 5-minutowe wyciszenie dla strefy '{zone_name}'.")
            self.alert_mute_until[zone_name] = now + self.mute_duration

    def _handle_detection(self, frame, confidence, zone_name=None):
        """
        Obsługuje wykrycie telefonu:
        1. Zapisuje ORYGINALNĄ klatkę (bez zamazanych głów!)
        2. Dodaje do kolejki dla AnonymizerWorker z ZAMROŻONĄ konfiguracją blur
        3. Worker zamaże głowy (jeśli włączone) i doda do DB
        """
        try:
            # Create detections directory if it doesn't exist
            os.makedirs('detections', exist_ok=True)
            
            # Save ORIGINAL image (without blurred heads!)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'phone_{timestamp}.jpg'
            filepath = os.path.join('detections', filename)
            
            # Walidacja klatki przed zapisem
            if frame is None or frame.size == 0:
                raise Exception("Invalid frame: None or empty")
            
            try:
                success = cv2.imwrite(filepath, frame)
                if not success:
                    raise Exception("Failed to save detection image")
            except cv2.error as cv_err:
                raise Exception(f"OpenCV error during imwrite: {cv_err}")
            
            should_blur = self.settings.get('blur_faces', True)
            
            detection_data = {
                'filepath': filepath,
                'confidence': confidence,
                'should_blur': should_blur,
                'zone_name': zone_name
            }
            self.detection_queue.put(detection_data)
            
        except Exception as e:
            import logging
            logging.error(f"Error saving detection: {e}")
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)

    # USUNIĘTE: process_detection_queue() - teraz robi to AnonymizerWorker asynchronicznie

    def _enhance_frame_for_detection(self, frame):
        """
        Poprawia jakość obrazu przed detekcją smartfonów.
        Zastosowane techniki:
        - Zwiększenie kontrastu (CLAHE - Contrast Limited Adaptive Histogram Equalization)
        - Wyostrzenie obrazu (unsharp masking)
        - Opcjonalne zwiększenie rozdzielczości dla małych obiektów
        
        Args:
            frame: numpy array (BGR image)
            
        Returns:
            enhanced_frame: numpy array z ulepszonym obrazem
        """
        try:
            enhanced = frame.copy()
            
            # 1. Konwersja do LAB i zwiększenie kontrastu tylko w kanale L (jasność)
            # To poprawia wykrywanie telefonów w różnych warunkach oświetleniowych
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
            
            # Zastosuj CLAHE (Contrast Limited Adaptive Histogram Equalization)
            # CLAHE jest lepsze niż zwykłe histogram equalization, bo nie powoduje over-enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_channel_enhanced = clahe.apply(l_channel)
            
            # Połącz z powrotem
            lab_enhanced = cv2.merge([l_channel_enhanced, a, b])
            enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
            
            # 2. Wyostrzenie obrazu (unsharp masking)
            # To pomaga w wykrywaniu krawędzi telefonów
            gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
            enhanced = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
            
            # 3. Opcjonalne zwiększenie rozdzielczości dla małych telefonów
            # Zwiększamy tylko jeśli obraz jest mały (poniżej 640px szerokości)
            h, w = enhanced.shape[:2]
            if w < 640:
                scale_factor = 640 / w
                new_width = int(w * scale_factor)
                new_height = int(h * scale_factor)
                enhanced = cv2.resize(enhanced, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            return enhanced
            
        except Exception as e:
            # W przypadku błędu, zwróć oryginalną klatkę
            print(f"⚠️  Błąd podczas ulepszania obrazu: {e}, używam oryginalnej klatki")
            return frame

    def _camera_loop(self):
        """Main camera loop for capturing and processing frames"""
        print("Starting camera loop...")
        consecutive_failures = 0
        opencv_error_count = 0  # Licznik błędów OpenCV
        
        while True:
            try:
                # Sprawdź aktualny stan harmonogramu
                is_within = self._is_within_schedule()
                
                # --- NOWA LOGIKA WYKRYWANIA ZMIAN ---
                # Sprawdzamy, czy harmonogram WŁAŚNIE SIĘ ZACZĄŁ
                # (tzn. jest w harmonogramie, a w poprzedniej pętli nie był)
                # UWAGA: Resetujemy manual_stop_engaged TYLKO jeśli użytkownik wcześniej ręcznie włączył kamerę
                if is_within and not self.was_within_schedule:
                    if self.camera_was_manually_started:
                        print("INFO: Wykryto początek nowego okresu harmonogramu.")
                        print("INFO: Automatyczne resetowanie flagi 'manual_stop_engaged' (kamera była wcześniej ręcznie włączona).")
                        self.manual_stop_engaged = False  # Resetuj blokadę tylko jeśli była ręcznie włączona
                    else:
                        print("INFO: Wykryto początek harmonogramu, ale kamera nie była ręcznie włączona w tej sesji - pomijam auto-start.")
                
                # Zapisz obecny stan na potrzeby następnej pętli
                self.was_within_schedule = is_within
                # --- KONIEC NOWEJ LOGIKI ---
                
                # Teraz uruchom standardową logikę start/stop
                if is_within:
                    # Jesteśmy w harmonogramie. Kamera MUSI działać.
                    if not self.is_running:
                        # Sprawdź, czy nie ma blokady manualnej
                        if self.manual_stop_engaged:
                            print("INFO: Automatyczne uruchomienie zablokowane przez manual stop.")
                        else:
                            # Kamera jest zatrzymana, ale powinna działać. Uruchom ją.
                            print("INFO: Czas zgodny z harmonogramem. Automatyczne uruchamianie kamery...")
                            # Otwórz kamerę bezpośrednio (bez tworzenia nowego wątku, bo już jesteśmy w pętli)
                            self._open_camera_for_loop()
                else:
                    # Jesteśmy poza harmonogramem. Kamera MUSI być wyłączona.
                    if self.is_running:
                        print("INFO: Czas poza harmonogramem. Automatyczne zatrzymywanie kamery...")
                        self._stop_camera_for_loop()
                        # Ważne: Zatrzymanie przez harmonogram resetuje też manual_stop_engaged
                        self.manual_stop_engaged = False
                
                # Jeśli kamera nie jest uruchomiona (bo jest poza harmonogramem lub wystąpił błąd),
                # śpij i kontynuuj pętlę (nie próbuj czytać klatek).
                if not self.is_running:
                    time.sleep(5)  # Sprawdź harmonogram ponownie za 5 sekund
                    continue
                
                # Sprawdzenie, czy kamera jest otwarta
                if not self.camera or not self.camera.isOpened():
                    # --- TO JEST JEDYNA POPRAWNA LOGIKA ODZYSKIWANIA ---
                    print(f"Ostrzeżenie: Kamera (indeks {self.assigned_camera_index}) jest zamknięta. Próba ponownego otwarcia...")
                    try:
                        if self.camera is not None:
                            self.camera.release()
                        self.camera = self._open_capture(self.assigned_camera_index)
                        if self.camera is None or not self.camera.isOpened():
                            print("BŁĄD: Ponowne otwarcie kamery nie powiodło się. Czekam 5 sekund...")
                            time.sleep(5)
                        else:
                            # Reset properties after reopen
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            print("Camera reopened successfully")
                    except Exception as e:
                        print(f"BŁĄD podczas ponownego otwarcia kamery: {e}. Czekam 5 sekund...")
                        time.sleep(5)
                    continue  # Spróbuj ponownie w następnej pętli
                    # --- KONIEC LOGIKI ODZYSKIWANIA ---
                
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
                        print(f"Zbyt wiele błędów odczytu, próba ponownego otwarcia kamery (indeks {self.assigned_camera_index})...")
                        try:
                            if self.camera is not None:
                                self.camera.release()
                            self.camera = self._open_capture(self.assigned_camera_index)
                            if self.camera is None or not self.camera.isOpened() or not self._capture_has_valid_frame(self.camera):
                                print("BŁĄD: Ponowne otwarcie kamery nie powiodło się. Czekam 5 sekund...")
                                time.sleep(5)
                                continue
                            # Reset properties after reopen
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            consecutive_failures = 0
                            print("Camera reopened successfully")
                        except Exception as e:
                            print(f"BŁĄD podczas ponownego otwarcia kamery: {e}. Czekam 5 sekund...")
                            time.sleep(5)
                            continue
                    # Daj kamerze chwilę na odzyskanie
                    time.sleep(0.1)
                    continue  # Przeskocz do następnej iteracji pętli - NIE ustawiamy last_frame!
                
                # Dopiero teraz klatka jest bezpieczna - ustawiamy last_frame PRZED wszystkimi innymi operacjami
                consecutive_failures = 0
                opencv_error_count = 0  # Reset licznika błędów OpenCV po udanym odczycie
                
                # Dodatkowa walidacja przed .copy() - sprawdź czy klatka jest ciągła w pamięci
                try:
                    if not frame.data.contiguous:
                        print("Ostrzeżenie: Klatka nie jest ciągła w pamięci. Tworzenie kopii...")
                        frame = np.ascontiguousarray(frame)
                except Exception:
                    pass  # Jeśli nie możemy sprawdzić, kontynuuj normalnie
                
                try:
                    with self.frame_lock:
                        self.last_frame = frame.copy()
                except cv2.error as e:
                    print(f"Błąd OpenCV podczas kopiowania klatki: {e}")
                    opencv_error_count += 1
                    time.sleep(0.1)
                    continue
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
                
                # KLUCZOWE: NIE zamazuj głów w real-time!
                # Zamazywanie będzie robione OFFLINE przez AnonymizerWorker
                # Wyświetlamy ORYGINALNĄ klatkę bez zamazania
                try:
                    display_frame = frame.copy()
                except cv2.error as e:
                    print(f"Błąd OpenCV podczas kopiowania display_frame: {e}")
                    opencv_error_count += 1
                    time.sleep(0.1)
                    continue
                except Exception as e:
                    print(f"Error copying frame for display: {e}")
                    time.sleep(0.1)
                    continue
                
                # Increment frame counter for skipping logic
                self.frame_counter += 1
                
                # --- KLUCZOWA LOGIKA POMIJANIA KLATEK ---
                # Jeśli to nie jest co 3. klatka, przeskocz do następnej iteracji
                # To pozwala na płynne działanie streamu, a detekcję wykonujemy tylko co 3. klatkę (dla lepszej detekcji)
                if self.frame_counter % self.process_every_n_frame != 0:
                    continue  # Pomiń detekcję dla tej klatki, ale stream działa normalnie
                
                # --- TEN KOD WYKONA SIĘ TERAZ TYLKO CO 3. KLATKĘ ---
                # (Zakładając 30 FPS = 10 detekcji na sekundę)
                if self.model is not None:
                    try:
                        # Validate display_frame exists and is valid before using
                        if display_frame is None or display_frame.size == 0:
                            continue
                        
                        # Preprocessing obrazu dla lepszej detekcji smartfonów
                        enhanced_frame = self._enhance_frame_for_detection(frame)
                            
                        results = self.model(enhanced_frame, verbose=False)  # Używa ulepszonej klatki
                        # Pobierz wymiary klatki do normalizacji
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
                                    # Oblicz środek detekcji
                                    bx1, by1, bx2, by2 = map(float, box.xyxy[0])
                                    center_x = (bx1 + bx2) / 2.0
                                    center_y = (by1 + by2) / 2.0
                                    
                                    # Znajdź, w której strefie jest telefon
                                    matched_zone = self.find_matching_zone(center_x, center_y, frame_width, frame_height)
                                    
                                    if matched_zone:
                                        # Mamy trafienie w strefę! Uruchom logikę throttlingu
                                        try:
                                            frame_copy = frame.copy()
                                            self.trigger_throttled_notification(matched_zone, frame_copy, confidence)
                                        except cv2.error as copy_err:
                                            print(f"Błąd OpenCV podczas kopiowania klatki dla detekcji: {copy_err}")
                                            opencv_error_count += 1
                                        except Exception as copy_err:
                                            print(f"Błąd podczas kopiowania klatki dla detekcji: {copy_err}")
                                    elif len(self.roi_zones) > 0:
                                        # Są zdefiniowane strefy, ale telefon nie trafił w żadną - pomijamy
                                        continue
                                    else:
                                        # Brak zdefiniowanych stref - użyj starej logiki (kompatybilność wsteczna)
                                        # Sprawdź legacy ROI jeśli istnieje
                                        roi = self.settings.get('roi_coordinates')
                                        allow = True
                                        if roi and isinstance(roi, (list, tuple)) and len(roi) == 4:
                                            try:
                                                x1f, y1f, x2f, y2f = [float(v) for v in roi]
                                            except Exception:
                                                x1f, y1f, x2f, y2f = 0.0, 0.0, 1.0, 1.0
                                            norm_cx = center_x / max(1, frame_width)
                                            print(f"Błąd podczas kopiowania klatki dla legacy detekcji: {copy_err}")

                                    # Rysuj bounding box na wyświetlanej klatce
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
                                            label = f"Phone: {confidence:.2f}"
                                            if matched_zone:
                                                label += f" [{matched_zone}]"
                                            cv2.putText(display_frame, label, (x1, text_y),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                        except Exception as draw_err:
                                            print(f"Error drawing phone box: {draw_err}")
                                    
                                    # Opcjonalnie: break, jeśli wystarczy nam jeden telefon na klatkę
                                    # break
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
                opencv_error_count += 1
                print(f"BŁĄD KRYTYCZNY OpenCV (cv::Mat::Mat?) w pętli kamery: {e}")
                print(f"Liczba błędów OpenCV: {opencv_error_count}/10")
                
                # Po 10 błędach OpenCV, zrestartuj kamerę
                if opencv_error_count >= 10:
                    print("⚠️ Zbyt wiele błędów OpenCV. Restart kamery...")
                    opencv_error_count = 0
                    try:
                        if self.camera is not None:
                            self.camera.release()
                        time.sleep(2)  # Poczekaj przed ponownym otwarciem
                        self.camera = self._open_capture(self.assigned_camera_index)
                        if self.camera is None or not self.camera.isOpened():
                            print("BŁĄD: Ponowne otwarcie kamery po błędach OpenCV nie powiodło się.")
                            time.sleep(5)
                        else:
                            # Reset properties
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            print("✅ Kamera zrestartowana pomyślnie po błędach OpenCV")
                    except Exception as restart_err:
                        print(f"BŁĄD podczas restartu kamery: {restart_err}")
                        time.sleep(5)
                else:
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
        """Zwraca kopię ostatniej klatki w sposób bezpieczny wątkowo (jeśli istnieje)."""
        if self.last_frame is not None:
            with self.frame_lock:
                try:
                    return self.last_frame.copy()
                except Exception as e:
                    print(f"Error copying frame in get_last_frame: {e}")
                    return None
        return None

    def anonymize_frame_logic(self, frame):
        """
        Anonimizuje wykryte głowy na numpy array (frame).
        Używa modelu Roboflow head-detection z AnonymizerWorker.
        
        Args:
            frame: numpy array (BGR image)
            
        Returns:
            anonymized_frame: numpy array z zanonimizowanymi głowami
        """
        try:
            # Użyj modelu z AnonymizerWorker jeśli dostępny
            anonymization_model = None
            if hasattr(self, 'anonymizer_worker'):
                if self.anonymizer_worker.model is not None:
                    anonymization_model = self.anonymizer_worker.model
            
            if anonymization_model is None:
                return frame.copy()
            
            # Kopiuj klatkę aby nie modyfikować oryginału
            anonymized_frame = frame.copy()
            img_h, img_w = anonymized_frame.shape[:2]
            
            # Zapisz klatkę tymczasowo (Roboflow wymaga pliku)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                temp_path = tmp.name
                cv2.imwrite(temp_path, frame)
            
            try:
                # Wykryj głowy za pomocą modelu Roboflow
                prediction = anonymization_model.predict(temp_path, confidence=40, overlap=30)
                results = prediction.json()
                
                predictions = results.get('predictions', [])
                
                heads_blurred = 0
                # Przetwórz wyniki (format Roboflow: x, y = środek; width, height)
                for det in predictions:
                    confidence = det.get('confidence', 0)
                    
                    # Wykrywamy głowy
                    if confidence >= 0.4:  # 0.4 = 40%
                        # Pobierz współrzędne (Roboflow: środek + wymiary)
                        center_x = int(det['x'])
                        center_y = int(det['y'])
                        width = int(det['width'])
                        height = int(det['height'])
                        
                        # Konwertuj na (x1, y1, x2, y2)
                        x1 = center_x - width // 2
                        y1 = center_y - height // 2
                        x2 = center_x + width // 2
                        y2 = center_y + height // 2
                        
                        # Upewnij się, że współrzędne są w granicach obrazu
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(img_w, x2), min(img_h, y2)
                        
                        # Sprawdź czy ROI ma sens
                        if x2 <= x1 or y2 <= y1:
                            continue
                        
                        # Wybierz region (całą głowę)
                        roi = anonymized_frame[y1:y2, x1:x2]
                        
                        # Zastosuj silne rozmycie
                        if roi.size > 0:
                            blur = cv2.GaussianBlur(roi, (99, 99), 30)
                            anonymized_frame[y1:y2, x1:x2] = blur
                            heads_blurred += 1
            
            finally:
                # Usuń tymczasowy plik
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            return anonymized_frame
            
        except Exception as e:
            import logging
            logging.error(f"Error in anonymize_frame_logic: {e}")
            return frame.copy()

    def __del__(self):
        """Czysty shutdown - zatrzymaj kamerę i workera"""
        self.stop_camera()
        
        if hasattr(self, 'anonymizer_worker'):
            self.detection_queue.put(None)
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
    def _scan_available_cameras_static():
        """Statyczna metoda do skanowania kamer - wywoływana tylko raz przy starcie serwera."""
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

    def get_available_cameras(self):
        """NOWA, SZYBKA metoda: Natychmiast zwraca zapisaną listę (bez skanowania)."""
        return self.available_cameras_list if hasattr(self, 'available_cameras_list') else []


    def find_camera_by_name(self, camera_name):
        """Find camera index by device name using Media Foundation API"""
        try:
            print(f"\n🔍 Searching for camera: {camera_name}")
            
            # First try to find by exact name match in both Camera and Image classes
            cmd = "powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | Select-Object Name, DeviceID, Manufacturer, Description, PNPClass | ConvertTo-Json\""
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Error getting camera list: {result.stderr}")
                # Fallback to using cached camera list
                available_cameras = self.get_available_cameras()
                for camera in available_cameras:
                    if camera_name.lower() in camera['name'].lower():
                        print(f"✅ Found camera '{camera_name}' at index {camera['index']} (via cached list)")
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
            
            # If not found by exact name, try using cached camera list
            print("Camera not found by name, checking cached camera list...")
            available_cameras = self.get_available_cameras()
            for camera in available_cameras:
                if camera_name.lower() in camera['name'].lower() or "iriun" in camera_name.lower() and "iriun" in camera['name'].lower():
                    print(f"✅ Found camera '{camera_name}' at index {camera['index']} (via cached list)")
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
    Worker thread do offline anonimizacji głów.
    
    Używa modelu Roboflow head-detection do wykrywania głów, zamazuje całą głowę.
    Działa asynchronicznie - nie blokuje głównej pętli kamery.
    Obsługuje również powiadomienia SMS przez Vonage i upload do Cloudinary.
    """
    
    def __init__(self, detection_queue, settings, 
                 yolo_model=None, vonage_sms=None, cloudinary_enabled=False,
                 email_user=None, email_password=None, email_recipient=None,
                 blur_kernel_size=99, blur_sigma=30):
        super().__init__(daemon=True)
        self.detection_queue = detection_queue
        self.settings = settings  # Referencja do settings z CameraController
        self.blur_kernel_size = blur_kernel_size
        self.blur_sigma = blur_sigma
        self.is_running = True
        
        # Statystyki
        self.tasks_processed = 0
        self.persons_anonymized = 0
        
        # Użyj przekazanych zasobów (NIE inicjalizuj ich tutaj!)
        self.model = yolo_model
        if self.model is not None:
            print("✅ AnonymizerWorker: Używam przekazanego modelu YOLO (head-detection)")
            print("   Zamazywanie całej wykrytej głowy")
        else:
            print("⚠️  AnonymizerWorker: Brak modelu YOLO (anonymization) - anonimizacja będzie wyłączona")
        
        # Użyj przekazanego klienta Vonage
        self.vonage_sms = vonage_sms
        # Inicjalizuj zmienne Vonage (potrzebne do wysyłania SMS)
        self.vonage_api_key = os.getenv('VONAGE_API_KEY')
        self.vonage_api_secret = os.getenv('VONAGE_API_SECRET')
        self.vonage_from_number = os.getenv('VONAGE_FROM_NUMBER', 'PhoneDetection')
        self.vonage_to_number = os.getenv('VONAGE_TO_NUMBER')
        
        if self.vonage_sms is not None:
            print("✅ AnonymizerWorker: Używam przekazanego klienta Vonage")
            if self.vonage_to_number:
                print(f"   Numer docelowy: {self.vonage_to_number}")
            else:
                print("⚠️  Brak numeru docelowego (VONAGE_TO_NUMBER) - SMS nie będzie działać")
        else:
            print("⚠️  AnonymizerWorker: Brak klienta Vonage - SMS będzie wyłączone")
        
        # Użyj przekazanej konfiguracji Cloudinary
        self.cloudinary_enabled = cloudinary_enabled
        if self.cloudinary_enabled:
            print("✅ AnonymizerWorker: Cloudinary jest włączone")
        else:
            print("⚠️  AnonymizerWorker: Cloudinary jest wyłączone")
        
        # Użyj przekazanych danych Email
        self.email_user = email_user
        self.email_password = email_password
        self.email_recipient = email_recipient
        if all([self.email_user, self.email_password, self.email_recipient]):
            print(f"✅ AnonymizerWorker: Dane Email załadowane (from: {self.email_user})")
        else:
            print("⚠️  AnonymizerWorker: Brak danych Email - email będzie wyłączony")
        
        # Ustawienia powiadomień - aktualizowalne w locie
        self.email_enabled = False  # Domyślnie wyłączone
        self.sms_enabled = False  # Domyślnie wyłączone
        self.settings_lock = threading.Lock()  # Lock do ochrony ustawień
        
        # Inicjalizuj ustawienia z przekazanego słownika settings (jeśli dostępne)
        if settings:
            with self.settings_lock:
                self.email_enabled = settings.get('email_notifications', False)
                self.sms_enabled = settings.get('sms_notifications', False)
                print(f"INFO: Worker zainicjalizowany z ustawieniami: email={self.email_enabled}, sms={self.sms_enabled}")
    
    def update_worker_settings(self, controller_instance):
        """
        Aktualizuje ustawienia powiadomień w locie (wywoływane z CameraController.update_settings).
        Przyjmuje instancję kontrolera, aby odczytać zaktualizowane wartości.
        """
        with self.settings_lock:
            # Odczytaj zaktualizowane wartości z KONTROLERA
            self.email_enabled = controller_instance.email_enabled
            self.sms_enabled = controller_instance.sms_enabled
            
            # Aktualizuj też słownik settings dla kompatybilności wstecznej
            self.settings['email_notifications'] = self.email_enabled
            self.settings['sms_notifications'] = self.sms_enabled
            if hasattr(controller_instance, 'camera_name'):
                self.settings['camera_name'] = controller_instance.camera_name
        
        print(f"INFO: Worker anonimizacji otrzymał nowe ustawienia powiadomień: email={self.email_enabled}, sms={self.sms_enabled}")
    
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
                zone_name = task_data.get('zone_name')  # Pobierz zone_name z task_data
                # KLUCZOWE: Odczytaj flagę should_blur (domyślnie True dla bezpieczeństwa)
                should_blur = task_data.get('should_blur', True)
                
                print(f"🔄 Przetwarzanie: {filepath} (blur: {should_blur}, zone: {zone_name})")
                
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
                self._save_to_database(task_data)
                
                # KLUCZOWY WARUNEK: Sprawdź czy KTÓRYKOLWIEK rodzaj powiadomień jest włączony
                # Użyj zmiennych członkowskich (chronionych lockiem) zamiast self.settings
                with self.settings_lock:
                    email_on = self.email_enabled
                    sms_on = self.sms_enabled
                
                if not email_on and not sms_on:
                    print(f"📵 Powiadomienia (Email/SMS) wyłączone - pomijam wysyłkę")
                else:
                    notification_types = []
                    if sms_on:
                        notification_types.append("SMS")
                    if email_on:
                        notification_types.append("Email")
                    
                    print(f"📲 Powiadomienia włączone ({', '.join(notification_types)}) - uruchamiam wysyłkę w tle")
                    # Uruchom w osobnym wątku aby nie blokować pętli run
                    notification_thread = threading.Thread(
                        target=self._handle_cloud_notification,
                        args=(filepath, confidence, zone_name),
                        daemon=True
                    )
                    notification_thread.start()
                
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
    
    def _send_sms_notification(self, public_link, confidence, zone_name=None):
        """
        Wysyła powiadomienie SMS przez Vonage (Nexmo).
        
        Args:
            public_link: Link do pliku na Google Drive (lub None jeśli upload się nie powiódł)
            confidence: Pewność detekcji
            zone_name: Nazwa strefy (np. "ławka 1") lub None
            
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            if self.vonage_sms is None:
                print("❌ Klient Vonage nie jest zainicjalizowany")
                return False
            
            if not self.vonage_to_number:
                print("❌ Brak numeru docelowego (VONAGE_TO_NUMBER) - nie można wysłać SMS")
                return False
            
            # Przygotuj treść wiadomości
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            location = zone_name or self.settings.get('camera_name', 'Camera 1')
            
            if public_link:
                message_body = (
                    f"Phone Detection Alert!\n"
                    f"Time: {timestamp}\n"
                    f"Location: {location}\n"
                    f"Confidence: {confidence:.2%}\n"
                    f"Image: {public_link}\n"
                    f"---"  # Padding dla Vonage demo - chroni link przed [FREE SMS DEMO...]
                )
            else:
                # Wyślij SMS bez linku jeśli Cloudinary zawiódł
                message_body = (
                    f"Phone Detection Alert!\n"
                    f"Time: {timestamp}\n"
                    f"Location: {location}\n"
                    f"Confidence: {confidence:.2%}\n"
                    f"(Image upload failed)\n"
                    f"---"  # Padding dla Vonage demo
                )
            
            # Vonage wymaga numeru bez '+' i jako string
            to_number = str(self.vonage_to_number).replace('+', '')
            
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
    
    def _handle_cloud_notification(self, filepath, confidence, zone_name=None):
        """
        Orkiestrator powiadomień - upload na Cloudinary i wysyłka SMS/Email.
        
        Args:
            filepath: Ścieżka do pliku
            confidence: Pewność detekcji
            zone_name: Nazwa strefy (np. "ławka 1") lub None
        """
        try:
            print(f"🚀 Rozpoczynam wysyłkę powiadomienia dla: {filepath}")
            
            # 1. Próbuj upload na Cloudinary (opcjonalnie)
            public_link = self._upload_to_cloudinary(filepath)
            
            # Pobierz aktualne ustawienia powiadomień (chronione lockiem)
            with self.settings_lock:
                email_on = self.email_enabled
                sms_on = self.sms_enabled
            
            if public_link:
                print(f"✅ Plik wysłany na Cloudinary")
                
                # 2. Wyślij SMS jeśli włączony
                if sms_on:
                    print("📱 SMS notifications włączone - wysyłanie...")
                    success = self._send_sms_notification(public_link, confidence, zone_name)
                    if success:
                        print(f"✅ SMS wysłany z linkiem do zdjęcia!")
                    else:
                        print(f"❌ Nie udało się wysłać SMS")
                else:
                    print("📵 SMS notifications wyłączone - pomijam SMS")
                
                # 3. Wyślij Email jeśli włączony
                if email_on:
                    print("📧 Email notifications włączone - wysyłanie...")
                    location = zone_name or self.settings.get('camera_name', 'Camera 1')
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
                
                if sms_on:
                    print("   ale wyślę SMS bez linku")
                    success = self._send_sms_notification(None, confidence, zone_name)
                    if success:
                        print(f"✅ SMS wysłany (bez linku)")
                    else:
                        print(f"❌ Nie udało się wysłać SMS")
                
                # Email z informacją o braku linku
                if email_on:
                    print("📧 Email notifications włączone - wysyłanie (bez linku Cloudinary)...")
                    location = zone_name or self.settings.get('camera_name', 'Camera 1')
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
        Anonimizuje wykryte głowy używając modelu Roboflow head-detection.
        
        Strategia:
        - Wykrywa głowy za pomocą modelu Roboflow
        - Dla każdej wykrytej głowy zamazuje cały bounding box
        - Jeśli brak głów - zapisuje oryginał bez zmian
        
        Args:
            image_path: Ścieżka do obrazu
            
        Returns:
            True jeśli sukces
        """
        try:
            # Sprawdź czy model jest dostępny
            if self.model is None:
                print("⚠️  Model Roboflow head-detection niedostępny, zapisuję oryginał")
                return True  # Brak modelu = zapisz oryginał
            
            # Wczytaj obraz
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Nie można wczytać: {image_path}")
                return False
            
            # Pobierz wymiary obrazu
            img_h, img_w = image.shape[:2]
            
            # Wykryj głowy za pomocą modelu Roboflow
            prediction = self.model.predict(image_path, confidence=40, overlap=30)
            results = prediction.json()
            
            heads_found = 0
            
            # Przetwórz wyniki (format Roboflow: x, y = środek; width, height)
            for det in results.get('predictions', []):
                confidence = det.get('confidence', 0)
                
                # Wykrywamy głowy
                if confidence >= 0.4:  # 0.4 = 40%
                    heads_found += 1
                    
                    # Pobierz współrzędne (Roboflow: środek + wymiary)
                    center_x = int(det['x'])
                    center_y = int(det['y'])
                    width = int(det['width'])
                    height = int(det['height'])
                    
                    # Konwertuj na (x1, y1, x2, y2)
                    x1 = center_x - width // 2
                    y1 = center_y - height // 2
                    x2 = center_x + width // 2
                    y2 = center_y + height // 2
                    
                    # Upewnij się, że współrzędne są w granicach obrazu
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(img_w, x2), min(img_h, y2)
                    
                    # Sprawdź czy ROI ma sens
                    if x2 <= x1 or y2 <= y1:
                        print(f"⚠️  Nieprawidłowy ROI głowy: ({x1},{y1})-({x2},{y2}), pomijam")
                        continue
                    
                    # Wybierz region (całą głowę)
                    roi = image[y1:y2, x1:x2]
                    
                    # Zastosuj silne rozmycie
                    if roi.size > 0:
                        blur = cv2.GaussianBlur(roi, (99, 99), 30)
                        image[y1:y2, x1:x2] = blur
                        self.persons_anonymized += 1
                        print(f"  ✓ Zanonimizowano głowę #{heads_found} (conf: {confidence:.2f})")
                    else:
                        print(f"⚠️  Pusty ROI dla głowy, pomijam")
            
            if heads_found == 0:
                print(f"ℹ️  Brak głów na obrazie - zapisuję oryginał bez zmian")
            else:
                print(f"👤 Zanonimizowano {heads_found} głów")
            
            # Nadpisz oryginalny plik (zanonimizowanym lub oryginalnym jeśli brak głów)
            success = cv2.imwrite(image_path, image)
            
            if not success:
                print(f"❌ Nie udało się zapisać: {image_path}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Błąd anonimizacji: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _save_to_database(self, detection_data):
        """Zapisuje wykrycie do bazy danych (tylko zanonimizowany obraz)"""
        try:
            from app import app
            filepath = detection_data.get('filepath')
            confidence = detection_data.get('confidence', 0.0)
            zone_name = detection_data.get('zone_name')
            filename = os.path.basename(filepath)
            
            with app.app_context():
                admin_user = User.query.filter_by(username='admin').first()
                if admin_user:
                    # Użyj zone_name jeśli dostępne, w przeciwnym razie użyj nazwy kamery
                    location = zone_name or self.settings.get('camera_name', 'Camera 1')
                    detection = Detection(
                        location=location,
                        confidence=confidence,
                        image_path=filename,
                        status='Pending',
                        user_id=admin_user.id
                    )
                    db.session.add(detection)
                    db.session.commit()
                    print(f"💾 Zapisano do DB: {filename} (strefa: {location})")
                else:
                    print("❌ Brak użytkownika admin")
        except Exception as e:
            print(f"❌ Błąd zapisu do DB: {e}")
    
    def stop(self):
        """Zatrzymuje workera"""
        self.is_running = False


if __name__ == "__main__":
    cameras = CameraController._scan_available_cameras_static()
    for camera in cameras:
        print(f"Camera {camera['index']}: {camera['name']} ({camera['resolution']}, {camera['fps']} FPS)")