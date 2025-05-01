import threading
import time
from datetime import datetime, time as dt_time
import cv2
from ultralytics import YOLO
import os
from flask import current_app
from models import db, Detection

class CameraController:
    def __init__(self):
        self.camera = None
        self.is_running = False
        self.thread = None
        print("Initializing YOLO model...")
        # Load YOLO model with higher confidence threshold
        self.model = YOLO('yolov8n.pt')
        print("YOLO model loaded successfully")
        self.settings = {
            'camera_start_time': '00:00',
            'camera_end_time': '23:59',
            'blur_faces': True,
            'confidence_threshold': 0.4  # Increased confidence threshold
        }
        
        # COCO class names for reference
        self.class_names = self.model.names
        print("\nAvailable classes in model:")
        for class_id, class_name in self.class_names.items():
            print(f"- {class_id}: {class_name}")
        
        # Find the class IDs for phone and person
        self.phone_class_id = None
        self.person_class_id = None
        
        for class_id, class_name in self.class_names.items():
            if 'phone' in class_name.lower() or 'cell' in class_name.lower():
                self.phone_class_id = class_id
                print(f"\nFound phone class ID: {class_id} ({class_name})")
            elif 'person' in class_name.lower():
                self.person_class_id = class_id
                print(f"Found person class ID: {class_id} ({class_name})")
        
        if self.phone_class_id is None:
            print("\nWarning: Could not find phone class ID in model")
            # Fallback to common COCO class ID for cell phone
            self.phone_class_id = 67
            print(f"Using default phone class ID: {self.phone_class_id}")
        
        if self.person_class_id is None:
            print("\nWarning: Could not find person class ID in model")
            # Fallback to common COCO class ID for person
            self.person_class_id = 0
            print(f"Using default person class ID: {self.person_class_id}")

    def update_settings(self, settings):
        print("\nUpdating camera settings...")
        self.settings = settings
        print(f"New settings: {settings}")
        # If camera is running and new settings indicate it should be off, stop it
        if self.is_running and not self._is_within_schedule():
            print("Stopping camera due to schedule change")
            self.stop_camera()
        # If camera is not running and new settings indicate it should be on, start it
        elif not self.is_running and self._is_within_schedule():
            print("Starting camera due to schedule change")
            self.start_camera()

    def _is_within_schedule(self):
        current_time = datetime.now().time()
        start_time = datetime.strptime(self.settings['camera_start_time'], '%H:%M').time()
        end_time = datetime.strptime(self.settings['camera_end_time'], '%H:%M').time()
        
        is_within = False
        if start_time <= end_time:
            is_within = start_time <= current_time <= end_time
        else:  # Handles overnight schedule
            is_within = current_time >= start_time or current_time <= end_time
        
        print(f"\nSchedule check - Current: {current_time}, Start: {start_time}, End: {end_time}, Within schedule: {is_within}")
        return is_within

    def start_camera(self):
        if self.is_running:
            print("Camera is already running")
            return

        try:
            print("\nAttempting to start camera...")
            # First, try to release any existing camera handles
            if self.camera is not None:
                self.camera.release()
                self.camera = None
                time.sleep(1)  # Give the system time to release the camera

            # Try different camera backends
            backends = [
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_MSMF, "Media Foundation"),
                (cv2.CAP_ANY, "Default")
            ]

            for backend, backend_name in backends:
                print(f"\nTrying {backend_name} backend...")
                for camera_index in [0, 1, 2]:
                    print(f"Attempting to open camera {camera_index} with {backend_name}...")
                    try:
                        self.camera = cv2.VideoCapture(camera_index + backend)
                        if self.camera.isOpened():
                            # Test camera read with timeout
                            start_time = time.time()
                            while time.time() - start_time < 5:  # 5 second timeout
                                ret, frame = self.camera.read()
                                if ret and frame is not None and frame.size > 0:
                                    print(f"Successfully opened camera {camera_index} with {backend_name}")
                                    print(f"Frame size: {frame.shape}")
                                    
                                    # Set camera properties
                                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                    self.camera.set(cv2.CAP_PROP_FPS, 30)
                                    
                                    # Verify properties
                                    width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                                    height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                                    fps = self.camera.get(cv2.CAP_PROP_FPS)
                                    print(f"Camera properties - Width: {width}, Height: {height}, FPS: {fps}")
                                    
                                    # Additional test frames
                                    success_count = 0
                                    for _ in range(5):
                                        ret, frame = self.camera.read()
                                        if ret and frame is not None and frame.size > 0:
                                            success_count += 1
                                        time.sleep(0.1)
                                    
                                    if success_count >= 3:  # At least 3 successful frames
                                        print(f"Camera test successful - {success_count}/5 frames captured")
                                        self.is_running = True
                                        self.thread = threading.Thread(target=self._camera_loop)
                                        self.thread.daemon = True
                                        self.thread.start()
                                        print("Camera started successfully")
                                        return
                                    else:
                                        print(f"Camera test failed - only {success_count}/5 frames captured")
                                        self.camera.release()
                                        self.camera = None
                                        continue
                                
                                time.sleep(0.1)
                            
                            print(f"Timeout while testing camera {camera_index} with {backend_name}")
                            self.camera.release()
                            self.camera = None
                        else:
                            print(f"Failed to open camera {camera_index} with {backend_name}")
                            if self.camera is not None:
                                self.camera.release()
                                self.camera = None
                    except Exception as e:
                        print(f"Error with camera {camera_index} using {backend_name}: {str(e)}")
                        if self.camera is not None:
                            self.camera.release()
                            self.camera = None
                        time.sleep(1)

            # If we get here, no camera was successfully opened
            raise Exception("Failed to open any camera with any backend")

        except Exception as e:
            print(f"Error starting camera: {str(e)}")
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            self.is_running = False
            raise

    def stop_camera(self):
        print("\nStopping camera...")
        self.is_running = False
        
        # Ensure all OpenCV windows are closed
        cv2.destroyAllWindows()
        cv2.waitKey(1)  # Wait for windows to close
        
        # Release camera resources
        if self.camera is not None:
            try:
                # Set camera properties to minimum values to reduce power
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1)
                self.camera.set(cv2.CAP_PROP_FPS, 1)
                
                # Release the camera
                self.camera.release()
                self.camera = None
                
                # Force garbage collection
                import gc
                gc.collect()
            except Exception as e:
                print(f"Error releasing camera: {str(e)}")
        
        # Wait for thread to finish
        if self.thread is not None and self.thread != threading.current_thread():
            try:
                self.thread.join(timeout=2.0)
            except Exception as e:
                print(f"Error joining thread: {str(e)}")
            self.thread = None
        
        print("Camera stopped and resources released")

    def __del__(self):
        """Destructor to ensure camera is released when object is destroyed"""
        self.stop_camera()

    def _camera_loop(self):
        print("\nStarting camera loop...")
        frame_count = 0
        consecutive_failures = 0
        max_failures = 5
        last_successful_frame_time = time.time()

        try:
            while self.is_running:
                if not self._is_within_schedule():
                    print("Outside of scheduled time, stopping camera")
                    self.is_running = False
                    break

                try:
                    # Check if we've gone too long without a successful frame
                    if time.time() - last_successful_frame_time > 10:  # 10 second timeout
                        print("No successful frames for 10 seconds, restarting camera")
                        self.is_running = False
                        break

                    ret, frame = self.camera.read()
                    if not ret or frame is None or frame.size == 0:
                        consecutive_failures += 1
                        print(f"Failed to grab frame (attempt {consecutive_failures}/{max_failures})")
                        if consecutive_failures >= max_failures:
                            print("Too many consecutive failures, stopping camera")
                            self.is_running = False
                            break
                        time.sleep(1)  # Wait a bit before retrying
                        continue

                    consecutive_failures = 0  # Reset failure counter on successful frame
                    last_successful_frame_time = time.time()
                    frame_count += 1

                    # Process frame with YOLO every 15 frames (increased frequency)
                    if frame_count % 15 == 0:
                        try:
                            # Process frame with YOLO
                            results = self.model(frame, verbose=False)
                            
                            # Draw detections on frame
                            for result in results:
                                boxes = result.boxes
                                if len(boxes) > 0:
                                    print("\nDetected objects:")
                                    for box in boxes:
                                        class_id = int(box.cls[0])
                                        confidence = float(box.conf[0])
                                        class_name = self.class_names[class_id]
                                        
                                        # Only process phone and person detections
                                        if class_id in [self.phone_class_id, self.person_class_id]:
                                            print(f"- {class_name}: {confidence:.2f}")
                                            
                                            # Draw bounding box
                                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                                            color = (0, 255, 0) if class_id == self.phone_class_id else (255, 0, 0)
                                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                                            cv2.putText(frame, f"{class_name}: {confidence:.2f}", 
                                                      (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                                                      0.5, color, 2)
                                            
                                            # Handle phone detection
                                            if class_id == self.phone_class_id and confidence >= self.settings['confidence_threshold']:
                                                print(f"\nPhone detected with confidence: {confidence:.2f}")
                                                self._handle_detection(frame.copy(), confidence)
                                else:
                                    print("No objects detected in frame")

                        except Exception as e:
                            print(f"Error processing frame: {str(e)}")

                    # Display the frame
                    cv2.imshow('Phone Detection', frame)
                    
                    # Check for 'q' key press to quit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("Quit key pressed")
                        self.is_running = False
                        break

                except Exception as e:
                    print(f"Error in camera loop: {str(e)}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        print("Too many consecutive failures, stopping camera")
                        self.is_running = False
                        break

                time.sleep(0.1)  # Reduced delay for more responsive detection
        finally:
            # Ensure cleanup happens even if there's an error
            print("Cleaning up camera resources...")
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            cv2.destroyAllWindows()
            cv2.waitKey(1)  # Wait for windows to close

    def _handle_detection(self, frame, confidence):
        try:
            print("\nHandling phone detection...")
            # Save detection image
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"detections/{timestamp}.jpg"
            os.makedirs('detections', exist_ok=True)
            
            # Draw bounding box on frame before saving
            results = self.model(frame, verbose=False)
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    if int(box.cls[0]) == self.phone_class_id:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f"Phone: {confidence:.2f}", (x1, y1 - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.imwrite(filename, frame)
            print(f"Saved detection image: {filename}")

            # Create detection record
            with current_app.app_context():
                detection = Detection(
                    location='Camera 1',
                    confidence=confidence,
                    image_path=filename,
                    status='Pending'
                )
                db.session.add(detection)
                db.session.commit()
                print(f"Created detection record with ID: {detection.id}")
        except Exception as e:
            print(f"Error handling detection: {e}")

# Create a global instance
camera_controller = CameraController() 