import requests
import sys

try:
    response = requests.get('http://localhost:5000/api/camera/status', timeout=2)
    if response.status_code in [200, 401]:
        print("✅ Flask działa na porcie 5000!")
        sys.exit(0)
    else:
        print(f"⚠️ Flask odpowiada, ale status: {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("❌ Flask NIE działa na porcie 5000")
    print("   Uruchom: python app.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ Błąd: {e}")
    sys.exit(1)

