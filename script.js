// ==========================================
// APP NAVIGATION & PANEL MANAGEMENT
// ==========================================
const panels = ["welcome-screen", "register-screen", "login-screen", "camera-screen", "logs-screen", "alert-screen"];

function showPanel(panelId) {
    panels.forEach(p => {
        const el = document.getElementById(p);
        if (p === panelId) {
            el.classList.add("active");
        } else {
            el.classList.remove("active");
        }
    });
}

// Global Variables
let appMode = ""; // "REGISTER" or "LOGIN"
let currentUsername = "";
let currentPassword = ""; // Only used during registration session

// Gesture States
const SEQUENCE_LENGTH = 3;
let capturedSequence = [];
let currentGesture = null;
let gestureStartTime = 0;
let lockedGesture = null;

// Camera and MediaPipe variables
let webcamStream = null;
let mpCamera = null;
let handsDetector = null;

// Gesture naming map
const GESTURE_NAMES = {
    0: "Fist",
    1: "One Finger",
    2: "Two Fingers",
    3: "Three Fingers",
    4: "Four Fingers",
    5: "Open Palm"
};

// ==========================================
// A. EVENT INITIALIZATION
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    // Menu navigation
    document.getElementById("btn-show-login").addEventListener("click", () => {
        showPanel("login-screen");
    });
    document.getElementById("btn-show-register").addEventListener("click", () => {
        showPanel("register-screen");
    });
    document.getElementById("btn-show-logs").addEventListener("click", () => {
        showPanel("logs-screen");
        loadLogs();
    });
    
    // Back buttons
    document.querySelectorAll(".btn-to-welcome").forEach(btn => {
        btn.addEventListener("click", () => {
            stopCamera();
            showPanel("welcome-screen");
        });
    });

    // Forms Submission
    document.getElementById("btn-submit-register").addEventListener("click", handleRegisterForm);
    document.getElementById("btn-submit-login").addEventListener("click", handleLoginForm);
    
    // HUD Cancel Button
    document.getElementById("btn-cancel-scan").addEventListener("click", () => {
        stopCamera();
        if (appMode === "REGISTER") {
            showPanel("register-screen");
        } else {
            authRepository.logEvent(currentUsername, "FAILED", "cancelled during gesture scan");
            showPanel("login-screen");
        }
    });

    // Alert Actions Complete
    document.getElementById("btn-alert-done").addEventListener("click", () => {
        showPanel("welcome-screen");
    });

    // Logs refresh
    document.getElementById("btn-refresh-logs").addEventListener("click", loadLogs);

    // Initialize bottom-right live date & time widget
    initClock();

    // Firebase Cloud Config Modal Handlers
    initCloudModal();
});

function initClock() {
    function updateClock() {
        const now = new Date();
        const timeEl = document.getElementById("clock-time");
        const dateEl = document.getElementById("clock-date");
        if (timeEl && dateEl) {
            timeEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
            dateEl.textContent = now.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
        }
    }
    updateClock();
    setInterval(updateClock, 1000);
}

function initCloudModal() {
    const pill = document.getElementById("cloud-status-pill");
    const modal = document.getElementById("firebase-modal");
    const closeBtn = document.getElementById("btn-close-modal");
    const saveBtn = document.getElementById("btn-save-firebase");
    const resetBtn = document.getElementById("btn-reset-firebase");
    const textarea = document.getElementById("firebase-config-input");

    if (pill && modal) {
        pill.addEventListener("click", () => {
            modal.classList.add("active");
            const stored = localStorage.getItem("firebase_config");
            if (stored) {
                textarea.value = JSON.stringify(JSON.parse(stored), null, 2);
            }
        });

        closeBtn.addEventListener("click", () => {
            modal.classList.remove("active");
        });

        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.classList.remove("active");
        });

        saveBtn.addEventListener("click", () => {
            const val = textarea.value.trim();
            try {
                let parsed;
                if (val.startsWith("{") && val.endsWith("}")) {
                    parsed = JSON.parse(val);
                } else if (val.includes("{") && val.includes("}")) {
                    const jsonPart = val.substring(val.indexOf("{"), val.lastIndexOf("}") + 1);
                    parsed = JSON.parse(jsonPart);
                } else {
                    throw new Error("Invalid format");
                }
                localStorage.setItem("firebase_config", JSON.stringify(parsed));
                alert("Firebase configuration saved! Reloading to connect...");
                location.reload();
            } catch (err) {
                alert("Please paste a valid Firebase configuration JSON object.");
            }
        });

        resetBtn.addEventListener("click", () => {
            localStorage.removeItem("firebase_config");
            alert("Reset to local fallback mode. Reloading...");
            location.reload();
        });
    }
}

// ==========================================
// B. FORM HANDLERS (Client-Side & Firebase)
// ==========================================
async function handleRegisterForm() {
    const errorEl = document.getElementById("reg-error");
    errorEl.textContent = "";

    const username = document.getElementById("reg-username").value.trim();
    const password = document.getElementById("reg-password").value;
    const confirm = document.getElementById("reg-confirm").value;

    if (!username) {
        errorEl.textContent = "Username cannot be empty.";
        return;
    }
    if (!password) {
        errorEl.textContent = "Password cannot be empty.";
        return;
    }
    if (password !== confirm) {
        errorEl.textContent = "Passwords do not match.";
        return;
    }

    try {
        // Check if user already exists
        const userKey = username.toLowerCase();
        let exists = false;
        if (isFirebaseConnected && db) {
            const doc = await db.collection("users").doc(userKey).get();
            exists = doc.exists;
        } else {
            const users = localStore.getUsers();
            exists = !!users[userKey];
        }

        if (exists) {
            errorEl.textContent = "Username already exists.";
            return;
        }

        // Cache details and start Camera Screen
        appMode = "REGISTER";
        currentUsername = username;
        currentPassword = password;
        
        startCameraScreen();
    } catch (e) {
        console.error("Register form check error:", e);
        errorEl.textContent = "System error checking username availability.";
    }
}

async function handleLoginForm() {
    const errorEl = document.getElementById("login-error");
    errorEl.textContent = "";

    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;

    if (!username || !password) {
        errorEl.textContent = "Please fill in all fields.";
        return;
    }

    try {
        // Validate password hash using WebCrypto & Firestore/localStorage
        const res = await authRepository.verifyPassword(username, password);
        
        if (!res.success) {
            errorEl.textContent = res.message || "Incorrect username or password.";
            return;
        }

        // Access password match! Start gesture scan screen
        appMode = "LOGIN";
        currentUsername = username;
        currentPassword = ""; // Clear password cache for security
        
        startCameraScreen();
    } catch (e) {
        console.error("Login form error:", e);
        errorEl.textContent = "Authentication communication failure.";
    }
}

// ==========================================
// C. CAMERA & GESTURE CORE ENGINE
// ==========================================
function startCameraScreen() {
    // Reset scanner states
    capturedSequence = [];
    currentGesture = null;
    gestureStartTime = 0;
    lockedGesture = null;
    
    // Update headers
    document.getElementById("camera-loading").style.display = "block";
    document.getElementById("gesture-progress").style.width = "0%";
    
    if (appMode === "REGISTER") {
        document.getElementById("camera-title").textContent = `Register Gestures for ${currentUsername}`;
        document.getElementById("camera-subtitle").textContent = "Perform 3 unique gestures in sequence.";
    } else {
        document.getElementById("camera-title").textContent = `Gesture Verification: ${currentUsername}`;
        document.getElementById("camera-subtitle").textContent = "Perform your saved 3-gesture sequence.";
    }
    
    updateHUDSequence();
    showPanel("camera-screen");
    
    // Start camera stream and MediaPipe Hands
    initMediaPipe();
}

function initMediaPipe() {
    const videoElement = document.getElementById("webcam");
    const canvasElement = document.getElementById("output-canvas");
    const canvasCtx = canvasElement.getContext("2d");
    const loadingOverlay = document.getElementById("camera-loading");

    // Initialize Hands object
    handsDetector = new Hands({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
    });

    handsDetector.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.7
    });

    // Callback on results
    handsDetector.onResults((results) => {
        // Clear loading screen
        if (loadingOverlay.style.display !== "none") {
            loadingOverlay.style.display = "none";
        }

        // Draw flipped mirror image to canvas
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        
        // Flip canvas context horizontally
        canvasCtx.translate(canvasElement.width, 0);
        canvasCtx.scale(-1, 1);
        canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);

        let detected = null;

        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
            const landmarks = results.multiHandLandmarks[0];
            
            // Draw MediaPipe Landmarks (mirrored on canvas)
            drawConnectors(canvasCtx, landmarks, HAND_CONNECTIONS, { color: '#00FF00', lineWidth: 4 });
            drawLandmarks(canvasCtx, landmarks, { color: '#FF0000', lineWidth: 2, radius: 4 });

            // Count raised fingers logic
            detected = countFingers(landmarks);
        }

        canvasCtx.restore();

        // Process Hold-to-Confirm logic
        handleHoldGesture(detected);
    });

    // Setup Camera stream via CameraUtils
    mpCamera = new Camera(videoElement, {
        onFrame: async () => {
            if (handsDetector) {
                await handsDetector.send({ image: videoElement });
            }
        },
        width: 640,
        height: 480
    });

    mpCamera.start().then(() => {
        webcamStream = videoElement.srcObject;
    }).catch(err => {
        loadingOverlay.textContent = "Camera Access Denied or Unavailable.";
    });
}

// Finger Counting Algorithm (Matches Python OpenCV/MediaPipe detector)
function countFingers(landmarks) {
    let fingers = 0;
    
    // MediaPipe Hand Landmark IDs
    // Thumb: 4, Index: 8, Middle: 12, Ring: 16, Pinky: 20
    const tipIds = [8, 12, 16, 20];
    
    // Check 4 fingers (Y-axis: top of screen is Y=0)
    for (const tip of tipIds) {
        if (landmarks[tip].y < landmarks[tip - 2].y) {
            fingers++;
        }
    }
    
    // Thumb calculation based on handedness/horizontal spacing
    // If Thumb tip is to the left/right of MCP joint
    // Approximate: distance comparison between tip(4) and pinky base(17) vs IP(3) and pinky base(17)
    const thumbDistTip = Math.hypot(landmarks[4].x - landmarks[17].x, landmarks[4].y - landmarks[17].y);
    const thumbDistIP = Math.hypot(landmarks[3].x - landmarks[17].x, landmarks[3].y - landmarks[17].y);
    
    if (thumbDistTip > thumbDistIP * 1.15) {
        fingers++;
    }
    
    return fingers;
}

// Gesture Stability & Capture Timing
function handleHoldGesture(gesture) {
    const progressBar = document.getElementById("gesture-progress");
    const descText = document.getElementById("hud-gesture-desc");
    
    if (gesture === null) {
        // Hand not detected
        currentGesture = null;
        gestureStartTime = 0;
        progressBar.style.width = "0%";
        descText.textContent = "Show your hand to the camera";
        return;
    }

    if (gesture !== currentGesture) {
        currentGesture = gesture;
        gestureStartTime = Date.now();
        progressBar.style.width = "0%";
        descText.textContent = `Holding: ${GESTURE_NAMES[gesture] || gesture}`;
    } else {
        const elapsed = Date.now() - gestureStartTime;
        const requiredHold = 1100; // 1.1 seconds hold
        const pct = Math.min(100, Math.floor((elapsed / requiredHold) * 100));
        progressBar.style.width = `${pct}%`;

        if (elapsed >= requiredHold) {
            // Check for immediate duplicate in sequence
            if (capturedSequence.length > 0 && capturedSequence[capturedSequence.length - 1] === currentGesture) {
                descText.textContent = `Change gesture! (${GESTURE_NAMES[currentGesture]} already captured)`;
                return;
            }

            // Capture successfully!
            capturedSequence.push(currentGesture);
            gestureStartTime = Date.now() + 600; // Grace cooldown period
            progressBar.style.width = "0%";
            updateHUDSequence();
            
            if (capturedSequence.length === SEQUENCE_LENGTH) {
                // Short wait to show final box filled before executing callback
                setTimeout(handleGestureSequenceComplete, 400);
            }
        }
    }
}

function updateHUDSequence() {
    for (let i = 0; i < SEQUENCE_LENGTH; i++) {
        const el = document.getElementById(`seq-${i}`);
        if (i < capturedSequence.length) {
            const val = capturedSequence[i];
            el.textContent = GESTURE_NAMES[val] || val;
            el.classList.add("active");
        } else {
            el.textContent = "Empty";
            el.classList.remove("active");
        }
    }
}

function stopCamera() {
    if (mpCamera) {
        mpCamera.stop();
        mpCamera = null;
    }
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    if (handsDetector) {
        handsDetector.close();
        handsDetector = null;
    }
    
    // Clear canvas
    const canvasElement = document.getElementById("output-canvas");
    if (canvasElement) {
        const canvasCtx = canvasElement.getContext("2d");
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    }
}

// ==========================================
// D. SEQUENCE COMPLETE WITH FIREBASE & WEBCRYPTO
// ==========================================
async function handleGestureSequenceComplete() {
    stopCamera();
    
    const seqStr = capturedSequence.join("-");
    const alertCard = document.getElementById("alert-card-container");
    const alertIcon = document.getElementById("alert-icon-graphic");
    const alertTitle = document.getElementById("alert-title");
    const alertMsg = document.getElementById("alert-message");
    
    const successIconSvg = `<div class="alert-icon-inner success-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg></div>`;
    const errorIconSvg = `<div class="alert-icon-inner danger-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></div>`;

    if (appMode === "REGISTER") {
        try {
            // Register user in Cloud Firestore / localStore with PBKDF2 hash
            const res = await authRepository.registerUser(currentUsername, currentPassword, seqStr);
            currentPassword = ""; // Clear password from memory for security

            if (res.success) {
                alertIcon.innerHTML = successIconSvg;
                alertTitle.textContent = "User Registered Successfully";
                alertMsg.textContent = `Account for '${currentUsername}' created. Master password and hand gesture key sequence stored securely.`;
                alertCard.classList.add("success-border");
                alertTitle.classList.add("success-text");
            } else {
                alertIcon.innerHTML = errorIconSvg;
                alertTitle.textContent = "Registration Failed";
                alertMsg.textContent = res.message || "Failed to create account.";
                alertCard.classList.add("danger-border");
                alertTitle.classList.add("danger-text");
            }
        } catch (e) {
            console.error("Registration error:", e);
            alertIcon.innerHTML = errorIconSvg;
            alertTitle.textContent = "Server Error";
            alertMsg.textContent = "Failed to store registration credentials.";
            alertCard.classList.add("danger-border");
            alertTitle.classList.add("danger-text");
        }
    } else {
        // AppMode is LOGIN
        try {
            // Verify gesture sequence with PBKDF2 hash
            const res = await authRepository.verifyGesture(currentUsername, seqStr);

            if (res.success) {
                alertIcon.innerHTML = successIconSvg;
                alertTitle.textContent = "Access Granted";
                alertMsg.textContent = `Welcome back, ${currentUsername}! Identity verified successfully.`;
                alertCard.classList.add("success-border");
                alertTitle.classList.add("success-text");
            } else {
                alertIcon.innerHTML = errorIconSvg;
                alertTitle.textContent = "Access Denied";
                
                if (res.locked) {
                    alertMsg.textContent = `Incorrect gesture sequence. Your account has been temporarily LOCKED for ${res.lock_remaining}s due to repeated failures.`;
                } else {
                    alertMsg.textContent = res.message || "Gesture credentials do not match.";
                }
                
                alertCard.classList.add("danger-border");
                alertTitle.classList.add("danger-text");
            }
        } catch (e) {
            console.error("Login verification error:", e);
            alertIcon.innerHTML = errorIconSvg;
            alertTitle.textContent = "Verification Error";
            alertMsg.textContent = "System failure during gesture verification.";
            alertCard.classList.add("danger-border");
            alertTitle.classList.add("danger-text");
        }
    }
    
    showPanel("alert-screen");
}

// ==========================================
// E. AUDIT LOGS DISPLAY
// ==========================================
async function loadLogs() {
    const tableBody = document.getElementById("logs-table-body");
    tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center;">Retrieving audit logs...</td></tr>`;

    try {
        const logs = await authRepository.getLogs(30);
        tableBody.innerHTML = "";
        
        if (!logs || logs.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center;">No logs found in database.</td></tr>`;
            return;
        }

        logs.forEach(log => {
            const tr = document.createElement("tr");
            
            const tdTime = document.createElement("td");
            tdTime.textContent = log.created_at;
            
            const tdUser = document.createElement("td");
            tdUser.textContent = log.username;
            
            const tdStatus = document.createElement("td");
            tdStatus.textContent = log.status;
            // Style based on success status
            if (log.status === "SUCCESS" || log.status === "REGISTERED") {
                tdStatus.style.color = "#10b981";
                tdStatus.style.fontWeight = "bold";
            } else if (log.status === "FAILED") {
                tdStatus.style.color = "#ef4444";
                tdStatus.style.fontWeight = "bold";
            }
            
            const tdReason = document.createElement("td");
            tdReason.textContent = log.reason;
            
            tr.appendChild(tdTime);
            tr.appendChild(tdUser);
            tr.appendChild(tdStatus);
            tr.appendChild(tdReason);
            tableBody.appendChild(tr);
        });
    } catch (e) {
        console.error("Logs load error:", e);
        tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#ef4444;">Failed to fetch audit logs.</td></tr>`;
    }
}
