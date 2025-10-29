# Phone Detection System

A modern web application for detecting and managing phone usage in restricted areas.

## Features

- Real-time phone detection using YOLOv8
- Face blurring for privacy (anonymizes upper body)
- Modern, responsive web dashboard
- Detection history and management
- Configurable camera settings and schedules
- **Multiple notification channels:**
  - **Email** notifications with image attachment (via Yagmail)
  - **SMS** notifications with image link (via Vonage)
- Cloudinary integration for cloud image storage
- User authentication and authorization
- Offline processing queue for non-blocking detection

## Project Structure

```
src/
├── components/         # Reusable components
│   └── Layout.tsx     # Main layout with navigation
├── contexts/          # React contexts
│   └── AuthContext.tsx # Authentication context
├── pages/             # Page components
│   ├── Dashboard.tsx  # Main dashboard
│   ├── Detections.tsx # Detection management
│   ├── Settings.tsx   # System settings
│   └── Login.tsx      # Login page
└── App.tsx           # Main application component
```

## Requirements

- Node.js 14 or newer
- npm or yarn
- Python 3.8 or newer (for backend)
- Web camera
- Internet access

## Installation

1. Clone the repository
2. Install frontend dependencies:
   ```bash
   npm install
   ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `.env` file
5. Start the development server:
   ```bash
   npm start
   ```

## Configuration

The system can be configured through the Settings page:

- Camera schedule (start/end time)
- Face blurring (privacy protection)
- Detection confidence threshold
- Notification channels (Email, SMS)
- Camera selection

### Notification Setup

For detailed setup instructions:
- **Email Notifications**: See [EMAIL_NOTIFICATIONS_SETUP.md](EMAIL_NOTIFICATIONS_SETUP.md)
- **SMS Notifications**: See [SMS_NOTIFICATIONS_SETUP.md](SMS_NOTIFICATIONS_SETUP.md)

### Environment Variables

Create a `.env` file in the project root:

```env
# Email Configuration
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
EMAIL_RECIPIENT=recipient@example.com

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# SMS Configuration (Optional)
VONAGE_API_KEY=your_vonage_key
VONAGE_API_SECRET=your_vonage_secret
VONAGE_FROM_NUMBER=PhoneDetection
VONAGE_TO_NUMBER=48123456789
```

## Development

### Frontend

- React with TypeScript
- Material-UI for components
- React Router for navigation
- Recharts for data visualization

### Backend

- Flask server with SQLAlchemy ORM
- SQLite database
- YOLOv8 for phone and person detection
- Cloudinary for image hosting
- Vonage API for SMS notifications
- Yagmail for email notifications
- Threaded processing for non-blocking operations

## Security

- JWT authentication
- Secure password storage
- API key management
- HTTPS support

## License

MIT License 