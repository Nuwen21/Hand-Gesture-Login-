# Hand Gesture Biometric Authentication System

A two-factor biometric authentication system combining a **master password** with a **3-step hand gesture sequence** (`0`–`5` raised fingers) captured in real time via webcam.

Built in two versions within one repository:
1. **Serverless Web Portal** — Neumorphic UI + MediaPipe JS + WebCrypto (`PBKDF2-HMAC-SHA256`) + Firebase Cloud Firestore (with automatic local browser demo fallback), ready for **GitHub Pages**, **Vercel**, or **Netlify**.
2. **Python Desktop & Flask Apps** — CustomTkinter GUI, terminal CLI, and local Flask server backed by OpenCV, MediaPipe Python, and SQLite.

> **Live Demo:** `https://<your-username>.github.io/<your-repo-name>/` *(update after enabling GitHub Pages)*

---

## Features

- **Two-Factor Biometric Flow:** Verifies both a text password and a sequential 3-gesture biometric key (e.g., `5 -> 0 -> 2`).
- **Real-Time Hand Tracking:** Counts raised fingers (`0`–`5`) via MediaPipe Hands in the browser (`@mediapipe/hands`) or Python (`mediapipe` + `opencv-python`).
- **Cryptographic Hashing:**
  - **Web Portal:** WebCrypto `PBKDF2-HMAC-SHA256` with `100,000` iterations and a 16-byte random salt.
  - **Python Apps:** `hashlib.pbkdf2_hmac("sha256")` with `150,000` iterations and a 16-byte random salt (`os.urandom(16)`).
- **Brute-Force Lockout:** 3 consecutive failed attempts trigger a 30-second temporary account lockout.
- **Security Audit Logs:** Records `REGISTERED`, `SUCCESS`, and `FAILED` events with timestamps and reasons.
- **Zero-Backend Hosting Option:** Runs 100% client-side on GitHub Pages/Vercel using Firebase Firestore or local browser fallback mode.

---

## Hand Gesture Key Reference

| Value | Gesture |
| :---: | :--- |
| `0` | Fist (0 fingers) |
| `1` | One Finger |
| `2` | Two Fingers |
| `3` | Three Fingers |
| `4` | Four Fingers |
| `5` | Open Palm (5 fingers) |

---

## Hosting the Web Portal (Recommended)

> **Note:** Browser webcam access requires **HTTPS** (provided automatically by GitHub Pages, Vercel, and Netlify) or `localhost`.

### Option 1: GitHub Pages
1. Upload the project files to your GitHub repository with `index.html` at the root.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
4. Select `main` and `/ (root)`, then click **Save**.

### Option 2: Vercel / Netlify
1. Import your GitHub repository into **Vercel** or **Netlify**.
2. Deploy as a static site (no build command required, output directory `.`).

### Optional: Connect Firebase Cloud Firestore
Without Firebase configured, the portal automatically runs in **Local Demo Mode** using browser storage. To enable cloud persistence across devices:
1. Create a project at [Firebase Console](https://console.firebase.google.com/) and create a **Firestore Database**.
2. Register a Web app (`</>`) and copy your Firebase config JSON.
3. Either click the **Cloud: Local Demo Mode** pill in the web UI and paste your config, or update `DEFAULT_FIREBASE_CONFIG` in `firebase-config.js`.

---

## Running Locally (Python Versions)

### Prerequisites
- Python 3.10+
- A working webcam

### Installation
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 1. Desktop GUI (CustomTkinter)
```bash
python app.py
```

### 2. Terminal CLI
```bash
python app_cli.py
```

### 3. Local Flask Web Server
```bash
python web_app/app.py
```
Then open `http://localhost:5001` in your browser.

---

## Project Structure

```text
.
├── index.html              # Web Portal entry point (GitHub Pages / Vercel root)
├── style.css               # Neumorphic UI styling
├── script.js               # MediaPipe JS hand tracking & authentication flow
├── firebase-config.js      # WebCrypto PBKDF2 hashing & Firebase Firestore service
├── bg.png                  # Background artwork
├── app.py                  # Desktop GUI launcher
├── app_gui.py              # CustomTkinter desktop interface
├── app_cli.py              # Terminal CLI version
├── gesture_detector.py     # OpenCV + MediaPipe finger counting engine
├── database.py             # SQLite user, lockout, and audit log storage
├── security.py             # PBKDF2-HMAC-SHA256 hashing & verification
├── requirements.txt        # Python dependencies
└── web_app/                # Local Flask + SQLite web server version
    ├── app.py
    ├── database.py
    ├── security.py
    ├── templates/index.html
    └── static/
```
