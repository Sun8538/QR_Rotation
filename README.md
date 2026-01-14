# Smart Attendance Management System with real-time sync and QR rotation

A comprehensive web-based attendance management system built with Python Flask, featuring real-time QR code scanning, dynamic QR rotation, cloud synchronization, and real-time updates via WebSocket.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd python_attendance_system
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python run.py
   ```

5. **Open in browser:**
   - Main page: http://localhost:5000
   - Student login: http://localhost:5000/auth/student/login
   - Professor login: http://localhost:5000/auth/professor/login

### Test Credentials
| Role | Email | Password |
|------|-------|----------|
| Professor | professor@acem.ac.in | password123 |
| Student | student@acem.ac.in | password123 |

## ✨ Features

### For Professors
- ✅ Create and manage classes
- ✅ Start/stop attendance sessions
- ✅ Generate dynamic QR codes (rotate every 30 seconds)
- ✅ View real-time attendance
- ✅ Enroll students in classes
- ✅ Update attendance status
- ✅ View analytics and reports
- ✅ Complete sessions (auto-mark absent)
- ✅ Cancel sessions

### For Students
- ✅ View enrolled classes
- ✅ Scan QR codes to mark attendance
- ✅ View attendance history
- ✅ Receive notifications
- ✅ Track attendance rate per class
- ✅ Update profile

### Security Features
- 🔐 HMAC-SHA256 signed QR codes
- 🔐 30-second QR expiration
- 🔐 Nonce to prevent replay attacks
- 🔐 Device fingerprinting
- 🔐 IP address logging
- 🔐 Email domain restriction (@acem.ac.in)

## 📁 Project Structure

```
python_attendance_system/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── models.py             # SQLAlchemy database models
│   ├── routes/
│   │   ├── auth.py           # Authentication routes
│   │   ├── main.py           # Home and common pages
│   │   ├── student.py        # Student dashboard and features
│   │   ├── professor.py      # Professor dashboard and features
│   │   └── api.py            # API endpoints
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── main/
│   │   ├── student/
│   │   └── professor/
│   └── utils/
│       ├── qr_generator.py   # QR code generation & validation
│       ├── session_generator.py
│       └── seed_data.py      # Initial database data
├── config.py                 # Configuration settings
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
└── FEATURES_DOCUMENTATION.md # Complete feature documentation
```

## 🔧 Configuration

Edit `config.py` to modify:

```python
# QR Code settings
QR_EXPIRY_SECONDS = 30  # QR codes expire in 30 seconds
QR_ROTATION_INTERVAL = 30

# Email domain restriction
ALLOWED_EMAIL_DOMAIN = '@acem.ac.in'

# Attendance settings
LATE_THRESHOLD_MINUTES = 5  # Students marked late after 5 minutes
```

## 🎯 How It Works

### QR Code Attendance Flow:

1. **Professor starts session** → Dynamic QR code generated
2. **QR code displayed** → Rotates every 30 seconds
3. **Student scans QR** → Using phone camera or web scanner
4. **System validates** → Checks signature, expiration, enrollment
5. **Attendance recorded** → Present or Late (based on time)
6. **Professor ends session** → Absent students auto-marked

### QR Code Security:

```json
{
  "sessionId": "uuid-string",
  "timestamp": 1736697600000,
  "nonce": "random-16-byte-hex",
  "signature": "hmac-sha256-hex",
  "expiresAt": "2026-01-12T12:00:30Z"
}
```

## 📱 Supported Browsers

- Chrome (recommended)
- Firefox
- Safari
- Edge

Camera access required for QR scanning.

## 🤝 API Endpoints

### Authentication
- `POST /auth/login` - General login
- `POST /auth/student/register` - Student registration
- `POST /auth/professor/register` - Professor registration
- `GET /auth/logout` - Logout

### Student
- `GET /student/dashboard` - Dashboard
- `GET /student/classes` - Class list
- `GET /student/scan` - QR scanner
- `POST /student/scan/process` - Process scan
- `GET /student/attendance` - Attendance history

### Professor
- `GET /professor/dashboard` - Dashboard
- `GET /professor/classes` - Class list
- `POST /professor/classes/create` - Create class
- `GET /professor/sessions` - All sessions
- `POST /professor/sessions/<id>/activate` - Start session
- `POST /professor/sessions/<id>/complete` - End session

### API
- `GET /api/health` - System health check
- `GET /api/sessions/<id>/qr` - Get QR code
- `GET /api/sessions/<id>/attendance` - Get attendance

## 📄 Documentation

For complete feature documentation, see [FEATURES_DOCUMENTATION.md](./FEATURES_DOCUMENTATION.md)

## 🛠️ Development

### Database
SQLite database stored in `instance/attendance.db`

### Real-time Updates
Flask-SocketIO for WebSocket connections

### Templates
Jinja2 templates with Tailwind CSS styling

## 📝 License

This project is for educational purposes.

---

**Smart Attendance Management System** - Making attendance tracking modern, secure, and efficient.
