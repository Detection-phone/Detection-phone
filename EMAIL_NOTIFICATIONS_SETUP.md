# Email Notifications Setup Guide

This document explains how to configure email notifications for the Phone Detection System using **Yagmail**.

## Overview

The system uses:
- **Yagmail** for sending email notifications
- **Cloudinary** for hosting detection images (shared with SMS notifications)
- Email notifications are triggered when a phone is detected and the "Email Notifications" toggle is enabled in the web panel

## Architecture

When a phone is detected and email notifications are enabled:
1. The original image is saved locally
2. If face blurring is enabled, the `AnonymizerWorker` anonymizes the image
3. The detection is saved to the database
4. **If email notifications are enabled**, the system:
   - Uploads the image to Cloudinary (if not already uploaded for SMS)
   - Sends an email via Yagmail with:
     - Detection details (confidence, location, timestamp)
     - Public link to the image on Cloudinary
     - The image file as an attachment

## Prerequisites

### 1. Gmail Account Setup

For Yagmail to work with Gmail, you need to create an **App Password** (not your regular Gmail password):

1. Go to your Google Account settings: [https://myaccount.google.com/](https://myaccount.google.com/)
2. Navigate to **Security** section
3. Enable **2-Step Verification** (if not already enabled)
4. Go to **App passwords** (search for it in the security section)
5. Generate a new App Password:
   - Select app: "Mail"
   - Select device: "Other" (custom name, e.g., "Phone Detection")
   - Click "Generate"
6. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
7. Store it securely - you'll need it for configuration

> **Note**: Regular Gmail passwords won't work. You MUST use an App Password.

### 2. Cloudinary Account Setup (if not already configured)

If you haven't set up Cloudinary for SMS notifications:

1. Create a free account at [https://cloudinary.com/](https://cloudinary.com/)
2. Go to your Dashboard
3. Note down your credentials:
   - Cloud Name
   - API Key
   - API Secret

## Configuration

### Environment Variables

Create or update your `.env` file in the `Detection-phone` directory with the following variables:

```env
# Email Configuration (Yagmail)
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-character App Password from Gmail
EMAIL_RECIPIENT=recipient@example.com  # Where to send notifications

# Cloudinary Configuration (for image hosting)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### Configuration Example

Here's a complete example `.env` file with email notifications:

```env
# Email Notifications
GMAIL_USER=myemail@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
EMAIL_RECIPIENT=phone-alerts@mycompany.com

# Cloudinary
CLOUDINARY_CLOUD_NAME=mycloud
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz123456

# SMS Notifications (Vonage) - Optional
VONAGE_API_KEY=your_vonage_key
VONAGE_API_SECRET=your_vonage_secret
VONAGE_FROM_NUMBER=PhoneDetection
VONAGE_TO_NUMBER=48123456789
```

### File Structure

Ensure you have:
```
Detection-phone/
├── camera_controller.py
├── .env                     # Environment variables (create this)
├── requirements.txt
└── ...
```

## Installation

### Install Yagmail

Add Yagmail to your Python environment:

```bash
pip install yagmail
```

Or update your `requirements.txt` to include:
```
yagmail==0.15.293
```

Then install all dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Enable Email Notifications

1. Start the Flask application (`python app.py`)
2. Log in to the web panel
3. Go to **Settings**
4. Enable the **"Email Notifications"** toggle
5. Save settings

### How It Works

When a phone is detected and email notifications are enabled:

1. **Detection Phase**:
   - Camera captures frame with phone
   - Original image saved to `detections/` directory
   - Detection added to processing queue

2. **Anonymization Phase** (if enabled):
   - `AnonymizerWorker` processes the image
   - Detects persons using YOLOv8
   - Blurs upper body (head and shoulders)
   - Saves anonymized image

3. **Notification Phase** (if email enabled):
   - **In a separate thread** (non-blocking):
     - Uploads image to Cloudinary (if not already uploaded)
     - Sends email with:
       - Subject: "Phone Detection Alert! (Camera 1)"
       - Body with detection details
       - Cloudinary link to image
       - Image file as attachment

4. **Database Phase**:
   - Detection saved to database
   - Image path stored for web panel viewing

### Email Message Format

The email notification contains:

**Subject**: `Phone Detection Alert! (Camera 1)`

**Body** (Professional HTML format):
- 📧 **Header**: "Wykryto Telefon!" (czerwony nagłówek)
- 📍 **Lokalizacja**: Nazwa kamery
- 📊 **Pewność detekcji**: Procentowa wartość confidence
- 🔵 **Przycisk**: "Zobacz Zdjęcie" (niebieski przycisk z linkiem do Cloudinary)
- 📎 **Notatka**: Informacja o załączniku

**Attachment**: The detection image file (JPG)

#### Wygląd e-maila:
```
╔════════════════════════════════════╗
║  Wykryto Telefon!                  ║
║  ──────────────────────────────   ║
║  Lokalizacja: Camera 1             ║
║  Pewność detekcji: 85.5%           ║
║                                    ║
║  [Zobacz Zdjęcie] (niebieski btn)  ║
║                                    ║
║  Zdjęcie jest również w załączniku.║
╚════════════════════════════════════╝
```

**Format**: Responsywny HTML z inline CSS (działa w każdym kliencie email)

## Troubleshooting

### Email Not Sending

Check the console output for error messages:

#### Common Issues

**`❌ Błąd inicjalizacji Yagmail: ...`**
- Check that `GMAIL_USER` and `GMAIL_APP_PASSWORD` are set in `.env`
- Verify you're using an **App Password**, not your regular Gmail password
- Ensure 2-Step Verification is enabled on your Gmail account

**`⚠️ Klient Yagmail nie jest skonfigurowany. Pomijam e-mail.`**
- Yagmail failed to initialize during startup
- Check credentials in `.env` file
- Look for initialization errors in the startup logs

**`❌ Błąd wysyłania e-mail (Yagmail): SMTPAuthenticationError`**
- Invalid Gmail credentials
- You must use an App Password, not your regular password
- Verify the App Password is copied correctly (no spaces in the `.env` file)

**`❌ Błąd wysyłania e-mail (Yagmail): SMTPException`**
- Gmail might be blocking the login attempt
- Check [https://myaccount.google.com/security](https://myaccount.google.com/security) for security alerts
- Ensure "Allow less secure apps" is NOT needed (App Passwords bypass this)

### Cloudinary Upload Failing

If the image doesn't upload to Cloudinary (email will still be sent with attachment):

- `⚠️ Brak danych Cloudinary w zmiennych środowiskowych`
  - Missing Cloudinary credentials in `.env`
- `❌ Błąd wysyłania na Cloudinary: ...`
  - Check Cloudinary credentials are correct
  - Verify internet connectivity
  - Check Cloudinary account status and quotas

### Verification Steps

When the application starts, you should see:
```
✅ YOLOv8 zainicjalizowany dla anonimizacji
✅ Klient Vonage zainicjalizowany (if SMS configured)
✅ Cloudinary zainicjalizowane
   Cloud Name: your_cloud_name
✅ Klient Yagmail (Email) zainicjalizowany.
   Wysyłka z: your_email@gmail.com
   Odbiorca: recipient@example.com
✅ AnonymizerWorker uruchomiony w tle
```

If you see warnings (⚠️) instead, check your configuration.

### Testing Email Notifications

To test the email notification system:

1. Ensure all credentials are configured in `.env`
2. Restart the application to load new environment variables
3. Enable email notifications in settings
4. Trigger a phone detection (hold phone in front of camera)
5. Check console output for:
   ```
   📧 Email notifications włączone - wysyłanie...
   📧 Inicjalizacja Yagmail (Email)...
   ✅ Klient Yagmail (Email) zainicjalizowany.
   ✅ Pomyślnie wysłano e-mail do recipient@example.com
   ```
6. Check the recipient's inbox for the email

## Security Notes

1. **Never commit** `.env` to version control
2. Add it to `.gitignore`:
   ```
   .env
   service_account.json
   *.pyc
   __pycache__/
   ```
3. Keep your Gmail App Password secure
4. App Passwords provide limited access (only for the specific app)
5. You can revoke App Passwords at any time from Google Account settings
6. Images uploaded to Cloudinary are publicly accessible via URL
7. Consider using a dedicated Gmail account for notifications (not your personal email)

## Multiple Notification Channels

You can enable both SMS and Email notifications simultaneously:

- **SMS**: Instant notification with link (via Vonage)
- **Email**: Detailed notification with both link and attachment (via Yagmail)

Both use the same Cloudinary upload, so no duplicate uploads occur.

### Console Output Example (Both Enabled)

```
📲 SMS notifications włączone - uruchamiam wysyłkę w tle
🚀 Rozpoczynam wysyłkę powiadomienia dla: detections/phone_20251029_143045.jpg
☁️ Wysyłanie phone_20251029_143045.jpg na Cloudinary...
✅ Plik wysłany na Cloudinary: phone_detections/phone_20251029_143045
🔗 Link (publiczny): https://res.cloudinary.com/...
📱 Wysyłanie SMS na 48123456789...
✅ SMS wysłany: 1234567890abcdef
📧 Email notifications włączone - wysyłanie...
✅ Pomyślnie wysłano e-mail do recipient@example.com
```

## Performance

- Email notifications run in a **separate thread** to avoid blocking the main detection loop
- Email sending typically takes 1-3 seconds
- Image upload to Cloudinary (shared with SMS) takes 2-5 seconds
- Main camera loop continues uninterrupted during notification sending
- Failed notifications are logged but don't stop the detection system

## Cost Considerations

- **Yagmail/Gmail**: Free for personal use
- **Gmail limits**: 
  - 500 emails per day for free Gmail accounts
  - 2000 emails per day for Google Workspace accounts
- **Cloudinary**: Free tier includes:
  - 25 GB storage
  - 25 GB bandwidth per month
  - 25,000 transformations per month
- Monitor your usage to avoid unexpected costs

## Advanced Configuration

### Custom Email Sender Name

To customize the sender name, you can modify the initialization in `camera_controller.py`:

```python
self.yag_client = yagmail.SMTP(
    user=self.email_user,
    password=self.email_password,
    smtp_server='smtp.gmail.com'
)
```

### HTML Emails

Yagmail supports HTML emails. You can modify `_send_email_notification` to use HTML formatting:

```python
body = f"""
<html>
<body>
    <h2>Phone Detection Alert!</h2>
    <p><strong>Wykryto telefon z pewnością {confidence:.1f}%</strong></p>
    <p>Lokalizacja: {location}</p>
    <p><a href="{public_link}">Zobacz obraz w chmurze</a></p>
    <p>Obraz również dołączony jako załącznik.</p>
</body>
</html>
"""
```

### Multiple Recipients

To send to multiple email addresses:

```env
EMAIL_RECIPIENT=recipient1@example.com,recipient2@example.com,recipient3@example.com
```

Then modify the code to split recipients:

```python
recipients = self.email_recipient.split(',')
self.yag_client.send(to=recipients, ...)
```

## Troubleshooting Gmail App Passwords

If you can't find App Passwords:

1. **2-Step Verification Required**: You MUST enable 2-Step Verification first
2. **Direct Link**: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. **Not Available**: If you don't see this option:
   - You might be using a Google Workspace account (contact your admin)
   - Your account might have security restrictions
   - Try using a different Gmail account

### Alternative: Less Secure Apps (NOT RECOMMENDED)

If you absolutely cannot use App Passwords:

1. Enable "Less secure app access" (deprecated by Google)
2. Use your regular Gmail password
3. **This is NOT recommended** for security reasons

## Support

For issues:
- **Yagmail**: [https://github.com/kootenpv/yagmail](https://github.com/kootenpv/yagmail)
- **Gmail App Passwords**: [https://support.google.com/accounts/answer/185833](https://support.google.com/accounts/answer/185833)
- **Cloudinary**: [https://cloudinary.com/documentation](https://cloudinary.com/documentation)
- Check application logs for detailed error messages

## Summary

✅ **Email notifications integrated successfully!**

Key points:
- Uses Gmail + Yagmail for reliable email delivery
- Sends both link (Cloudinary) and attachment
- Runs in background thread (non-blocking)
- Works alongside SMS notifications
- Easy to configure with `.env` file
- Free for personal use (Gmail limits apply)

