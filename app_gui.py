import customtkinter as ctk
import cv2
import time
import os
from PIL import Image, ImageTk
from datetime import datetime

import database
import security
from gesture_detector import count_fingers, sequence_to_string

# Try to import MediaPipe
try:
    from mediapipe.python.solutions import hands as mp_hands
    from mediapipe.python.solutions import drawing_utils as mp_draw
except Exception as e:
    mp_hands = None
    mp_draw = None
    print("MediaPipe import failed in GUI:", e)

# Theme and Color Scheme Constants
COLOR_BG = "#0f172a"          # Slate-900 (Deep background)
COLOR_CARD = "#1e293b"        # Slate-800 (Card background)
COLOR_TEXT = "#f8fafc"        # Slate-50 (Near white text)
COLOR_MUTED = "#94a3b8"       # Slate-400 (Muted gray text)
COLOR_PRIMARY = "#6366f1"     # Indigo (Action buttons)
COLOR_PRIMARY_HOVER = "#4f46e5"
COLOR_SUCCESS = "#10b981"     # Emerald Green
COLOR_DANGER = "#ef4444"      # Rose Red
COLOR_WARNING = "#f59e0b"     # Amber

GESTURE_NAMES = {
    0: "Fist ✊",
    1: "One Finger ☝️",
    2: "Two Fingers ✌️",
    3: "Three Fingers 🤟",
    4: "Four Fingers ✋",
    5: "Open Palm 🖐️"
}

class GestureLoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure Main Window
        self.title("Hand Gesture Security & Login System")
        self.geometry("900x700")
        self.configure(fg_color=COLOR_BG)
        self.resizable(False, False)
        
        # Initialize Database
        database.init_db()
        
        # Application State
        self.current_user = None
        self.captured_sequence = []
        
        # Main Container
        self.container = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        # Create and cache frames
        self.frames = {}
        for F in (WelcomeScreen, RegisterScreen, LoginScreen, CameraScreen, LogsScreen, SuccessScreen):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            
        self.show_frame("WelcomeScreen")

    def show_frame(self, page_name, **kwargs):
        """Bring a frame to the front and call its on_show hook if defined."""
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
            
    def handle_exit(self):
        # Gracefully release camera if active in any screen
        camera_screen = self.frames.get("CameraScreen")
        if camera_screen:
            camera_screen.stop_camera()
        self.destroy()

# ==========================================
# 1. WELCOME / MAIN MENU SCREEN
# ==========================================
class WelcomeScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG)
        self.controller = controller
        
        # Title Card
        title_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=16, border_width=2, border_color="#334155")
        title_frame.pack(pady=(80, 40), padx=50, fill="x")
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="BIOMETRIC GESTURE AUTHENTICATION", 
            font=ctk.CTkFont(family="Helvetica", size=26, weight="bold"),
            text_color=COLOR_TEXT
        )
        title_label.pack(pady=(20, 5))
        
        subtitle_label = ctk.CTkLabel(
            title_frame, 
            text="Secure your local vault using PBKDF2 cryptography and hand gestures.", 
            font=ctk.CTkFont(family="Helvetica", size=14),
            text_color=COLOR_MUTED
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Buttons Container
        btn_frame = ctk.CTkFrame(self, fg_color=COLOR_BG)
        btn_frame.pack(pady=20)
        
        self.btn_login = ctk.CTkButton(
            btn_frame, 
            text="🔑 Login", 
            width=240, 
            height=50, 
            font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=lambda: self.controller.show_frame("LoginScreen")
        )
        self.btn_login.grid(row=0, column=0, padx=20, pady=15)
        
        self.btn_register = ctk.CTkButton(
            btn_frame, 
            text="📝 Register New User", 
            width=240, 
            height=50, 
            font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            fg_color=COLOR_CARD,
            hover_color="#334155",
            border_width=2,
            border_color="#475569",
            command=lambda: self.controller.show_frame("RegisterScreen")
        )
        self.btn_register.grid(row=1, column=0, padx=20, pady=15)
        
        self.btn_logs = ctk.CTkButton(
            btn_frame, 
            text="📋 View Audit Logs", 
            width=240, 
            height=50, 
            font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            fg_color=COLOR_CARD,
            hover_color="#334155",
            border_width=2,
            border_color="#475569",
            command=lambda: self.controller.show_frame("LogsScreen")
        )
        self.btn_logs.grid(row=2, column=0, padx=20, pady=15)
        
        self.btn_exit = ctk.CTkButton(
            btn_frame, 
            text="❌ Exit System", 
            width=240, 
            height=50, 
            font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            fg_color="#311010",
            hover_color="#7f1d1d",
            border_width=2,
            border_color=COLOR_DANGER,
            command=self.controller.handle_exit
        )
        self.btn_exit.grid(row=3, column=0, padx=20, pady=15)

# ==========================================
# 2. REGISTER SCREEN
# ==========================================
class RegisterScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG)
        self.controller = controller
        
        # Header
        header = ctk.CTkLabel(
            self, 
            text="Register New Credentials", 
            font=ctk.CTkFont(family="Helvetica", size=24, weight="bold"),
            text_color=COLOR_TEXT
        )
        header.pack(pady=(40, 10))
        
        card = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=16, border_width=1, border_color="#334155")
        card.pack(pady=10, padx=50, fill="both", expand=True)
        
        # Inputs
        label_user = ctk.CTkLabel(card, text="Username", font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"))
        label_user.pack(pady=(20, 2), anchor="w", padx=40)
        self.entry_user = ctk.CTkEntry(card, width=400, height=40, placeholder_text="Enter unique username")
        self.entry_user.pack(pady=(0, 15))
        
        label_pass = ctk.CTkLabel(card, text="Password", font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"))
        label_pass.pack(pady=(5, 2), anchor="w", padx=40)
        self.entry_pass = ctk.CTkEntry(card, width=400, height=40, show="*", placeholder_text="Enter password")
        self.entry_pass.pack(pady=(0, 15))
        
        label_confirm = ctk.CTkLabel(card, text="Confirm Password", font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"))
        label_confirm.pack(pady=(5, 2), anchor="w", padx=40)
        self.entry_confirm = ctk.CTkEntry(card, width=400, height=40, show="*", placeholder_text="Confirm password")
        self.entry_confirm.pack(pady=(0, 20))
        
        # Error Label
        self.lbl_error = ctk.CTkLabel(card, text="", text_color=COLOR_DANGER, font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"))
        self.lbl_error.pack(pady=5)
        
        # Actions
        btn_action_frame = ctk.CTkFrame(card, fg_color=COLOR_CARD)
        btn_action_frame.pack(pady=(10, 20))
        
        btn_cancel = ctk.CTkButton(
            btn_action_frame, 
            text="⬅️ Back", 
            width=180, 
            height=45, 
            font=ctk.CTkFont(family="Helvetica", size=15),
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.controller.show_frame("WelcomeScreen")
        )
        btn_cancel.grid(row=0, column=0, padx=15)
        
        btn_next = ctk.CTkButton(
            btn_action_frame, 
            text="Continue to Gestures ➡️", 
            width=180, 
            height=45, 
            font=ctk.CTkFont(family="Helvetica", size=15, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self.validate_and_continue
        )
        btn_next.grid(row=0, column=1, padx=15)
        
    def on_show(self):
        # Clear fields when screen is loaded
        self.entry_user.delete(0, "end")
        self.entry_pass.delete(0, "end")
        self.entry_confirm.delete(0, "end")
        self.lbl_error.configure(text="")
        
    def validate_and_continue(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get()
        confirm = self.entry_confirm.get()
        
        if not username:
            self.lbl_error.configure(text="Username cannot be empty.")
            return
        if not password:
            self.lbl_error.configure(text="Password cannot be empty.")
            return
        if password != confirm:
            self.lbl_error.configure(text="Passwords do not match.")
            return
            
        # Check if username exists
        if database.get_user(username) is not None:
            self.lbl_error.configure(text="Username already exists.")
            return
            
        # Go to Camera Screen in REGISTER mode
        self.controller.show_frame(
            "CameraScreen", 
            mode="REGISTER", 
            username=username, 
            password=password
        )

# ==========================================
# 3. LOGIN SCREEN
# ==========================================
class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG)
        self.controller = controller
        
        # Header
        header = ctk.CTkLabel(
            self, 
            text="System Login", 
            font=ctk.CTkFont(family="Helvetica", size=24, weight="bold"),
            text_color=COLOR_TEXT
        )
        header.pack(pady=(50, 10))
        
        card = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=16, border_width=1, border_color="#334155")
        card.pack(pady=10, padx=50, fill="both", expand=True)
        
        # Inputs
        label_user = ctk.CTkLabel(card, text="Username", font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"))
        label_user.pack(pady=(30, 2), anchor="w", padx=40)
        self.entry_user = ctk.CTkEntry(card, width=400, height=40, placeholder_text="Enter your username")
        self.entry_user.pack(pady=(0, 20))
        
        label_pass = ctk.CTkLabel(card, text="Password", font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"))
        label_pass.pack(pady=(5, 2), anchor="w", padx=40)
        self.entry_pass = ctk.CTkEntry(card, width=400, height=40, show="*", placeholder_text="Enter your password")
        self.entry_pass.pack(pady=(0, 20))
        
        # Error Label
        self.lbl_error = ctk.CTkLabel(card, text="", text_color=COLOR_DANGER, font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"))
        self.lbl_error.pack(pady=5)
        
        # Actions
        btn_action_frame = ctk.CTkFrame(card, fg_color=COLOR_CARD)
        btn_action_frame.pack(pady=(10, 30))
        
        btn_cancel = ctk.CTkButton(
            btn_action_frame, 
            text="⬅️ Back", 
            width=180, 
            height=45, 
            font=ctk.CTkFont(family="Helvetica", size=15),
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.controller.show_frame("WelcomeScreen")
        )
        btn_cancel.grid(row=0, column=0, padx=15)
        
        btn_next = ctk.CTkButton(
            btn_action_frame, 
            text="Verify Password ➡️", 
            width=180, 
            height=45, 
            font=ctk.CTkFont(family="Helvetica", size=15, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self.verify_password
        )
        btn_next.grid(row=0, column=1, padx=15)
        
    def on_show(self):
        self.entry_user.delete(0, "end")
        self.entry_pass.delete(0, "end")
        self.lbl_error.configure(text="")
        
    def verify_password(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get()
        
        if not username or not password:
            self.lbl_error.configure(text="Please fill in all fields.")
            return
            
        user = database.get_user(username)
        if user is None:
            database.log_login(username, "FAILED", "unknown username")
            self.lbl_error.configure(text="Incorrect username or password.")
            return
            
        # Check Account Lock
        if database.is_locked(user):
            seconds = database.lock_remaining_seconds(user)
            database.log_login(username, "FAILED", "account locked")
            self.lbl_error.configure(text=f"Account temporarily locked. Try again in {seconds}s.")
            return
            
        # Verify password hash
        if not security.verify_secret(password, user["password_salt"], user["password_hash"]):
            database.record_failed_attempt(username)
            database.log_login(username, "FAILED", "wrong password")
            self.lbl_error.configure(text="Incorrect username or password.")
            return
            
        # Password match! Now transition to Camera gesture verification
        self.controller.show_frame(
            "CameraScreen",
            mode="LOGIN",
            username=username,
            user_record=user
        )

# ==========================================
# 4. CAMERA & GESTURE DETECTION SCREEN
# ==========================================
class CameraScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG)
        self.controller = controller
        
        # State variables
        self.mode = None # "REGISTER" or "LOGIN"
        self.username = None
        self.password = None # Only for Register
        self.user_record = None # Only for Login
        
        self.cap = None
        self.hands_detector = None
        
        # Gesture Hold State Machine
        self.sequence_length = 3
        self.captured_sequence = []
        self.current_gesture = None
        self.gesture_start_time = 0
        self.locked_gesture = None
        self.loop_id = None
        
        # Header Label
        self.lbl_header = ctk.CTkLabel(
            self, 
            text="Verify Gesture Password", 
            font=ctk.CTkFont(family="Helvetica", size=20, weight="bold"),
            text_color=COLOR_TEXT
        )
        self.lbl_header.pack(pady=(15, 5))
        
        # Status Subtitle
        self.lbl_status = ctk.CTkLabel(
            self,
            text="Show your gestures to the camera",
            font=ctk.CTkFont(family="Helvetica", size=13),
            text_color=COLOR_MUTED
        )
        self.lbl_status.pack(pady=(0, 10))
        
        # Camera Feed Panel (Main area)
        self.camera_panel = ctk.CTkLabel(self, text="Loading Camera...", fg_color="#020617", corner_radius=12)
        self.camera_panel.pack(pady=5, padx=30, fill="both", expand=True)
        
        # Bottom HUD Controls
        hud_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12)
        hud_frame.pack(pady=15, padx=30, fill="x")
        
        # Visual captured boxes
        self.boxes_frame = ctk.CTkFrame(hud_frame, fg_color=COLOR_CARD)
        self.boxes_frame.pack(pady=10)
        
        # Progress indicator for current hold
        self.progress_bar = ctk.CTkProgressBar(hud_frame, width=450, height=8, progress_color=COLOR_PRIMARY)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(pady=5)
        
        self.lbl_gesture_desc = ctk.CTkLabel(
            hud_frame, 
            text="Hold gesture for 1 second", 
            font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"),
            text_color=COLOR_MUTED
        )
        self.lbl_gesture_desc.pack(pady=(0, 10))
        
        # Stop / Cancel Button
        self.btn_cancel = ctk.CTkButton(
            self, 
            text="🛑 Cancel Authentication", 
            width=250, 
            height=40,
            font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"),
            fg_color="#311010",
            hover_color="#7f1d1d",
            border_width=1,
            border_color=COLOR_DANGER,
            command=self.cancel_scan
        )
        self.btn_cancel.pack(pady=(0, 20))
        
    def on_show(self, mode, username, password=None, user_record=None):
        self.mode = mode
        self.username = username
        self.password = password
        self.user_record = user_record
        
        self.captured_sequence = []
        self.current_gesture = None
        self.gesture_start_time = 0
        self.locked_gesture = None
        self.progress_bar.set(0.0)
        
        # Update Titles
        if self.mode == "REGISTER":
            self.lbl_header.configure(text=f"Register Gestures for {self.username}")
            self.lbl_status.configure(text="Perform 3 unique gestures in sequence.")
        else:
            self.lbl_header.configure(text=f"Gesture Auth Required: {self.username}")
            self.lbl_status.configure(text="Perform your saved 3-gesture login sequence.")
            
        self.update_boxes()
        
        # Initialize OpenCV Camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.camera_panel.configure(text="CRITICAL ERROR: Camera could not be opened.\nPlease check system permissions.")
            return
            
        # Initialize MediaPipe Hands
        if mp_hands is not None:
            self.hands_detector = mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7
            )
        else:
            self.camera_panel.configure(text="ERROR: MediaPipe is missing or failed to import.")
            return
            
        # Start capture loop
        self.update_loop()
        
    def update_boxes(self):
        # Clear old children in boxes frame
        for widget in self.boxes_frame.winfo_children():
            widget.destroy()
            
        for i in range(self.sequence_length):
            if i < len(self.captured_sequence):
                val = self.captured_sequence[i]
                text = GESTURE_NAMES.get(val, str(val))
                bg_color = COLOR_SUCCESS
            else:
                text = "Empty"
                bg_color = "#334155"
                
            box = ctk.CTkLabel(
                self.boxes_frame, 
                text=text, 
                width=130, 
                height=35,
                corner_radius=8,
                fg_color=bg_color,
                font=ctk.CTkFont(family="Helvetica", size=13, weight="bold")
            )
            box.grid(row=0, column=i, padx=10)
            
    def cancel_scan(self):
        self.stop_camera()
        if self.mode == "REGISTER":
            self.controller.show_frame("RegisterScreen")
        else:
            database.log_login(self.username, "FAILED", "gesture cancelled")
            self.controller.show_frame("LoginScreen")
            
    def stop_camera(self):
        # Cancel active tkinter schedule loops
        if self.loop_id:
            self.after_cancel(self.loop_id)
            self.loop_id = None
            
        # Release resources
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.hands_detector:
            self.hands_detector.close()
            self.hands_detector = None
            
        # Reset camera preview label
        self.camera_panel.configure(image=None, text="Camera Offline")
        
    def update_loop(self):
        if not self.cap or not self.cap.isOpened():
            return
            
        success, frame = self.cap.read()
        if not success:
            self.camera_panel.configure(text="Failed to grab camera frame.")
            self.stop_camera()
            return
            
        # Frame processing
        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        # Resize to fit in our display smoothly (maintaining aspect ratio roughly)
        target_w = 640
        target_h = 480
        frame = cv2.resize(frame, (target_w, target_h))
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands_detector.process(rgb_frame)
        
        detected_gesture = None
        
        # Process Hand Landmarks
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            
            # Draw landmarks directly onto frame for visual feedback
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(99, 102, 241), thickness=2, circle_radius=3), # Custom primary color line
                mp_draw.DrawingSpec(color=(16, 185, 129), thickness=2, circle_radius=2)  # Secondary nodes green
            )
            
            detected_gesture = count_fingers(hand_landmarks)
            
            # Draw visual overlay on top of webcam feed in GUI
            cv2.putText(
                frame,
                f"Detected: {GESTURE_NAMES.get(detected_gesture, str(detected_gesture))}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (99, 102, 241),
                2,
                cv2.LINE_AA
            )
            
            # Hold Gesture State Management
            if detected_gesture == self.locked_gesture:
                self.progress_bar.set(0.0)
                self.lbl_gesture_desc.configure(text="Change gesture or remove hand for next step", text_color=COLOR_WARNING)
            else:
                if detected_gesture != self.current_gesture:
                    self.current_gesture = detected_gesture
                    self.gesture_start_time = time.time()
                    self.progress_bar.set(0.0)
                else:
                    elapsed = time.time() - self.gesture_start_time
                    self.progress_bar.set(min(1.0, elapsed / 1.0))
                    self.lbl_gesture_desc.configure(
                        text=f"Holding {GESTURE_NAMES.get(detected_gesture)}: {elapsed:.1f}s / 1.0s",
                        text_color=COLOR_PRIMARY
                    )
                    
                    if elapsed >= 1.0:
                        # Append and play a beep or flash color
                        self.captured_sequence.append(detected_gesture)
                        self.locked_gesture = detected_gesture
                        self.current_gesture = None
                        self.progress_bar.set(0.0)
                        self.update_boxes()
                        
                        # Briefly output to console for logging
                        print(f"Captured gesture: {detected_gesture}")
                        
                        # Process completion
                        if len(self.captured_sequence) == self.sequence_length:
                            self.after(500, self.handle_sequence_complete)
                            return
        else:
            # Reset hold progress if no hand is in frame
            self.current_gesture = None
            self.locked_gesture = None
            self.progress_bar.set(0.0)
            self.lbl_gesture_desc.configure(text="No hand detected", text_color=COLOR_MUTED)
            
        # Convert frame to PhotoImage
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img_tk = ImageTk.PhotoImage(image=img)
        
        self.camera_panel.configure(image=img_tk, text="")
        self.camera_panel.image = img_tk  # Keep reference
        
        # Schedule next tick
        self.loop_id = self.after(10, self.update_loop)
        
    def handle_sequence_complete(self):
        self.stop_camera()
        gesture_str = sequence_to_string(self.captured_sequence)
        
        if self.mode == "REGISTER":
            # Save User to database
            pass_salt, pass_hash = security.hash_secret(self.password)
            gest_salt, gest_hash = security.hash_secret(gesture_str)
            
            success = database.create_user(
                self.username, 
                pass_salt, 
                pass_hash, 
                gest_salt, 
                gest_hash
            )
            
            if success:
                database.log_login(self.username, "REGISTERED", f"gesture_length={self.sequence_length}")
                self.controller.show_frame(
                    "SuccessScreen",
                    title="User Registered Successfully!",
                    message=f"Account for {self.username} has been created.\nYour hand gesture key sequence is saved securely.",
                    status="SUCCESS"
                )
            else:
                self.controller.show_frame(
                    "SuccessScreen",
                    title="Registration Failed",
                    message="Username already exists. Please try another.",
                    status="FAILED"
                )
                
        elif self.mode == "LOGIN":
            # Verify gesture key sequence
            user = self.user_record
            if security.verify_secret(gesture_str, user["gesture_salt"], user["gesture_hash"]):
                database.reset_failed_attempts(self.username)
                database.log_login(self.username, "SUCCESS", "password and gesture matched")
                self.controller.show_frame(
                    "SuccessScreen",
                    title="Access Granted",
                    message=f"Welcome back, {self.username}!\nIdentity verified using gesture sequence.",
                    status="SUCCESS"
                )
            else:
                database.record_failed_attempt(self.username)
                database.log_login(self.username, "FAILED", "wrong gesture")
                
                # Check lock status again after logging failure
                updated_user = database.get_user(self.username)
                if database.is_locked(updated_user):
                    msg = "Incorrect gesture password.\nYour account has been temporarily LOCKED due to repeated failures."
                else:
                    msg = "Gesture credentials do not match stored key sequence.\nPlease try again."
                    
                self.controller.show_frame(
                    "SuccessScreen",
                    title="Access Denied",
                    message=msg,
                    status="FAILED"
                )

# ==========================================
# 5. AUDIT LOGS SCREEN
# ==========================================
class LogsScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG)
        self.controller = controller
        
        # Header
        header = ctk.CTkLabel(
            self, 
            text="Audit Authentication Logs", 
            font=ctk.CTkFont(family="Helvetica", size=22, weight="bold"),
            text_color=COLOR_TEXT
        )
        header.pack(pady=(30, 5))
        
        subtitle = ctk.CTkLabel(
            self,
            text="Real-time security auditing and failed attempt tracking",
            font=ctk.CTkFont(family="Helvetica", size=13),
            text_color=COLOR_MUTED
        )
        subtitle.pack(pady=(0, 15))
        
        # Text/Table display
        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Courier", size=13), fg_color="#020617")
        self.textbox.pack(fill="both", expand=True, padx=45, pady=5)
        
        # Refresh and back actions
        btn_frame = ctk.CTkFrame(self, fg_color=COLOR_BG)
        btn_frame.pack(pady=20)
        
        btn_back = ctk.CTkButton(
            btn_frame, 
            text="⬅️ Back to Main Menu", 
            width=200, 
            height=40,
            font=ctk.CTkFont(family="Helvetica", size=14),
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.controller.show_frame("WelcomeScreen")
        )
        btn_back.grid(row=0, column=0, padx=15)
        
        btn_refresh = ctk.CTkButton(
            btn_frame, 
            text="🔄 Refresh Logs", 
            width=200, 
            height=40,
            font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self.refresh_logs
        )
        btn_refresh.grid(row=0, column=1, padx=15)
        
    def on_show(self):
        self.refresh_logs()
        
    def refresh_logs(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        
        # Build headers
        self.textbox.insert("end", f"{'Timestamp':<22} | {'Username':<12} | {'Action/Status':<15} | Details / Reason\n")
        self.textbox.insert("end", "="*80 + "\n")
        
        rows = database.show_logs(limit=25)
        if not rows:
            self.textbox.insert("end", "\nNo security audit logs found.")
        else:
            for row in rows:
                timestamp = row["created_at"]
                user = row["username"]
                status = row["status"]
                reason = row["reason"]
                self.textbox.insert("end", f"{timestamp:<22} | {user:<12} | {status:<15} | {reason}\n")
                
        self.textbox.configure(state="disabled")

# ==========================================
# 6. ACTION SUCCESS / FAILURE ALERT SCREEN
# ==========================================
class SuccessScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=COLOR_BG)
        self.controller = controller
        
        self.status = "SUCCESS"
        
        self.card = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=16, border_width=2, border_color="#334155")
        self.card.pack(pady=80, padx=80, fill="both", expand=True)
        
        # Big Icon/Emoji
        self.lbl_icon = ctk.CTkLabel(
            self.card, 
            text="✅", 
            font=ctk.CTkFont(family="Helvetica", size=72)
        )
        self.lbl_icon.pack(pady=(40, 10))
        
        # Status Title
        self.lbl_title = ctk.CTkLabel(
            self.card, 
            text="Action Complete", 
            font=ctk.CTkFont(family="Helvetica", size=24, weight="bold"),
            text_color=COLOR_TEXT
        )
        self.lbl_title.pack(pady=10)
        
        # Detail message
        self.lbl_msg = ctk.CTkLabel(
            self.card, 
            text="Details of execution go here", 
            font=ctk.CTkFont(family="Helvetica", size=14),
            text_color=COLOR_MUTED
        )
        self.lbl_msg.pack(pady=15, padx=30)
        
        # Continue Button
        self.btn_done = ctk.CTkButton(
            self.card, 
            text="Continue", 
            width=220, 
            height=45,
            font=ctk.CTkFont(family="Helvetica", size=15, weight="bold"),
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self.done_click
        )
        self.btn_done.pack(pady=(20, 40))
        
    def on_show(self, title, message, status="SUCCESS"):
        self.status = status
        self.lbl_title.configure(text=title)
        self.lbl_msg.configure(text=message)
        
        if self.status == "SUCCESS":
            self.lbl_icon.configure(text="✅")
            self.card.configure(border_color=COLOR_SUCCESS)
            self.lbl_title.configure(text_color=COLOR_SUCCESS)
            self.btn_done.configure(fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER)
        else:
            self.lbl_icon.configure(text="❌")
            self.card.configure(border_color=COLOR_DANGER)
            self.lbl_title.configure(text_color=COLOR_DANGER)
            self.btn_done.configure(fg_color=COLOR_DANGER, hover_color="#991b1b")
            
    def done_click(self):
        self.controller.show_frame("WelcomeScreen")

# Run Application Entry Point
def run_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = GestureLoginApp()
    
    # Custom window close callback
    app.protocol("WM_DELETE_WINDOW", app.handle_exit)
    app.mainloop()

if __name__ == "__main__":
    run_gui()
