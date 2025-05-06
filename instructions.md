# Phone Detection System User Manual

## System Requirements
- Python 3.8 or newer
- Web camera
- Internet access
- Operating System: Windows 10/11, Linux, macOS

## System Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Web Camera     │────▶│  YOLOv8 Model   │────▶│  Detection      │
│                 │     │                 │     │  Processing     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Admin Panel    │◀────│  Flask Server   │◀────│  Database       │
│  (Dashboard)    │     │                 │     │  (SQLite)       │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Google Drive   │◀────│  Notification   │◀────│  Scheduler      │
│  Storage        │     │  System         │     │  System         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Component Description:

1. **Input Layer**
   - Web Camera: Captures real-time video feed
   - YOLOv8 Model: Processes frames to detect phones
   - Detection Processing: Handles detection results

2. **Core System**
   - Flask Server: Main application server
   - Database (SQLite): Stores detections and settings
   - Admin Panel: Web interface for monitoring and control

3. **Output Layer**
   - Notification System:
     - SMS (Vonage)
     - Email
   - Google Drive Storage:
     - Organized folder structure
     - Automatic file management
   - Scheduler System:
     - Camera operation schedule
     - Notification timing

### Data Flow:
1. Camera captures video frame
2. YOLOv8 model processes frame
3. If phone detected:
   - Save detection to database
   - Upload image to Google Drive
   - Send notifications
   - Update dashboard
4. Repeat process

### System States:
1. **Active State**
   - Camera is on
   - Detection is running
   - Notifications are enabled

2. **Scheduled State**
   - Camera follows schedule
   - Notifications follow priority rules
   - System maintains logs

3. **Maintenance State**
   - System updates
   - Database cleanup
   - Log rotation

## Installation
1. Ensure Python 3.8 or newer is installed
2. Create a new directory for the project
3. Copy all project files to the directory
4. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Configure `.env` file with required environment variables:
   - VONAGE_API_KEY
   - VONAGE_API_SECRET
   - TEACHER_PHONE_NUMBER
6. Run the application:
   ```bash
   python app.py
   ```

## Configuration
### Camera Settings
1. Open the admin panel and log in
2. Go to the "Settings" tab
3. In the "Camera Schedule" section:
   - Select camera start time (24h format)
   - Select camera end time (24h format)
   - Click "Submit" to save settings
4. In the "Camera Options" section:
   - Enable/disable face blurring
   - Set detection confidence threshold (default 0.5)
   - Click "Save Changes"

### Interface Design
The system is designed with a modern and user-friendly interface:
1. Dashboard:
   - Clean, minimalist design
   - Responsive layout for different screen sizes
   - Intuitive navigation
   - Readable charts and statistics
   - Animated transitions between views

2. Settings Panel:
   - Clear configuration form
   - Interactive form elements
   - Instant input validation
   - Change confirmation notifications

3. Detections View:
   - Photo gallery of detections
   - Quick photo preview
   - Filtering and sorting options
   - Responsive photo grid

4. General Design Principles:
   - Consistent color scheme
   - Readable typography
   - Clear action buttons
   - User feedback
   - Smooth animations
   - Dark and light themes

### Notifications
1. Configure email notifications:
   - SMTP address
   - Port
   - Login credentials
   - Message template:
     ```
     Subject: Phone Usage Detected
     
     Dear Teacher,
     
     The system has detected phone usage on {date} at {time}.
     
     Detection details:
     - Location: {location}
     - Detection confidence: {confidence}%
     - Photo link: {photo_link}
     
     Best regards,
     Monitoring System
     ```

2. Configure SMS notifications:
   - Vonage API key
   - Phone number
   - SMS template:
     ```
     DETECTION: Phone detected on {date} at {time} in {location}.
     Photo link: {photo_link}
     ```
   - Date format: DD.MM.YYYY
   - Time format: HH:MM
   - Maximum SMS length: 160 characters
   - Automatic link shortening

3. Google Drive Integration:
   - API Configuration:
     1. Go to Google Cloud Console
     2. Create new project
     3. Enable Google Drive API
     4. Create service account
     5. Download credentials.json
     6. Place file in application root directory
   
   - Folder Structure:
     ```
     /Phone Detection
     ├── /{year}
     │   ├── /{month}
     │   │   ├── /{day}
     │   │   │   ├── phone_detected_{timestamp}.jpg
     │   │   │   └── metadata.json
     ```
   
   - metadata.json format:
     ```json
     {
       "timestamp": "YYYY-MM-DD HH:MM:SS",
       "location": "string",
       "confidence": float,
       "device_type": "string",
       "status": "string",
       "image_path": "string"
     }
     ```
   
   - Automatic file management:
     - Automatic folder structure creation
     - 30-day file retention
     - Automatic old file cleanup
     - Image compression before upload
     - Thumbnail generation

### Notification Management
1. Notification Priorities:
   - High: SMS + Email
   - Low: Email only

2. Notification Schedule:
   - Weekdays: all notifications
   - Weekends: high priority only
   - Night hours (22:00-6:00): high priority only

3. Notification Limits:
   - SMS: max 10 per day
   - Email: max 500 per day

4. Error Management:
   - Automatic retry mechanism
   - Error logging
   - Sending failure notifications
   - Daily notification status reports

## Usage
### Admin Panel
1. Log in using default credentials:
   - Username: admin
   - Password: admin123
2. Change default password after first login

### Monitoring
1. Dashboard shows:
   - Detection count
   - Camera status
   - Recent detections
   - Detection photos
   - Statistics

### Detection Management
1. Browse detections in "Detections" tab
2. You can:
   - View detection details
   - Delete detection
   - Download photo
   - View frame photo

## Troubleshooting
### Camera Issues
1. Check camera connection
2. Ensure camera is not used by another application
3. Check camera access permissions

### Notification Issues
1. Check notification configuration
2. Verify internet connection
3. Check application logs

### Database Issues
1. Check database file permissions
2. Verify database integrity
3. Create backup before repair

## Maintenance
### Regular Tasks
1. Clean old detections
2. Update YOLOv8 model
3. Check logs
4. Create backups

### Updates
1. Regularly update dependencies
2. Check for new YOLOv8 model versions
3. Update operating system

## Security
1. Regularly change passwords
2. Use strong passwords
3. Restrict admin panel access
4. Monitor logs for suspicious activity 