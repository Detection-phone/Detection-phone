# SMS Notifications Setup Guide

This document explains how to configure SMS notifications for the Phone Detection System.

## Overview

The system uses:
- **Twilio** for sending SMS notifications
- **Google Drive API** for uploading detection images
- SMS notifications are triggered when a phone is detected and the "SMS Notifications" toggle is enabled in the web panel

## Architecture

When a phone is detected:
1. The original image is saved locally
2. If face blurring is enabled, the `AnonymizerWorker` anonymizes the image
3. The detection is saved to the database
4. **If SMS notifications are enabled**, the system:
   - Uploads the image to Google Drive (in a separate thread to avoid blocking)
   - Sets the file permissions to public (anyone with link can view)
   - Sends an SMS via Twilio with the public link and detection details

## Prerequisites

### 1. Twilio Account Setup

1. Create a Twilio account at [https://www.twilio.com/](https://www.twilio.com/)
2. Get a phone number from Twilio console
3. Note down your credentials:
   - Account SID
   - Auth Token
   - Your Twilio phone number (from number)
   - Your personal phone number (to number)

### 2. Google Drive API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API for your project
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Create a new service account
   - Download the JSON key file
   - Rename it to `service_account.json`
   - Place it in the `Detection-phone` directory
5. (Optional) Create a dedicated folder on Google Drive:
   - Create a new folder in your Google Drive
   - Share the folder with the service account email (found in `service_account.json`)
   - Note the folder ID from the URL (e.g., `https://drive.google.com/drive/folders/FOLDER_ID_HERE`)

## Configuration

### Environment Variables

Create a `.env` file in the `Detection-phone` directory with the following variables:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
TWILIO_TO_NUMBER=+0987654321

# Google Drive Configuration (optional - if not set, files go to root)
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
```

### File Structure

Ensure you have:
```
Detection-phone/
├── camera_controller.py
├── service_account.json    # Google Drive service account credentials
├── .env                     # Environment variables (create this)
└── ...
```

## Installation

Install required packages:

```bash
pip install -r requirements.txt
```

The `requirements.txt` file already includes:
- `twilio==9.0.0`
- `google-api-python-client==2.118.0`
- `google-auth-httplib2==0.2.0`
- `google-auth-oauthlib==1.2.0`

## Usage

### Enable SMS Notifications

1. Start the Flask application (`python app.py`)
2. Log in to the web panel
3. Go to Settings
4. Enable the **"SMS Notifications"** toggle
5. Save settings

### How It Works

When a phone is detected:

1. **Detection Phase**:
   - Camera captures frame with phone
   - Original image saved to `detections/` directory
   - Detection added to processing queue

2. **Anonymization Phase** (if enabled):
   - `AnonymizerWorker` processes the image
   - Detects persons using YOLOv8
   - Blurs upper body (head and shoulders)
   - Saves anonymized image

3. **Notification Phase** (if SMS enabled):
   - **In a separate thread** (non-blocking):
     - Uploads image to Google Drive
     - Sets public permissions
     - Sends SMS with link and details

4. **Database Phase**:
   - Detection saved to database
   - Image path stored for web panel viewing

### SMS Message Format

The SMS notification contains:
```
⚠️ Phone Detection Alert!
Time: 2025-10-28 14:30:45
Location: Camera 1
Confidence: 85.50%
Image: https://drive.google.com/file/d/...
```

## Troubleshooting

### SMS Not Sending

Check the console output for error messages:
- `⚠️ Brak danych Twilio w zmiennych środowiskowych` - Missing Twilio credentials in `.env`
- `❌ Klient Twilio nie jest zainicjalizowany` - Twilio client failed to initialize
- `❌ Błąd wysyłania SMS: ...` - Error sending SMS (check Twilio account balance, phone numbers format)

### Google Drive Upload Failing

Check the console output:
- `⚠️ Brak pliku service_account.json` - Service account file not found
- `❌ Google Drive API nie jest zainicjalizowane` - Drive API failed to initialize
- `❌ Błąd wysyłania na Google Drive: ...` - Upload error (check service account permissions)

### Verification Steps

When the application starts, you should see:
```
✅ YOLOv8 zainicjalizowany dla anonimizacji
✅ Klient Twilio zainicjalizowany
✅ Google Drive API zainicjalizowane
✅ AnonymizerWorker uruchomiony w tle
```

If you see warnings (⚠️) instead, check your configuration.

## Security Notes

1. **Never commit** `.env` or `service_account.json` to version control
2. Add them to `.gitignore`:
   ```
   .env
   service_account.json
   ```
3. Keep your Twilio credentials secure
4. Images uploaded to Google Drive are set to public (anyone with link can view)
5. Consider setting up a dedicated Google Drive folder with access restrictions

## Performance

- SMS notifications run in a **separate thread** to avoid blocking the main detection loop
- Image upload typically takes 2-5 seconds depending on file size and internet speed
- Main camera loop continues uninterrupted during notification sending
- Failed notifications are logged but don't stop the detection system

## Cost Considerations

- **Twilio**: SMS costs vary by country (typically $0.0075-$0.10 per SMS)
- **Google Drive API**: Free tier includes 1GB storage and 750MB/day upload quota
- Monitor your usage to avoid unexpected costs

## Testing

To test the SMS notification system:

1. Ensure all credentials are configured
2. Enable SMS notifications in settings
3. Trigger a phone detection (hold phone in front of camera)
4. Check console output for:
   ```
   📲 SMS notifications włączone - uruchamiam wysyłkę w tle
   ☁️ Wysyłanie ... na Google Drive...
   ✅ Plik wysłany na Drive: ...
   🔓 Ustawiono uprawnienia publiczne
   📱 Wysyłanie SMS na ...
   ✅ SMS wysłany: ...
   ```
5. Check your phone for the SMS message

## Support

For issues:
- Twilio: [https://www.twilio.com/docs](https://www.twilio.com/docs)
- Google Drive API: [https://developers.google.com/drive](https://developers.google.com/drive)
- Check application logs for detailed error messages

