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

load_dotenv()

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
        self.frame_lock = threading.Lock()
        
        if camera_name:
            self.camera_index = self.find_camera_by_name(camera_name)
            if self.camera_index is None:
                self.camera_index = camera_index
        else:
            self.camera_index = camera_index
        
        self.assigned_camera_index = self.camera_index
        self._verify_camera()
        
        from models import DEFAULT_SCHEDULE
        
        self.schedule = DEFAULT_SCHEDULE.copy()
        self.assigned_camera_index = self.camera_index
        self.camera_name = camera_name if camera_name else 'Camera 1'
        self.blur_faces = True
        self.confidence_threshold = 0.2
        self.sms_notifications = False
        self.email_notifications = False
        self.email_enabled = False
        self.sms_enabled = False
        self.anonymization_percent = 50
        self.roi_coordinates = None
        self.roi_zones = []
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
        self.alert_mute_until = {}
        self.mute_duration = timedelta(minutes=5)
        self.alert_lock = threading.Lock()
        
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
        self.manual_stop_engaged = True
        self.was_within_schedule = False
        self.camera_was_manually_started = False
        
        self.model = yolo_model_detection
        if self.model is not None:
            self.phone_class_id = None
            for class_id, class_name in self.model.names.items():
                if 'phone' in class_name.lower() or 'cell' in class_name.lower():
                    self.phone_class_id = class_id
                    break
            
            if self.phone_class_id is None:
                self.phone_class_id = 67
        else:
            self.phone_class_id = 67

        self.frame_counter = 0
        self.process_every_n_frame = 3
        
        if available_cameras_list is not None:
            self.available_cameras_list = available_cameras_list
        else:
            self.available_cameras_list = []
        
        self.camera_thread = threading.Thread(target=self._camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()

    def _open_capture(self, index):
        """Open a cv2.VideoCapture STRICTLY for the selected index.

        Order:
        1) Default backend (MSMF on Windows) - preferred for virtual cams like Iriun
        2) DirectShow (CAP_DSHOW) as the only fallback for the SAME index
        No other indices or backends are attempted here.
        """
        
        cap = cv2.VideoCapture(index)
        if cap is not None and cap.isOpened():
            return cap
        try:
            cap.release()
        except Exception:
            pass


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
        try:
            cap = self._open_capture(self.camera_index)
            if not cap.isOpened():
                available_cameras = self.get_available_cameras()
                if available_cameras:
                    self.camera_index = available_cameras[0]['index']
            cap.release()
        except Exception as e:
            import logging
            logging.error(f"Error verifying camera: {e}")

    def update_settings(self, settings_model):
        if hasattr(settings_model, 'schedule') and settings_model.schedule:
            self.schedule = settings_model.schedule.copy()
        
        if hasattr(settings_model, 'roi_zones') and settings_model.roi_zones is not None:
            self.roi_zones = settings_model.roi_zones.copy() if isinstance(settings_model.roi_zones, list) else []
        
        if hasattr(settings_model, 'camera_index') and settings_model.camera_index is not None:
            self.assigned_camera_index = int(settings_model.camera_index)
        
        if hasattr(settings_model, 'blur_faces'):
            self.blur_faces = bool(settings_model.blur_faces)
        
        if hasattr(settings_model, 'confidence_threshold'):
            self.confidence_threshold = float(settings_model.confidence_threshold)
        
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
        
        self.settings['email_notifications'] = self.email_enabled
        self.settings['sms_notifications'] = self.sms_enabled
        self.settings['blur_faces'] = self.blur_faces
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
            if not self.schedule:
                return False
            
            now = datetime.now()
            current_day = now.strftime('%A').lower()
            current_time = now.time()
            today_schedule = self.schedule.get(current_day)
            
            if not today_schedule or not today_schedule.get('enabled', False):
                return False
            
            start_time = datetime.strptime(today_schedule['start'], '%H:%M').time()
            end_time = datetime.strptime(today_schedule['end'], '%H:%M').time()
            
            if end_time < start_time:
                is_within = (current_time >= start_time) or (current_time <= end_time)
            else:
                is_within = start_time <= current_time <= end_time
            
            return is_within
        
        except Exception as e:
            import logging
            logging.error(f"Error checking schedule: {e}")
            return False

    def _check_schedule_start(self):
        """Thread to check when to start the camera based on schedule"""
        while not self.is_running:
            within = self._is_within_schedule()
            if within:
                if not self.manual_stop_engaged:
                    self.start_camera()
                    break
            else:
                self.manual_stop_engaged = False
            time.sleep(1)

    def start_camera(self):
        """Start the camera and detection process (STRICT selected index only)."""
        if self.is_running:
            return
        
        try:
            self.manual_stop_engaged = False
            self.camera_was_manually_started = True
            self.camera_index = self.assigned_camera_index

            self.camera = None
            last_error = None

            for backend in ('default', 'dshow'):
                if backend == 'default':
                    cap = cv2.VideoCapture(self.camera_index)
                else:
                    cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

                if cap is not None and cap.isOpened() and self._capture_has_valid_frame(cap):
                    self.camera = cap
                    break

                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
                last_error = f"Failed to open STRICT camera index {self.camera_index} using backend {backend}"

            if self.camera is None or not self.camera.isOpened():
                import logging
                logging.error(f"Cannot open camera (Index: {self.assigned_camera_index}). Camera may be in use by another application.")
                self.is_running = False
                self.camera = None
                return
            
            try:
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            except Exception:
                pass

            preferred_res = [(1280, 720), (640, 480)]
            applied = None
            for w, h in preferred_res:
                try:
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                except Exception:
                    continue
                if self._capture_has_valid_frame(self.camera, warmup_reads=5, delay_s=0.05):
                    applied = (w, h)
                    break

            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            self.is_running = True
            
        except Exception as e:
            import logging
            logging.error(f"Error starting camera: {e}")
            self.is_running = False
            if self.camera is not None:
                self.camera.release()
                self.camera = None

    def _open_camera_for_loop(self):
        """Otwiera kamerę bez tworzenia nowego wątku (używane z wewnątrz _camera_loop)."""
        try:
            self.camera_index = self.assigned_camera_index
            self.camera = None
            
            for backend in ('default', 'dshow'):
                if backend == 'default':
                    cap = cv2.VideoCapture(self.camera_index)
                else:
                    cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                
                if cap is not None and cap.isOpened() and self._capture_has_valid_frame(cap):
                    self.camera = cap
                    break
                
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
            
            if self.camera is None or not self.camera.isOpened():
                return False
            
            try:
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            except Exception:
                pass
            
            preferred_res = [(1280, 720), (640, 480)]
            for w, h in preferred_res:
                try:
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                except Exception:
                    continue
                if self._capture_has_valid_frame(self.camera, warmup_reads=5, delay_s=0.05):
                    break
            
            self.is_running = True
            return True
            
        except Exception as e:
            import logging
            logging.error(f"Error opening camera: {e}")
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
        self.is_running = False
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception as e:
                import logging
                logging.error(f"Error closing camera: {e}")
            self.camera = None

    def stop_camera(self):
        """Stop the camera and cleanup resources (GUI cleanup in main thread)."""
        self.is_running = False
        
        if hasattr(self, 'camera_thread') and self.camera_thread is not None:
            try:
                self.camera_thread.join(timeout=1.0)
            except Exception:
                pass
        
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None
        
        try:
            try:
                cv2.destroyWindow('Phone Detection')
            except Exception:
                cv2.destroyAllWindows()
        except Exception:
            pass
        
        if not hasattr(self, 'schedule_check_thread') or not self.schedule_check_thread.is_alive():
            self.schedule_check_thread = threading.Thread(target=self._check_schedule_start)
            self.schedule_check_thread.daemon = True
            self.schedule_check_thread.start()

    def set_assigned_camera(self, index):
        """Ustawia, który indeks kamery ma być monitorowany."""
        if index == self.assigned_camera_index:
            return
        
        self.assigned_camera_index = index
        if self.is_running:
            self.stop_camera()

    def update_roi_zones(self, new_zones_list):
        """Publiczna metoda do aktualizacji stref ROI z zewnątrz (np. z app.py)."""
        self.roi_zones = new_zones_list

    def find_matching_zone(self, center_x, center_y, frame_width, frame_height):
        """Sprawdza, czy punkt (x, y) detekcji wpada w którąś ze zdefiniowanych stref ROI."""
        norm_x = center_x / frame_width
        norm_y = center_y / frame_height

        for zone in self.roi_zones:
            coords = zone.get('coords', {})
            if not isinstance(coords, dict):
                continue
            
            x = coords.get('x', 0)
            y = coords.get('y', 0)
            w = coords.get('w', 0)
            h = coords.get('h', 0)
            
            x2 = x + w
            y2 = y + h

            if x <= norm_x <= x2 and y <= norm_y <= y2:
                return zone.get('name')

        return None

    def trigger_throttled_notification(self, zone_name, frame, confidence):
        """Sprawdza wyciszenie i wysyła powiadomienie dla danej strefy."""
        now = datetime.now()

        with self.alert_lock:
            if zone_name in self.alert_mute_until:
                if now < self.alert_mute_until[zone_name]:
                    mute_until_str = self.alert_mute_until[zone_name].strftime('%H:%M:%S')
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"📱 Wykryto telefon w strefie '{zone_name}' (confidence: {confidence:.2%}), ale strefa jest wyciszona do {mute_until_str} - pomijam powiadomienia")
                    return
                else:
                    self.alert_mute_until.pop(zone_name, None)

            self._handle_detection(frame, confidence, zone_name)
            self.alert_mute_until[zone_name] = now + self.mute_duration

    def _handle_detection(self, frame, confidence, zone_name=None):
        """
        Obsługuje wykrycie telefonu:
        1. Zapisuje ORYGINALNĄ klatkę (bez zamazanych głów!)
        2. Dodaje do kolejki dla AnonymizerWorker z ZAMROŻONĄ konfiguracją blur
        3. Worker zamaże głowy (jeśli włączone) i doda do DB
        """
        try:
            os.makedirs('detections', exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'phone_{timestamp}.jpg'
            filepath = os.path.join('detections', filename)
            
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
            
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_channel_enhanced = clahe.apply(l_channel)
            
            lab_enhanced = cv2.merge([l_channel_enhanced, a, b])
            enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
            
            gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
            enhanced = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
            
            h, w = enhanced.shape[:2]
            if w < 640:
                scale_factor = 640 / w
                new_width = int(w * scale_factor)
                new_height = int(h * scale_factor)
                enhanced = cv2.resize(enhanced, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            return enhanced
            
        except Exception as e:
            import logging
            logging.error(f"Error enhancing frame: {e}")
            return frame

    def _camera_loop(self):
        """Main camera loop for capturing and processing frames"""
        consecutive_failures = 0
        opencv_error_count = 0
        
        while True:
            try:
                is_within = self._is_within_schedule()
                
                if is_within and not self.was_within_schedule:
                    if self.camera_was_manually_started:
                        self.manual_stop_engaged = False
                
                self.was_within_schedule = is_within
                
                if is_within:
                    if not self.is_running:
                        if not self.manual_stop_engaged:
                            self._open_camera_for_loop()
                else:
                    if self.is_running:
                        self._stop_camera_for_loop()
                        self.manual_stop_engaged = False
                
                if not self.is_running:
                    time.sleep(5)
                    continue
                
                if not self.camera or not self.camera.isOpened():
                    try:
                        if self.camera is not None:
                            self.camera.release()
                        self.camera = self._open_capture(self.assigned_camera_index)
                        if self.camera is None or not self.camera.isOpened():
                            time.sleep(5)
                        else:
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    except Exception:
                        time.sleep(5)
                    continue
                
                ret, frame = self.camera.read()
                
                frame_is_invalid = False
                try:
                    if not ret or frame is None:
                        frame_is_invalid = True
                    else:
                        if not hasattr(frame, 'size') or frame.size == 0:
                            frame_is_invalid = True
                except Exception as e:
                    frame_is_invalid = True
                
                if frame_is_invalid:
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        try:
                            if self.camera is not None:
                                self.camera.release()
                            self.camera = self._open_capture(self.assigned_camera_index)
                            if self.camera is None or not self.camera.isOpened() or not self._capture_has_valid_frame(self.camera):
                                time.sleep(5)
                                continue
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            consecutive_failures = 0
                        except Exception:
                            time.sleep(5)
                            continue
                    time.sleep(0.1)
                    continue
                
                consecutive_failures = 0
                opencv_error_count = 0
                
                try:
                    if not frame.data.contiguous:
                        frame = np.ascontiguousarray(frame)
                except Exception:
                    pass
                
                try:
                    with self.frame_lock:
                        self.last_frame = frame.copy()
                except cv2.error as e:
                    opencv_error_count += 1
                    time.sleep(0.1)
                    continue
                except Exception:
                    time.sleep(0.1)
                    continue
                
                try:
                    h, w = frame.shape[:2]
                    if h == 0 or w == 0:
                        time.sleep(0.1)
                        continue
                except (AttributeError, IndexError, TypeError):
                    time.sleep(0.1)
                    continue
                
                try:
                    display_frame = frame.copy()
                except cv2.error as e:
                    opencv_error_count += 1
                    time.sleep(0.1)
                    continue
                except Exception:
                    time.sleep(0.1)
                    continue
                
                self.frame_counter += 1
                
                if self.frame_counter % self.process_every_n_frame != 0:
                    continue
                
                if self.model is not None:
                    try:
                        if display_frame is None or display_frame.size == 0:
                            continue
                        
                        enhanced_frame = self._enhance_frame_for_detection(frame)
                            
                        results = self.model(enhanced_frame, verbose=False)
                        frame_height, frame_width = frame.shape[:2]
                        
                        for result in results:
                            if result.boxes is None:
                                continue
                            boxes = result.boxes
                            for box in boxes:
                                if box.xyxy is None or len(box.xyxy) == 0 or len(box.xyxy[0]) < 4:
                                    continue
                                class_id = int(box.cls[0])
                                confidence = float(box.conf[0])
                                if class_id == self.phone_class_id and confidence >= self.settings['confidence_threshold']:
                                    bx1, by1, bx2, by2 = map(float, box.xyxy[0])
                                    center_x = (bx1 + bx2) / 2.0
                                    center_y = (by1 + by2) / 2.0
                                    
                                    matched_zone = self.find_matching_zone(center_x, center_y, frame_width, frame_height)
                                    
                                    if matched_zone:
                                        try:
                                            frame_copy = frame.copy()
                                            self.trigger_throttled_notification(matched_zone, frame_copy, confidence)
                                        except cv2.error as copy_err:
                                            opencv_error_count += 1
                                        except Exception:
                                            pass
                                    elif len(self.roi_zones) > 0:
                                        continue
                                    else:
                                        roi = self.settings.get('roi_coordinates')
                                        allow = True
                                        if roi and isinstance(roi, (list, tuple)) and len(roi) == 4:
                                            try:
                                                x1f, y1f, x2f, y2f = [float(v) for v in roi]
                                            except Exception:
                                                x1f, y1f, x2f, y2f = 0.0, 0.0, 1.0, 1.0
                                            norm_cx = center_x / max(1, frame_width)

                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    
                                    x1 = max(0, min(x1, frame_width - 1))
                                    y1 = max(0, min(y1, frame_height - 1))
                                    x2 = max(0, min(x2, frame_width - 1))
                                    y2 = max(0, min(y2, frame_height - 1))
                                    
                                    if x2 > x1 and y2 > y1:
                                        try:
                                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                                            text_y = max(10, y1 - 10)
                                            label = f"Phone: {confidence:.2f}"
                                            if matched_zone:
                                                label += f" [{matched_zone}]"
                                            cv2.putText(display_frame, label, (x1, text_y),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                        except Exception:
                                            pass
                                    
                                if class_id == 0 and confidence >= 0.5:
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    
                                    x1 = max(0, min(x1, frame_width - 1))
                                    y1 = max(0, min(y1, frame_height - 1))
                                    x2 = max(0, min(x2, frame_width - 1))
                                    y2 = max(0, min(y2, frame_height - 1))
                                    
                                    if x2 > x1 and y2 > y1:
                                        try:
                                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                                            text_y = max(10, y1 - 10)
                                            cv2.putText(display_frame, f'Person: {confidence:.2f}', (x1, text_y),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                                        except Exception:
                                            pass
                    except Exception:
                        pass
                
            except cv2.error as e:
                opencv_error_count += 1
                if opencv_error_count >= 10:
                    opencv_error_count = 0
                    try:
                        if self.camera is not None:
                            self.camera.release()
                        time.sleep(2)
                        self.camera = self._open_capture(self.assigned_camera_index)
                        if self.camera is None or not self.camera.isOpened():
                            time.sleep(5)
                        else:
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    except Exception:
                        pass
                time.sleep(0.1)
                continue
            except Exception as e:
                import logging
                logging.error(f"Unexpected error in camera loop: {e}")
                time.sleep(1)
                continue
        
        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
        except Exception:
            pass

    def get_current_frame_bytes(self):
        """Return the latest captured frame encoded as JPEG bytes, or None if unavailable."""
        try:
            if self.last_frame is None:
                return None
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
            anonymization_model = None
            if hasattr(self, 'anonymizer_worker'):
                if self.anonymizer_worker.model is not None:
                    anonymization_model = self.anonymizer_worker.model
            
            if anonymization_model is None:
                return frame.copy()
            
            anonymized_frame = frame.copy()
            img_h, img_w = anonymized_frame.shape[:2]
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                temp_path = tmp.name
                cv2.imwrite(temp_path, frame)
            
            try:
                prediction = anonymization_model.predict(temp_path, confidence=40, overlap=30)
                results = prediction.json()
                
                predictions = results.get('predictions', [])
                
                heads_blurred = 0
                for det in predictions:
                    confidence = det.get('confidence', 0)
                    
                    if confidence >= 0.4:
                        center_x = int(det['x'])
                        center_y = int(det['y'])
                        width = int(det['width'])
                        height = int(det['height'])
                        
                        x1 = center_x - width // 2
                        y1 = center_y - height // 2
                        x2 = center_x + width // 2
                        y2 = center_y + height // 2
                        
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(img_w, x2), min(img_h, y2)
                        
                        if x2 <= x1 or y2 <= y1:
                            continue
                        
                        roi = anonymized_frame[y1:y2, x1:x2]
                        
                        if roi.size > 0:
                            blur = cv2.GaussianBlur(roi, (99, 99), 30)
                            anonymized_frame[y1:y2, x1:x2] = blur
                            heads_blurred += 1
            
            finally:
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
        cap = cv2.VideoCapture(index)
        if cap is not None and cap.isOpened():
            return cap
        try:
            cap.release()
        except Exception:
            pass

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
            for attempt in range(warmup_reads):
                ret, frame = cap.read()
                if ret and frame is not None:
                    frame_size = getattr(frame, 'size', 0)
                    if frame_size > 0:
                        try:
                            h, w = frame.shape[:2]
                            if h > 0 and w > 0:
                                return True
                        except (AttributeError, IndexError, TypeError):
                            pass
                if attempt < warmup_reads - 1:
                    time.sleep(delay_s)
        except Exception as e:
            print(f"    ⚠️ Exception in _capture_has_valid_frame_static: {e}")
        return False

    @staticmethod
    def _scan_available_cameras_static():
        """Statyczna metoda do skanowania kamer - wywoływana tylko raz przy starcie serwera."""
        available_cameras = []
        
        print("\n🔍 Starting camera scan...")
        
        all_camera_devices = []
        try:
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
        
        for index in range(16):
            cap = None
            try:
                print(f"  🔍 Attempting to open camera index {index}...")
                cap = CameraController._open_capture_static(index)
                if cap is None:
                    continue
                if not cap.isOpened():
                    try:
                        cap.release()
                    except:
                        pass
                    continue
            except Exception:
                pass
                import traceback
                traceback.print_exc()
                continue
            
            if cap is None or not cap.isOpened():
                continue
                
            if cap.isOpened():
                print(f"  📹 Testing camera index {index}...")
                
                try:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    if width == 0 or height == 0:
                        print(f"    ⚠️ Camera {index} opened but properties are 0x0, trying to read a frame...")
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            width = test_frame.shape[1] if len(test_frame.shape) > 1 else 0
                            height = test_frame.shape[0] if len(test_frame.shape) > 0 else 0
                        else:
                            width = 640
                            height = 480
                            print(f"    ⚠️ Using default resolution 640x480 for camera {index}")
                except Exception as e:
                    print(f"    ⚠️ Error getting camera properties: {e}, using defaults")
                    width = 640
                    height = 480
                    fps = 30
                
                has_valid_frame = False
                try:
                    has_valid_frame = CameraController._capture_has_valid_frame_static(cap, warmup_reads=3, delay_s=0.1)
                    if not has_valid_frame:
                        time.sleep(0.3)
                        has_valid_frame = CameraController._capture_has_valid_frame_static(cap, warmup_reads=5, delay_s=0.15)
                except Exception as e:
                    print(f"    ⚠️ Frame validation error (non-critical): {e}")
                
                if not has_valid_frame:
                    print(f"    ⚠️ Camera {index} cannot deliver valid frames yet, but will include it anyway (may work when actively used)")
                
                print(f"    ✅ Camera {index} is working! ({width}x{height} @ {fps} FPS)")
                
                name = f"Camera {index}"
                
                try:
                    try:
                        backend_name = cap.getBackendName()
                        print(f"    📷 Camera backend: {backend_name}")
                    except:
                        pass
                    
                    if len(all_camera_devices) > 0:
                        if index < len(all_camera_devices):
                            name = all_camera_devices[index]['name']
                            print(f"    ✅ Using name from pre-scanned device list: {name}")
                        else:
                            print(f"    ⚠️ Camera index {index} beyond pre-scanned list, trying PowerShell query...")
                    
                    if name == f"Camera {index}":
                        cmd = f"powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {{ $_.PNPClass -eq 'Camera' }} | Select-Object -Index {index} | Select-Object -ExpandProperty Name\""
                        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
                        if result.returncode == 0 and result.stdout.strip():
                            name = result.stdout.strip()
                            print(f"    ✅ Got name from Windows (Camera class): {name}")
                        else:
                            cmd = f"powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {{ $_.PNPClass -eq 'Image' }} | Select-Object -Index {index} | Select-Object -ExpandProperty Name\""
                            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
                            if result.returncode == 0 and result.stdout.strip():
                                name = result.stdout.strip()
                                print(f"    ✅ Got name from Windows (Image class): {name}")
                    
                    if "Iriun" not in name and "iriun" not in name.lower() and len(all_camera_devices) > 0:
                        for device in all_camera_devices:
                            if "Iriun" in device['name'] or "iriun" in device['name'].lower():
                                name = device['name']
                                print(f"    ✅ Found Iriun in device list: {name}")
                                break
                                
                except Exception as e:
                    print(f"    ⚠️ Warning: Could not get name for camera index {index}: {e}")
                
                if "Iriun" in name or "iriun" in name.lower():
                    name = "Iriun Webcam"
                    print(f"    ✅ Normalized to: Iriun Webcam")
                
                try:
                    cmd = f"powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object {{ $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' }} | Select-Object -Index {index} | Select-Object -Property Name, DeviceID, Manufacturer, Description, PNPClass | ConvertTo-Json\""
                    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        device_info = json.loads(result.stdout)
                        print(f"    📷 Device info: {device_info}")
                except Exception as e:
                    pass
                
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
            
            cmd = "powershell -Command \"Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | Select-Object Name, DeviceID, Manufacturer, Description, PNPClass | ConvertTo-Json\""
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Error getting camera list: {result.stderr}")
                available_cameras = self.get_available_cameras()
                for camera in available_cameras:
                    if camera_name.lower() in camera['name'].lower():
                        print(f"✅ Found camera '{camera_name}' at index {camera['index']} (via cached list)")
                        return camera['index']
                return None
            
            devices = json.loads(result.stdout)
            if not isinstance(devices, list):
                devices = [devices]
            
            print(f"Found {len(devices)} camera-like devices in Windows")
            current_index = 0
            for device in devices:
                device_name = device.get('Name', '')
                print(f"  Checking device {current_index}: {device_name} (Class: {device.get('PNPClass', 'Unknown')})")
                
                search_name = camera_name.lower()
                if "iriun" in search_name or "iriun" in device_name.lower():
                    if "iriun" in device_name.lower():
                        print(f"✅ Found Iriun Webcam at index {current_index}")
                        return current_index
                
                if search_name in device_name.lower() or device_name.lower() in search_name:
                    print(f"✅ Found camera '{camera_name}' at index {current_index}")
                    return current_index
                
                if "Camera" in device_name or "Image" in device.get('PNPClass', ''):
                    current_index += 1
            
            print("Camera not found by name, checking cached camera list...")
            available_cameras = self.get_available_cameras()
            for camera in available_cameras:
                if camera_name.lower() in camera['name'].lower() or "iriun" in camera_name.lower() and "iriun" in camera['name'].lower():
                    print(f"✅ Found camera '{camera_name}' at index {camera['index']} (via cached list)")
                    return camera['index']
            
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
        self.settings = settings
        self.blur_kernel_size = blur_kernel_size
        self.blur_sigma = blur_sigma
        self.is_running = True
        
        self.tasks_processed = 0
        self.persons_anonymized = 0
        
        self.model = yolo_model
        
        self.vonage_sms = vonage_sms
        self.vonage_api_key = os.getenv('VONAGE_API_KEY')
        self.vonage_api_secret = os.getenv('VONAGE_API_SECRET')
        self.vonage_from_number = os.getenv('VONAGE_FROM_NUMBER', 'PhoneDetection')
        self.vonage_to_number = os.getenv('VONAGE_TO_NUMBER')
        
        
        self.cloudinary_enabled = cloudinary_enabled
        
        self.email_user = email_user
        self.email_password = email_password
        self.email_recipient = email_recipient
        
        self.email_enabled = False
        self.sms_enabled = False
        self.settings_lock = threading.Lock()
        
        if settings:
            with self.settings_lock:
                self.email_enabled = settings.get('email_notifications', False)
                self.sms_enabled = settings.get('sms_notifications', False)
    
    def update_worker_settings(self, controller_instance):
        """
        Aktualizuje ustawienia powiadomień w locie (wywoływane z CameraController.update_settings).
        Przyjmuje instancję kontrolera, aby odczytać zaktualizowane wartości.
        """
        with self.settings_lock:
            self.email_enabled = controller_instance.email_enabled
            self.sms_enabled = controller_instance.sms_enabled
            
            self.settings['email_notifications'] = self.email_enabled
            self.settings['sms_notifications'] = self.sms_enabled
            if hasattr(controller_instance, 'camera_name'):
                self.settings['camera_name'] = controller_instance.camera_name
        
    
    def run(self):
        """Główna pętla workera - przetwarza zadania z kolejki"""
        
        while self.is_running:
            try:

                try:
                    task_data = self.detection_queue.get(timeout=1)
                except:
                    continue
                
                if task_data is None:

                    self.detection_queue.task_done()
                    break
                
                filepath = task_data.get('filepath')
                confidence = task_data.get('confidence', 0.0)
                zone_name = task_data.get('zone_name')

                should_blur = task_data.get('should_blur', True)
                
                print(f"🔄 Przetwarzanie: {filepath} (blur: {should_blur}, zone: {zone_name})")
                

                if should_blur:
                    success = self._anonymize_faces(filepath)
                    
                    if success:
                        print(f"✅ Zanonimizowano: {filepath}")
                        self.tasks_processed += 1
                    else:
                        import logging
                        logging.error(f"Anonymization error: {filepath}")
                else:

                    print(f"⏭️  Pomijam anonimizację (blur wyłączony): {filepath}")
                    self.tasks_processed += 1
                



                self._save_to_database(task_data)
                


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

                    notification_thread = threading.Thread(
                        target=self._handle_cloud_notification,
                        args=(filepath, confidence, zone_name),
                        daemon=True
                    )
                    notification_thread.start()
                
                self.detection_queue.task_done()
                
            except Exception as e:
                import logging
                logging.error(f"Error in AnonymizerWorker: {e}")
                try:
                    self.detection_queue.task_done()
                except:
                    pass
        
    
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
                import logging
                logging.error("Cloudinary not initialized")
                return None
            
            filename = os.path.basename(filepath)
            
            print(f"☁️  Wysyłanie {filename} na Cloudinary...")
            
            response = cloudinary.uploader.upload(
                filepath,
                folder="phone_detections",
                public_id=os.path.splitext(filename)[0],
                resource_type="image",
                overwrite=True
            )
            
            secure_url = response.get('secure_url')
            public_id = response.get('public_id')
            
            print(f"✅ Plik wysłany na Cloudinary: {public_id}")
            print(f"🔗 Link (publiczny): {secure_url}")
            
            return secure_url
            
        except Exception as e:
            import logging
            logging.error(f"Error uploading to Cloudinary: {e}")
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
                import logging
                logging.error("Vonage client not initialized")
                return False
            
            if not self.vonage_to_number:
                import logging
                logging.error("Missing destination number (VONAGE_TO_NUMBER) - cannot send SMS")
                return False
            

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            location = zone_name or self.settings.get('camera_name', 'Camera 1')
            
            if public_link:
                message_body = (
                    f"Phone Detection Alert!\n"
                    f"Time: {timestamp}\n"
                    f"Location: {location}\n"
                    f"Confidence: {confidence:.2%}\n"
                    f"Image: {public_link}\n"
                    f"---"
                )
            else:
                message_body = (
                    f"Phone Detection Alert!\n"
                    f"Time: {timestamp}\n"
                    f"Location: {location}\n"
                    f"Confidence: {confidence:.2%}\n"
                    f"(Image upload failed)\n"
                    f"---"
            )

            to_number = str(self.vonage_to_number).replace('+', '')
            
            print(f"📱 Wysyłanie SMS na +{to_number}...")
            
            sms_message = SmsMessage(
                to=to_number,
                from_=self.vonage_from_number,
                text=message_body
            )
            
            response = self.vonage_sms.send(sms_message)
            
            if response and hasattr(response, 'messages'):
                if response.messages[0].status == '0':
                    message_id = response.messages[0].message_id
                    print(f"✅ SMS wysłany: {message_id}")
                    return True
                else:
                    error = getattr(response.messages[0], 'error_text', 'Unknown error')
                    import logging
                    logging.error(f"Vonage error: {error}")
                    return False
            else:
                import logging
                logging.error(f"Invalid Vonage response: {response}")
                return False
            
        except Exception as e:
            import logging
            logging.error(f"Error sending SMS: {e}")
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

        if not all([self.email_user, self.email_password, self.email_recipient]):
            print("⚠️ Brak danych Email. Pomijam wysyłkę.")
            return False
        
        try:
            subject = f"Wykryto Telefon! ({location})"
            
            body_content = [
                "<b>Wykryto Telefon!</b>",
                "<hr>",
                f"<b>Lokalizacja:</b> {location}",
                 f"<b>Pewność detekcji:</b> {(confidence * 100):.1f}%",
                "<br>",
                "Zanonimizowany obraz (osadzony poniżej i w załączniku):",
                yagmail.inline(filepath)
            ]
            

            if public_link and public_link != "(Upload do Cloudinary nie powiódł się)":
                body_content.append(f'<br><a href="{public_link}">Link do obrazu w chmurze</a>')
            


            with yagmail.SMTP(self.email_user, self.email_password) as yag_client:
                yag_client.send(
                    to=self.email_recipient,
                    subject=subject,
                    contents=body_content,
                    attachments=filepath
                )

            
            print(f"✅ Pomyślnie wysłano e-mail (z osadzonym obrazem) do {self.email_recipient}")
            return True
            
        except smtplib.SMTPDataError as e:

            if e.smtp_code == 250:
                print(f"✅ E-mail prawdopodobnie wysłany (otrzymano kod 250 OK), ale wystąpił wyjątek: {e}")
                return True
            else:
                import logging
                logging.error(f"Critical email error (Yagmail SMTPDataError): {e}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:

            import logging
            logging.error(f"Critical email error (Yagmail): {e}")
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
            

            public_link = self._upload_to_cloudinary(filepath)
            

            with self.settings_lock:
                email_on = self.email_enabled
                sms_on = self.sms_enabled
            
            if public_link:
                print(f"✅ Plik wysłany na Cloudinary")
                

                if sms_on:
                    self._send_sms_notification(public_link, confidence, zone_name)
                
                if email_on:
                    location = zone_name or self.settings.get('camera_name', 'Camera 1')
                    self._send_email_notification(
                        public_link,
                        filepath,
                        confidence,
                        location
                    )
            else:
                if sms_on:
                    self._send_sms_notification(None, confidence, zone_name)
                
                if email_on:
                    location = zone_name or self.settings.get('camera_name', 'Camera 1')

                    self._send_email_notification(
                        "(Upload do Cloudinary nie powiódł się)",
                        filepath,
                        confidence,
                        location
                    )
                
        except Exception as e:
            import logging
            logging.error(f"Error in _handle_cloud_notification: {e}")
    
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

            if self.model is None:
                return True
            

            image = cv2.imread(image_path)
            if image is None:
                import logging
                logging.error(f"Cannot load: {image_path}")
                return False
            

            img_h, img_w = image.shape[:2]
            

            prediction = self.model.predict(image_path, confidence=40, overlap=30)
            results = prediction.json()
            
            heads_found = 0
            

            for det in results.get('predictions', []):
                confidence = det.get('confidence', 0)
                

                if confidence >= 0.4:
                    heads_found += 1
                    

                    center_x = int(det['x'])
                    center_y = int(det['y'])
                    width = int(det['width'])
                    height = int(det['height'])
                    

                    x1 = center_x - width // 2
                    y1 = center_y - height // 2
                    x2 = center_x + width // 2
                    y2 = center_y + height // 2
                    

                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(img_w, x2), min(img_h, y2)
                    

                    if x2 <= x1 or y2 <= y1:
                        print(f"⚠️  Nieprawidłowy ROI głowy: ({x1},{y1})-({x2},{y2}), pomijam")
                        continue
                    

                    roi = image[y1:y2, x1:x2]
                    

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
            

            success = cv2.imwrite(image_path, image)
            
            if not success:
                import logging
                logging.error(f"Failed to save: {image_path}")
                return False
            
            return True
            
        except Exception as e:
            import logging
            logging.error(f"Anonymization error: {e}")
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
                else:
                    import logging
                    logging.error("Admin user not found")
        except Exception as e:
            import logging
            logging.error(f"Database save error: {e}")
    
    def stop(self):
        """Zatrzymuje workera"""
        self.is_running = False


if __name__ == "__main__":
    cameras = CameraController._scan_available_cameras_static()
    for camera in cameras:
        print(f"Camera {camera['index']}: {camera['name']} ({camera['resolution']}, {camera['fps']} FPS)")