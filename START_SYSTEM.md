# 🚀 Quick Start - Phone Detection System
## How to Start Both Frontend and Backend

---

## ⚡ QUICK START (2 Terminals)

### Terminal 1: Flask Backend (Python)
```bash
# Navigate to project root
cd C:\Users\askik\Desktop\Phone_detection\Detection-phone

# Activate virtual environment (if you have one)
# venv\Scripts\activate

# Run Flask
python app.py
```

**Expected Output:**
```
✅ AnonymizerWorker uruchomiony w tle
Loading YOLO model...
YOLO model loaded successfully
Camera controller initialized
 * Running on http://localhost:5000
```

---

### Terminal 2: React Frontend (Node.js)
```bash
# Navigate to Detection-phone folder
cd C:\Users\askik\Desktop\Phone_detection\Detection-phone

# Start React dev server
npm start
```

**Expected Output:**
```
Compiled successfully!

You can now view phone-detection-system in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

---

## 🎯 Access the Application

1. **Open Browser:** `http://localhost:3000`
2. **Login Page:** Should load with dark theme
3. **Enter Credentials:** Use real database user (not `admin/admin123`)
4. **Dashboard:** Should load with real data from Flask

---

## ✅ Verification Steps

### 1. Check Flask is Running
- Terminal 1 should show: `Running on http://localhost:5000`
- No errors about camera or YOLO model

### 2. Check React is Running
- Terminal 2 should show: `Compiled successfully!`
- Browser opens automatically to `localhost:3000`

### 3. Test Login
- Enter username/password (must exist in database!)
- Press "Login" button
- Should redirect to Dashboard (not stay on login page)

### 4. Check Browser Console (F12)
Look for these messages:
```
✅ Login successful: {message: "Login successful"}
✅ Dashboard data loaded: {...}
```

### 5. Check Network Tab (F12 → Network → XHR)
Should see successful API calls:
- `POST /api/login` → 200 OK
- `GET /api/dashboard-stats` → 200 OK

---

## 🐛 Troubleshooting

### Problem: "Missing script: start"
**Solution:** You're in wrong directory
```bash
# Make sure you're in Detection-phone folder
cd C:\Users\askik\Desktop\Phone_detection\Detection-phone
pwd  # Should show: .../Phone_detection/Detection-phone
```

### Problem: "Cannot find module 'flask'"
**Solution:** Install Python dependencies
```bash
pip install -r requirements.txt
```

### Problem: "npm: command not found"
**Solution:** Install Node.js from https://nodejs.org/

### Problem: "CORS error" in browser
**Solution:** Make sure Flask has `CORS(app)` (it does - line 25 in app.py)

### Problem: Login fails with 401
**Solution:** User doesn't exist in database
```bash
# Create initial admin user
python init_db.py
```

### Problem: Dashboard shows "Failed to load"
**Cause:** Flask backend not running
**Solution:** Start Flask first (Terminal 1), then React (Terminal 2)

### Problem: "Camera Status: Offline"
**Normal:** Camera doesn't start automatically
**Solution:** Add camera start button (TODO in API_INTEGRATION_COMPLETE.md)

---

## 📊 What Should You See?

### Login Page ✨
- Dark theme (#0F172A background)
- Glassmorphism card
- Phone icon at top
- Username/password fields with icons
- Loading button animation

### Dashboard 📈
- 3 KPI cards (Total, Today, Camera Status)
- AreaChart (weekly detections)
- BarChart (detections by location)
- Table with recent detections
- Auto-refresh every 30 seconds

---

## 🔄 How to Stop

### Stop React (Terminal 2):
Press `Ctrl + C`

### Stop Flask (Terminal 1):
Press `Ctrl + C`

---

## 📝 Important Files

### Backend (Flask):
- `app.py` - Main Flask application
- `camera_controller.py` - Camera and YOLO logic
- `models.py` - Database models
- `requirements.txt` - Python dependencies

### Frontend (React):
- `src/App.tsx` - Main React app
- `src/services/api.ts` - API integration layer
- `src/pages/Dashboard.tsx` - Dashboard with real data
- `package.json` - Node dependencies

---

## 🎯 Next Steps

1. ✅ Start both servers
2. ✅ Login with real credentials
3. ✅ Verify Dashboard loads data
4. ⏳ Complete Detections page API integration
5. ⏳ Complete Settings page API integration
6. ⏳ Add camera start/stop UI controls

---

**Need more help?** Check `API_INTEGRATION_COMPLETE.md` for detailed documentation.

---

**Quick Reference:**
- Flask: `http://localhost:5000`
- React: `http://localhost:3000`
- Login: Real DB user required!
- Debug: Browser Console (F12)

