# Phone Detection System

A modern web application for detecting and managing phone usage in restricted areas.

## Features

- Real-time phone detection using YOLOv8
- Modern, responsive dashboard
- Detection history and management
- Configurable camera settings
- Multiple notification channels (Email, SMS, Telegram)
- Google Drive integration for storage
- User authentication and authorization

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

- Camera schedule
- Face blurring
- Detection confidence threshold
- Notification channels
- Storage settings

## Development

### Frontend

- React with TypeScript
- Material-UI for components
- React Router for navigation
- Recharts for data visualization

### Backend

- Flask server
- SQLite database
- YOLOv8 for detection
- Google Drive API integration
- Vonage API for SMS

## Security

- JWT authentication
- Secure password storage
- API key management
- HTTPS support

## License

MIT License 