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

class CameraController:
    def __init__(self):
        self.camera = None
        self.is_running = False
        self.thread = None
        self.settings = {
            'camera_start_time': '00:00',
            'camera_end_time': '23:59',
            'blur_faces': True,
            'confidence_threshold': 0.4
        }
        self.detection_queue = Queue()
        
        # Initialize YOLO model
        try:
            print("Loading YOLO model...")
            self.model = YOLO('yolov8n.pt')
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

    def update_settings(self, settings):
        """Update camera settings and handle camera state"""
        print("\nUpdating camera settings...")
        print(f"Current settings: {self.settings}")
        print(f"New settings: {settings}")
        
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
            print("Initializing camera...")
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise Exception("Failed to open camera")
            
            self.is_running = True
            print("Camera started successfully")
            
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
                
                # Process frame with YOLO every 15 frames
                frame_count += 1
                if frame_count % 15 == 0 and self.model is not None:
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