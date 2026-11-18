/**
 * Firebase Cloud Firestore Configuration & Authentication Service
 * 100% Client-Side Biometric Gesture Authentication for GitHub Pages
 */

// Default configuration placeholder
// You can paste your Firebase credentials here OR paste them into the "Cloud Config" modal in the UI!
const DEFAULT_FIREBASE_CONFIG = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_SENDER_ID",
    appId: "YOUR_APP_ID"
};

let db = null;
let isFirebaseConnected = false;

// Initialize Firebase
function initFirebase() {
    // Check localStorage for saved custom config first, then fallback to DEFAULT_FIREBASE_CONFIG
    let config = null;
    const stored = localStorage.getItem("firebase_config");
    if (stored) {
        try {
            config = JSON.parse(stored);
        } catch (e) {
            console.error("Failed to parse stored firebase config:", e);
        }
    }
    if (!config || !config.apiKey || config.apiKey === "YOUR_API_KEY") {
        config = DEFAULT_FIREBASE_CONFIG;
    }

    if (config && config.apiKey && config.apiKey !== "YOUR_API_KEY") {
        try {
            if (!firebase.apps.length) {
                firebase.initializeApp(config);
            }
            db = firebase.firestore();
            isFirebaseConnected = true;
            console.log("Firebase Cloud Firestore connected successfully.");
        } catch (e) {
            console.error("Firebase init failed, switching to local fallback:", e);
            isFirebaseConnected = false;
        }
    } else {
        isFirebaseConnected = false;
    }

    updateCloudIndicator();
}

function updateCloudIndicator() {
    const pill = document.getElementById("cloud-status-pill");
    const label = document.getElementById("cloud-status-label");
    const dot = document.getElementById("cloud-status-dot");
    if (pill && label && dot) {
        if (isFirebaseConnected) {
            label.textContent = "Cloud: Firestore Active";
            dot.className = "cloud-dot connected";
            pill.title = "Connected to Firebase Cloud Firestore";
        } else {
            label.textContent = "Cloud: Local Demo Mode";
            dot.className = "cloud-dot local";
            pill.title = "Click to configure your Firebase project credentials";
        }
    }
}

/* =========================================================
   CRYPTOGRAPHY ENGINE (PBKDF2-HMAC-SHA256 via WebCrypto)
   100,000 iterations + Salt (Identical to security.py)
   ========================================================= */

const cryptoService = {
    async hashSecret(secret, saltHex = null) {
        const enc = new TextEncoder();
        let salt;
        if (saltHex) {
            salt = new Uint8Array(saltHex.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
        } else {
            salt = window.crypto.getRandomValues(new Uint8Array(16));
            saltHex = Array.from(salt).map(b => b.toString(16).padStart(2, '0')).join('');
        }

        const keyMaterial = await window.crypto.subtle.importKey(
            "raw",
            enc.encode(secret),
            { name: "PBKDF2" },
            false,
            ["deriveBits"]
        );

        const derivedBits = await window.crypto.subtle.deriveBits(
            {
                name: "PBKDF2",
                salt: salt,
                iterations: 100000,
                hash: "SHA-256"
            },
            keyMaterial,
            256
        );

        const hashHex = Array.from(new Uint8Array(derivedBits))
            .map(b => b.toString(16).padStart(2, '0'))
            .join('');

        return { salt: saltHex, hash: hashHex };
    },

    async verifySecret(secret, saltHex, expectedHashHex) {
        const { hash } = await this.hashSecret(secret, saltHex);
        return hash === expectedHashHex;
    }
};

/* =========================================================
   LOCAL STORAGE FALLBACK STORE (Used before Firebase is set)
   ========================================================= */

const localStore = {
    getUsers() {
        return JSON.parse(localStorage.getItem("gesture_users") || "{}");
    },
    saveUsers(users) {
        localStorage.setItem("gesture_users", JSON.stringify(users));
    },
    getLogs() {
        return JSON.parse(localStorage.getItem("gesture_logs") || "[]");
    },
    saveLogs(logs) {
        localStorage.setItem("gesture_logs", JSON.stringify(logs));
    }
};

/* =========================================================
   AUTHENTICATION & DATABASE REPOSITORY
   ========================================================= */

const LOCK_SECONDS = 30;
const MAX_FAILED_ATTEMPTS = 3;

const authRepository = {
    // Check if account is currently locked
    isLocked(user) {
        if (!user || !user.locked_until) return false;
        return new Date(user.locked_until) > new Date();
    },

    lockRemainingSeconds(user) {
        if (!this.isLocked(user)) return 0;
        const diff = Math.ceil((new Date(user.locked_until) - new Date()) / 1000);
        return Math.max(0, diff);
    },

    // Record an audit log entry
    async logEvent(username, status, reason) {
        const entry = {
            username: username || "anonymous",
            status: status,
            reason: reason || "",
            created_at: new Date().toISOString().replace("T", " ").substring(0, 19)
        };

        if (isFirebaseConnected && db) {
            try {
                await db.collection("login_logs").add(entry);
                return;
            } catch (e) {
                console.error("Firestore log write failed, using local fallback:", e);
            }
        }

        // Local fallback
        const logs = localStore.getLogs();
        logs.unshift(entry);
        if (logs.length > 50) logs.pop();
        localStore.saveLogs(logs);
    },

    // Get audit logs
    async getLogs(limitCount = 30) {
        if (isFirebaseConnected && db) {
            try {
                const snapshot = await db.collection("login_logs")
                    .orderBy("created_at", "desc")
                    .limit(limitCount)
                    .get();
                const logs = [];
                snapshot.forEach(doc => logs.push(doc.data()));
                return logs;
            } catch (e) {
                console.error("Firestore getLogs failed, reading local fallback:", e);
            }
        }

        return localStore.getLogs().slice(0, limitCount);
    },

    // Register a new user
    async registerUser(username, password, gestureSequence) {
        const userKey = username.trim().toLowerCase();

        // Check if user exists
        if (isFirebaseConnected && db) {
            const doc = await db.collection("users").doc(userKey).get();
            if (doc.exists) {
                return { success: false, message: "Username already exists." };
            }
        } else {
            const users = localStore.getUsers();
            if (users[userKey]) {
                return { success: false, message: "Username already exists." };
            }
        }

        // Hash secrets
        const pwdHash = await cryptoService.hashSecret(password);
        const gstHash = await cryptoService.hashSecret(gestureSequence);

        const userData = {
            username: username.trim(),
            password_salt: pwdHash.salt,
            password_hash: pwdHash.hash,
            gesture_salt: gstHash.salt,
            gesture_hash: gstHash.hash,
            failed_attempts: 0,
            locked_until: null,
            created_at: new Date().toISOString()
        };

        if (isFirebaseConnected && db) {
            await db.collection("users").doc(userKey).set(userData);
        } else {
            const users = localStore.getUsers();
            users[userKey] = userData;
            localStore.saveUsers(users);
        }

        await this.logEvent(username, "REGISTERED", `gesture_length=${gestureSequence.split("-").length}`);
        return { success: true, message: "User registered successfully." };
    },

    // Step 1: Verify Password
    async verifyPassword(username, password) {
        const userKey = username.trim().toLowerCase();
        let user = null;

        if (isFirebaseConnected && db) {
            const doc = await db.collection("users").doc(userKey).get();
            if (doc.exists) user = doc.data();
        } else {
            const users = localStore.getUsers();
            user = users[userKey] || null;
        }

        if (!user) {
            await this.logEvent(username, "FAILED", "unknown username");
            return { success: false, message: "Incorrect username or password." };
        }

        if (this.isLocked(user)) {
            const remaining = this.lockRemainingSeconds(user);
            await this.logEvent(username, "FAILED", "account locked");
            return {
                success: false,
                message: `Account is temporarily locked. Try again in ${remaining}s.`
            };
        }

        const match = await cryptoService.verifySecret(password, user.password_salt, user.password_hash);
        if (!match) {
            await this.recordFailedAttempt(userKey, user);
            await this.logEvent(username, "FAILED", "wrong password");
            return { success: false, message: "Incorrect username or password." };
        }

        return { success: true, message: "Password verified successfully." };
    },

    // Step 2: Verify Gesture Sequence
    async verifyGesture(username, gestureSequence) {
        const userKey = username.trim().toLowerCase();
        let user = null;

        if (isFirebaseConnected && db) {
            const doc = await db.collection("users").doc(userKey).get();
            if (doc.exists) user = doc.data();
        } else {
            const users = localStore.getUsers();
            user = users[userKey] || null;
        }

        if (!user) {
            await this.logEvent(username, "FAILED", "unknown username (gesture stage)");
            return { success: false, message: "Authentication failed." };
        }

        if (this.isLocked(user)) {
            const remaining = this.lockRemainingSeconds(user);
            await this.logEvent(username, "FAILED", "account locked (gesture stage)");
            return {
                success: false,
                message: `Account is locked. Try again in ${remaining}s.`
            };
        }

        const match = await cryptoService.verifySecret(gestureSequence, user.gesture_salt, user.gesture_hash);
        if (match) {
            await this.resetFailedAttempts(userKey, user);
            await this.logEvent(username, "SUCCESS", "password and gesture matched");
            return { success: true, message: "Login successful!" };
        } else {
            const updated = await this.recordFailedAttempt(userKey, user);
            await this.logEvent(username, "FAILED", "wrong gesture");
            const locked = this.isLocked(updated);
            const remaining = this.lockRemainingSeconds(updated);

            return {
                success: false,
                message: "Gesture sequence did not match.",
                locked: locked,
                lock_remaining: remaining
            };
        }
    },

    // Record a failed attempt & lock if needed
    async recordFailedAttempt(userKey, user) {
        user.failed_attempts = (user.failed_attempts || 0) + 1;
        if (user.failed_attempts >= MAX_FAILED_ATTEMPTS) {
            const lockDate = new Date(Date.now() + LOCK_SECONDS * 1000);
            user.locked_until = lockDate.toISOString();
        }

        if (isFirebaseConnected && db) {
            await db.collection("users").doc(userKey).update({
                failed_attempts: user.failed_attempts,
                locked_until: user.locked_until
            });
        } else {
            const users = localStore.getUsers();
            users[userKey] = user;
            localStore.saveUsers(users);
        }
        return user;
    },

    // Reset failed attempts upon successful authentication
    async resetFailedAttempts(userKey, user) {
        user.failed_attempts = 0;
        user.locked_until = null;

        if (isFirebaseConnected && db) {
            await db.collection("users").doc(userKey).update({
                failed_attempts: 0,
                locked_until: null
            });
        } else {
            const users = localStore.getUsers();
            users[userKey] = user;
            localStore.saveUsers(users);
        }
    }
};

// Auto-initialize when loaded
initFirebase();
