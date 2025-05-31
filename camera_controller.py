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
            'blur_faces': True,
            'confidence_threshold': 0.2,
            'camera_index': self.camera_index,
            'camera_name': camera_name
        }
        self.detection_queue = Queue()
        
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

    def _verify_camera(self):
        """Verify if the selected camera is available and working"""
        print(f"\nVerifying camera with index {self.camera_index}...")
        try:
            cap = cv2.VideoCapture(self.camera_index)
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
        
        # Update settings
        self.settings.update(settings)
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
            self.camera = cv2.VideoCapture(self.camera_index)
            if not self.camera.isOpened():
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
        try:
            # Create detections directory if it doesn't exist
            os.makedirs('detections', exist_ok=True)
            
            # Save image
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'phone_{timestamp}.jpg'  # Only filename
            filepath = os.path.join('detections', filename)
            success = cv2.imwrite(filepath, frame)
            if not success:
                raise Exception("Failed to save detection image")
            print(f"Saved detection image: {filepath}")
            
            # Add detection to queue instead of direct database access
            detection_data = {
                'filename': filename,  # Only filename
                'confidence': confidence,
                'timestamp': timestamp
            }
            self.detection_queue.put(detection_data)
        except Exception as e:
            print(f"Error handling detection: {e}")
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)

    def process_detection_queue(self):
        """Process the detection queue and save to database"""
        while not self.detection_queue.empty():
            try:
                detection_data = self.detection_queue.get()
                from app import app
                with app.app_context():
                    try:
                        admin_user = User.query.filter_by(username='admin').first()
                        if admin_user:
                            detection = Detection(
                                location='Camera 1',
                                confidence=detection_data['confidence'],
                                image_path=detection_data['filename'],  # Only filename
                                status='Pending',
                                user_id=admin_user.id
                            )
                            db.session.add(detection)
                            db.session.commit()
                            print(f"Created detection record with ID: {detection.id}")
                        else:
                            print("Error: Admin user not found")
                            if os.path.exists(os.path.join('detections', detection_data['filename'])):
                                os.remove(os.path.join('detections', detection_data['filename']))
                    except Exception as e:
                        print(f"Database error: {e}")
                        if os.path.exists(os.path.join('detections', detection_data['filename'])):
                            os.remove(os.path.join('detections', detection_data['filename']))
            except Exception as e:
                print(f"Error processing detection queue: {e}")
            finally:
                self.detection_queue.task_done()

    def _camera_loop(self):
        """Main camera loop for capturing and processing frames"""
        print("Starting camera loop...")
        frame_count = 0
        
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
                if not ret or frame is None:
                    print("Error reading frame")
                    time.sleep(1)
                    continue
                
                # Blur faces if enabled
                if self.settings.get('blur_faces', False):
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                    for (x, y, w, h) in faces:
                        face_roi = frame[y:y+h, x:x+w]
                        face_roi = cv2.GaussianBlur(face_roi, (99, 99), 30)
                        frame[y:y+h, x:x+w] = face_roi
                
                # Run detection every 5 frames
                frame_count += 1
                if frame_count % 5 == 0 and self.model is not None:
                    try:
                        results = self.model(frame, verbose=False)
                        for result in results:
                            boxes = result.boxes
                            for box in boxes:
                                class_id = int(box.cls[0])
                                confidence = float(box.conf[0])
                                if class_id == self.phone_class_id and confidence >= self.settings['confidence_threshold']:
                                    print(f"Phone detected with confidence: {confidence}")
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                    cv2.putText(frame, f"Phone: {confidence:.2f}", (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                                    self._handle_detection(frame.copy(), confidence)
                                # Draw bounding box for person
                                if class_id == 0 and confidence >= 0.5:  # 0 is 'person' in COCO
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                                    cv2.putText(frame, f'Person: {confidence:.2f}', (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    except Exception as e:
                        print(f"Error processing frame with YOLO: {e}")
                
                # Display frame
                cv2.imshow('Phone Detection', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # Process detection queue periodically
                self.process_detection_queue()
                
            except Exception as e:
                print(f"Error in camera loop: {e}")
                time.sleep(1)
        
        print("Camera loop ended")

    def __del__(self):
        self.stop_camera()

    @staticmethod
    def scan_available_cameras():
        """Scan and list all available camera devices and their indices"""
        available_cameras = []
        
        # Try to open cameras with indices 0-9
        for index in range(10):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
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

# TODO: Implement dynamic camera detection by name
# For Windows:
# - Use Media Foundation API to enumerate video devices
# - Example: https://docs.microsoft.com/en-us/windows/win32/medfound/enumerating-video-capture-devices
# - Could use pygrabber or similar library to access Media Foundation
#
# For Linux:
# - Use v4l2-ctl to list video devices
# - Example: v4l2-ctl --list-devices
# - Could parse output to find device by name
#
# Implementation could be added as a new method:
# def find_camera_by_name(self, camera_name):
#     """Find camera index by device name"""
#     pass 

# Przykład użycia:
cameras = CameraController.scan_available_cameras()
for camera in cameras:
    print(f"Camera {camera['index']}: {camera['name']} ({camera['resolution']}, {camera['fps']} FPS)") 