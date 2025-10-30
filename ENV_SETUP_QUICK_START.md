# ⚡ Quick Start: SMS & Email Setup

**Time Required:** 15-20 minutes  
**Difficulty:** Easy

---

## 🎯 **What You Need**

To enable SMS and Email notifications, you need API keys from 3 services:

1. **Vonage** (for SMS) - FREE ($2 credit)
2. **Gmail** (for Email) - FREE (needs App Password)
3. **Cloudinary** (for image hosting) - FREE tier

---

## 📝 **Step 1: Create `.env` File**

### **Option A: Copy the Template (Recommended)**

```powershell
cd C:\Users\askik\Desktop\Phone_detection\Detection-phone
copy .env.example .env
notepad .env
```

### **Option B: Create Manually**

1. Open Notepad
2. Copy this content:

```env
# SMS Notifications (Vonage)
VONAGE_API_KEY=
VONAGE_API_SECRET=
VONAGE_FROM_NUMBER=PhoneDetection
VONAGE_TO_NUMBER=

# Email Notifications (Gmail)
GMAIL_USER=
GMAIL_APP_PASSWORD=
EMAIL_RECIPIENT=

# Cloudinary (Image Hosting)
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Flask
SECRET_KEY=dev-secret-key-change-in-production
```

3. Save as: `C:\Users\askik\Desktop\Phone_detection\Detection-phone\.env`
   - **Important:** Save as "All Files" (not .txt)

---

## 🔑 **Step 2: Get Vonage Keys (SMS) - 5 minutes**

### **2.1. Sign Up**
- Go to: https://dashboard.nexmo.com/sign-up
- Create account (you get $2 free = ~40 SMS)

### **2.2. Get Keys**
- After login: https://dashboard.nexmo.com/getting-started/sms
- Copy **API Key** and **API Secret**
- Paste into `.env`:

```env
VONAGE_API_KEY=abc123def456789
VONAGE_API_SECRET=xyz789uvw321qwerty
```

### **2.3. Set Your Phone Number**
Replace with YOUR phone number (country code + number, NO + sign):

```env
VONAGE_TO_NUMBER=48123456789  # Example for Poland
```

**Other countries:**
- USA: `1234567890`
- UK: `447123456789`
- Germany: `491234567890`

---

## 📧 **Step 3: Get Gmail App Password - 5 minutes**

### **3.1. Enable 2-Step Verification**
- Go to: https://myaccount.google.com/security
- Click "2-Step Verification" → Turn ON
- Follow setup wizard (verify with phone)

### **3.2. Generate App Password**
- Go to: https://myaccount.google.com/apppasswords
- Select:
  - **App:** Mail
  - **Device:** Windows Computer
- Click **Generate**
- Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### **3.3. Update `.env`**

```env
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
EMAIL_RECIPIENT=recipient@example.com
```

**Notes:**
- `GMAIL_USER` = your Gmail address
- `GMAIL_APP_PASSWORD` = the 16-char password you just generated
- `EMAIL_RECIPIENT` = who receives the notifications (can be same as GMAIL_USER)

---

## ☁️ **Step 4: Get Cloudinary Keys - 5 minutes**

### **4.1. Sign Up**
- Go to: https://cloudinary.com/users/register/free
- Create free account

### **4.2. Get Keys from Dashboard**
- After login, you'll see the Dashboard
- Look for "Account Details" section
- Copy these 3 values:
  - **Cloud Name**
  - **API Key**
  - **API Secret**

### **4.3. Update `.env`**

```env
CLOUDINARY_CLOUD_NAME=dxyj123abc
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz123
```

---

## ✅ **Step 5: Verify & Test**

### **5.1. Check `.env` File**

Your `.env` should look like this (with YOUR values):

```env
# SMS Notifications (Vonage)
VONAGE_API_KEY=abc123def456789
VONAGE_API_SECRET=xyz789uvw321qwerty
VONAGE_FROM_NUMBER=PhoneDetection
VONAGE_TO_NUMBER=48123456789

# Email Notifications (Gmail)
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
EMAIL_RECIPIENT=recipient@example.com

# Cloudinary (Image Hosting)
CLOUDINARY_CLOUD_NAME=dxyj123abc
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz123

# Flask
SECRET_KEY=dev-secret-key-change-in-production
```

### **5.2. Restart Flask**

```powershell
cd C:\Users\askik\Desktop\Phone_detection\Detection-phone
python app.py
```

**Look for these success messages:**

```
✅ Klient Vonage zainicjalizowany
✅ Cloudinary zainicjalizowany
✅ Dane Email zainicjalizowane (połączenie będzie tworzone przy wysyłce).
   Wysyłka z: your_email@gmail.com
   Odbiorca: recipient@example.com
```

**If you see warnings:**

```
⚠️ Brak danych Vonage w zmiennych środowiskowych
⚠️ Brak danych Cloudinary w zmiennych środowiskowych
⚠️ Brak danych Email w zmiennych środowiskowych (.env)
```

→ Check that `.env` file is in the correct directory and has no typos

### **5.3. Test in React App**

1. Open Settings: http://localhost:3000/settings
2. Enable **SMS Notifications** (switch ON)
3. Enable **Email Notifications** (switch ON)
4. Click **Save Settings**
5. Click **Start Camera**
6. Show a phone to the camera

**Expected:**
- SMS arrives on your phone (~5-10 seconds)
- Email arrives in your inbox (~5-10 seconds)
- Both contain image link or embedded image

---

## 🚨 **Troubleshooting**

### **SMS Not Working**

**Error: "❌ Brak danych Vonage w zmiennych środowiskowych"**
- Check `.env` has `VONAGE_API_KEY` and `VONAGE_API_SECRET`
- Restart Flask after editing `.env`

**Error: "❌ Błąd Vonage: Invalid phone number"**
- Remove + sign from phone number
- Ensure format: `48123456789` (country code + number)

**No SMS received but no errors:**
- Check Vonage balance: https://dashboard.nexmo.com/billing-and-payments/billing-overview
- Verify phone number is correct
- Check if SMS arrived (can take up to 30 seconds)

---

### **Email Not Working**

**Error: "⚠️ Brak danych Email w zmiennych środowiskowych (.env)"**
- Check `.env` has all 3 values: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_RECIPIENT`
- Restart Flask

**Error: "❌ SMTPAuthenticationError: Username and Password not accepted"**
- You're using regular password instead of App Password
- Re-generate App Password: https://myaccount.google.com/apppasswords
- Ensure 2-Step Verification is ON

**Email arrives but no image:**
- Check Cloudinary configuration
- Verify Cloudinary keys are correct

---

### **Cloudinary Not Working**

**Error: "❌ Błąd uploadu na Cloudinary: Authentication failed"**
- Check all 3 values in `.env`:
  - `CLOUDINARY_CLOUD_NAME`
  - `CLOUDINARY_API_KEY`
  - `CLOUDINARY_API_SECRET`
- Log in to Cloudinary dashboard and re-copy keys
- Restart Flask

---

## 📱 **Optional: Skip SMS/Email (Testing Only)**

If you just want to test the camera without notifications:

1. Open Settings
2. Leave **SMS** and **Email** switches OFF
3. Click **Save Settings**
4. Start Camera

Images will still be saved locally in `detections/` folder!

---

## ✅ **Success Checklist**

- [ ] `.env` file exists in `Detection-phone/` directory
- [ ] All API keys filled in (no empty values)
- [ ] Gmail App Password is 16 characters
- [ ] Phone number has NO + sign
- [ ] 2-Step Verification enabled on Google
- [ ] Flask restarted after creating `.env`
- [ ] Saw success messages in Flask logs
- [ ] Tested and received SMS
- [ ] Tested and received Email

---

**If all checked ✅ → Your system is fully operational! 🎉**

---

## 📞 **Still Having Issues?**

1. Check `COMPLETE_FIX_SUMMARY.md` for detailed documentation
2. Check Flask console for error messages
3. Check Browser console (F12) for frontend errors
4. Verify all 3 services (Vonage, Gmail, Cloudinary) accounts are active

---

**Estimated Total Cost:** $0/month (free tiers sufficient for testing)
- Vonage: $2 free credit = ~40 SMS
- Gmail: Free (unlimited emails)
- Cloudinary: Free tier = 25 GB storage

**Production Costs (if needed later):**
- Vonage: ~$0.05 per SMS
- Gmail: Free (or Google Workspace if needed)
- Cloudinary: ~$89/month for Pro (if you need more storage)

