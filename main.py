import cv2
import numpy as np
import threading
import time
import os
import json
from pathlib import Path
import platform
import subprocess
from datetime import datetime

# Global flag to control alarm state
alarm_active = False
alarm_thread = None

# Default settings
DEFAULT_EAR_THRESHOLD = 0.2  # Lower value means more closed
DEFAULT_CLOSED_FRAMES_THRESHOLD = 3

# Settings file path
SETTINGS_FILE = "eye_monitor_settings.json"

# UI Configuration
UI_BG_COLOR = (25, 25, 25)  # Dark background
UI_TEXT_COLOR = (240, 240, 240)  # Light text
UI_ACCENT_COLOR = (0, 165, 255)  # Orange accent
UI_SUCCESS_COLOR = (0, 255, 100)  # Green for open eyes
UI_WARNING_COLOR = (0, 165, 255)  # Orange for warning
UI_DANGER_COLOR = (0, 0, 255)  # Red for closed eyes/alerts
UI_FONT = cv2.FONT_HERSHEY_SIMPLEX

# Menu Configuration
MENU_ACTIVE = False  # Flag to show/hide menu
MENU_SELECTED_ITEM = 0  # Currently selected menu item

# Menu Items and Settings (will be updated from loaded settings)
MENU_ITEMS = [
    {"name": "EAR Threshold", "value": DEFAULT_EAR_THRESHOLD, "step": 0.01, "min": 0.1, "max": 0.5},
    {"name": "Closed Frames Threshold", "value": DEFAULT_CLOSED_FRAMES_THRESHOLD, "step": 1, "min": 1, "max": 10},
    {"name": "Alarm Enabled", "value": True, "type": "toggle"},
    {"name": "Visualization", "value": True, "type": "toggle"},
    {"name": "Sound Volume", "value": 100, "step": 5, "min": 0, "max": 100, "unit": "%"},
    {"name": "Alert Style", "value": 0, "options": ["Flashing", "Text Only", "Both"], "type": "options"},
    {"name": "Save Settings", "type": "action"},
    {"name": "Reset to Defaults", "type": "action"},
    {"name": "Exit Application", "type": "action"}
]

def load_settings():
    """Load settings from file or use defaults"""
    global MENU_ITEMS
    
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                
            # Update menu items with loaded settings
            for i, item in enumerate(MENU_ITEMS):
                if i < len(settings) and "value" in item:
                    item["value"] = settings[i]
                    
            print(f"Settings loaded from {SETTINGS_FILE}")
        else:
            print("No settings file found, using defaults")
    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings():
    """Save current settings to file"""
    try:
        # Extract values from menu items
        settings = [item["value"] for item in MENU_ITEMS if "value" in item]
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
            
        print(f"Settings saved to {SETTINGS_FILE}")
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def reset_to_defaults():
    """Reset settings to default values"""
    global MENU_ITEMS
    
    MENU_ITEMS[0]["value"] = DEFAULT_EAR_THRESHOLD
    MENU_ITEMS[1]["value"] = DEFAULT_CLOSED_FRAMES_THRESHOLD
    MENU_ITEMS[2]["value"] = True  # Alarm Enabled
    MENU_ITEMS[3]["value"] = True  # Visualization
    MENU_ITEMS[4]["value"] = 100   # Sound Volume
    MENU_ITEMS[5]["value"] = 0     # Alert Style
    
    print("Settings reset to defaults")
    return True

def sound_alarm():
    """Play alarm sound in a loop until stopped"""
    global alarm_active, MENU_ITEMS
    
    alarm_active = True
    
    # Get volume setting (0-100%)
    volume = MENU_ITEMS[4]["value"] / 100.0
    
    try:
        # First attempt with playsound
        from playsound import playsound
        sound_file = Path("alert.mp3").absolute()
        
        # Play sound in a loop until alarm_active is set to False
        while alarm_active:
            playsound(str(sound_file))
            
    except Exception as e:
        print(f"Could not play sound with playsound: {e}")
        try:
            # Fallback to platform-specific method
            system = platform.system()
            sound_file = Path("alert.mp3").absolute()
            
            # Play sound in a loop until alarm_active is set to False
            while alarm_active:
                if system == "Darwin":  # macOS
                    # Add volume control for macOS
                    sound_process = subprocess.Popen(["afplay", "-v", str(volume), str(sound_file)])
                    sound_process.wait()
                elif system == "Windows":
                    sound_process = subprocess.Popen(["start", str(sound_file)], shell=True)
                    sound_process.wait()
                elif system == "Linux":
                    # Add volume control for Linux
                    sound_process = subprocess.Popen(["aplay", "-q", str(sound_file)])
                    sound_process.wait()
                else:
                    print(f"Unsupported platform: {system}")
                    return
                
                # Small delay between loops to prevent CPU overload
                time.sleep(0.1)
                
        except Exception as e2:
            print(f"Fallback sound method also failed: {e2}")

def stop_alarm():
    """Stop the alarm"""
    global alarm_active, alarm_thread
    alarm_active = False
    if alarm_thread and alarm_thread.is_alive():
        alarm_thread.join(0.5)  # Give time for the thread to exit

def eye_aspect_ratio(eye):
    """
    Calculate the eye aspect ratio
    eye: array of 6 points [(x1,y1), (x2,y2), ...]
    """
    # Vertical eye landmarks
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    
    # Horizontal eye landmark
    C = np.linalg.norm(eye[0] - eye[3])
    
    # Eye aspect ratio
    ear = (A + B) / (2.0 * C)
    return ear

def draw_fancy_text(frame, text, position, font=UI_FONT, size=0.7, color=UI_TEXT_COLOR, thickness=2, shadow=True):
    """Draw text with shadow for better visibility"""
    if shadow:
        # Draw shadow
        cv2.putText(frame, text, (position[0]+2, position[1]+2), font, size, (0, 0, 0), thickness+1)
    # Draw main text
    cv2.putText(frame, text, position, font, size, color, thickness)

def draw_menu(frame):
    """Draw the settings menu overlay"""
    global MENU_ITEMS, MENU_SELECTED_ITEM
    
    height, width = frame.shape[:2]
    
    # Semi-transparent overlay
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), UI_BG_COLOR, -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # Draw menu title
    title = "SETTINGS MENU"
    title_size = cv2.getTextSize(title, UI_FONT, 1.0, 2)[0]
    title_x = (width - title_size[0]) // 2
    cv2.putText(frame, title, (title_x, 60), UI_FONT, 1.0, UI_ACCENT_COLOR, 2)
    cv2.line(frame, (width//4, 75), (3*width//4, 75), UI_ACCENT_COLOR, 2)
    
    # Draw menu items
    start_y = 130
    item_height = 50  # Reduced to fit more items
    
    # Calculate visible range for scrolling if we have more than 7 items
    max_visible_items = 7
    total_items = len(MENU_ITEMS)
    
    if total_items <= max_visible_items:
        start_item = 0
        end_item = total_items
    else:
        # Create scrolling effect based on selected item
        middle_idx = max_visible_items // 2
        if MENU_SELECTED_ITEM <= middle_idx:
            start_item = 0
        elif MENU_SELECTED_ITEM >= total_items - middle_idx - 1:
            start_item = total_items - max_visible_items
        else:
            start_item = MENU_SELECTED_ITEM - middle_idx
        
        end_item = start_item + max_visible_items
        
        # Draw scroll indicators if needed
        if start_item > 0:
            cv2.putText(frame, "▲", (width//2, start_y - 20), UI_FONT, 0.8, UI_ACCENT_COLOR, 2)
        if end_item < total_items:
            cv2.putText(frame, "▼", (width//2, start_y + max_visible_items*item_height + 20), UI_FONT, 0.8, UI_ACCENT_COLOR, 2)
    
    for i in range(start_item, end_item):
        item = MENU_ITEMS[i]
        item_idx = i - start_item  # Adjusted index for display position
        
        # Highlight selected item
        if i == MENU_SELECTED_ITEM:
            item_bg = frame.copy()
            cv2.rectangle(item_bg, (width//4 - 20, start_y + item_idx*item_height - 20), 
                         (3*width//4 + 20, start_y + item_idx*item_height + 20), UI_ACCENT_COLOR, -1)
            cv2.addWeighted(item_bg, 0.3, frame, 0.7, 0, frame)
            cv2.rectangle(frame, (width//4 - 20, start_y + item_idx*item_height - 20), 
                         (3*width//4 + 20, start_y + item_idx*item_height + 20), UI_ACCENT_COLOR, 2)
            text_color = UI_TEXT_COLOR
        else:
            text_color = UI_TEXT_COLOR
        
        # Draw item name with keyboard shortcut
        shortcut = ""
        if "type" in item and item["type"] == "toggle":
            shortcut = " [T]"
        elif "type" in item and item["type"] == "options":
            shortcut = " [O]"
        elif "type" in item and item["type"] == "action":
            if item["name"] == "Save Settings":
                shortcut = " [S]"
            elif item["name"] == "Reset to Defaults":
                shortcut = " [R]"
            elif item["name"] == "Exit Application":
                shortcut = " [X]"
        elif "step" in item:
            shortcut = " [←/→]"
        
        draw_fancy_text(frame, item["name"] + shortcut, (width//4, start_y + item_idx*item_height), size=0.7, color=text_color)
        
        # Draw item value based on type
        if "type" in item and item["type"] == "toggle":
            value_text = "ON" if item["value"] else "OFF"
            value_color = UI_SUCCESS_COLOR if item["value"] else UI_DANGER_COLOR
        elif "type" in item and item["type"] == "options":
            value_text = item["options"][item["value"]]
            value_color = UI_ACCENT_COLOR
        elif "type" in item and item["type"] == "action":
            value_text = ""
            value_color = text_color
        elif "unit" in item:
            value_text = f"{item['value']}{item['unit']}"
            value_color = UI_ACCENT_COLOR
        else:
            value_text = f"{item['value']:.2f}" if isinstance(item["value"], float) else f"{item['value']}"
            value_color = UI_ACCENT_COLOR
        
        draw_fancy_text(frame, value_text, (3*width//4, start_y + item_idx*item_height), size=0.7, color=value_color)
    
    # Draw instructions with keyboard shortcuts
    instructions = "↑/↓: Navigate  [T]: Toggle  [O]: Change Option  [←/→]: Adjust Value  [S]: Save  [R]: Reset  [X]: Exit  [M]: Close Menu  [Q]: Quit"
    inst_size = cv2.getTextSize(instructions, UI_FONT, 0.6, 1)[0]
    inst_x = (width - inst_size[0]) // 2
    cv2.putText(frame, instructions, (inst_x, height - 40), UI_FONT, 0.6, UI_TEXT_COLOR, 1)

def display_notification(frame, message, duration=2.0, color=UI_ACCENT_COLOR):
    """Display a temporary notification message"""
    height, width = frame.shape[:2]
    
    # Semi-transparent notification background
    overlay = frame.copy()
    notification_height = 50
    notification_y = height // 4
    cv2.rectangle(overlay, (width//4, notification_y), (3*width//4, notification_y + notification_height), UI_BG_COLOR, -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
    
    # Draw notification border
    cv2.rectangle(frame, (width//4, notification_y), (3*width//4, notification_y + notification_height), color, 2)
    
    # Draw notification text
    text_size = cv2.getTextSize(message, UI_FONT, 0.7, 2)[0]
    text_x = (width - text_size[0]) // 2
    text_y = notification_y + notification_height//2 + text_size[1]//2
    draw_fancy_text(frame, message, (text_x, text_y), size=0.7, color=color)
    
    return frame

def draw_status_panel(frame, ear_value=None, closed_frames=0, eyes_open=True):
    """Draw a modern status panel at the bottom of the frame"""
    height, width = frame.shape[:2]
    
    # Draw panel background
    panel_height = 80
    panel_y = height - panel_height
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, panel_y), (width, height), UI_BG_COLOR, -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    
    # Draw divider line
    cv2.line(frame, (0, panel_y), (width, panel_y), UI_ACCENT_COLOR, 2)
    
    # Add time
    current_time = datetime.now().strftime("%H:%M:%S")
    draw_fancy_text(frame, current_time, (width-150, panel_y+30), size=0.7, color=UI_TEXT_COLOR)
    
    # Add status indicators
    if ear_value is not None:
        ear_status = f"EAR: {ear_value:.2f}"
        color = UI_SUCCESS_COLOR if eyes_open else UI_DANGER_COLOR
        draw_fancy_text(frame, ear_status, (20, panel_y+30), size=0.7, color=color)
    
    # Get threshold from menu settings
    ear_threshold = MENU_ITEMS[0]["value"]
    frames_threshold = MENU_ITEMS[1]["value"]
    
    # Draw current thresholds
    threshold_text = f"Thresholds: EAR={ear_threshold:.2f}, Frames={int(frames_threshold)}"
    draw_fancy_text(frame, threshold_text, (width//2 - 150, panel_y+60), size=0.6, color=UI_TEXT_COLOR)
    
    # Draw closed frames counter
    status_color = UI_SUCCESS_COLOR if closed_frames == 0 else UI_WARNING_COLOR if closed_frames < frames_threshold else UI_DANGER_COLOR
    draw_fancy_text(frame, f"Closed frames: {closed_frames}", (20, panel_y+60), size=0.7, color=status_color)
    
    # Draw status indicator
    status_text = "EYES OPEN" if eyes_open else "EYES CLOSED"
    status_color = UI_SUCCESS_COLOR if eyes_open else UI_DANGER_COLOR
    text_size = cv2.getTextSize(status_text, UI_FONT, 0.7, 2)[0]
    draw_fancy_text(frame, status_text, (width - text_size[0] - 20, panel_y+60), size=0.7, color=status_color)
    
    # Draw status dot
    status_radius = 8
    cv2.circle(frame, (width - text_size[0] - 40, panel_y+56), status_radius, status_color, -1)
    # Add highlight to circle
    cv2.circle(frame, (width - text_size[0] - 42, panel_y+54), 3, (255, 255, 255, 128), -1)
    
    # Add menu hint
    draw_fancy_text(frame, "Press 'M' for menu", (width//2 - 80, panel_y+30), size=0.7, color=UI_ACCENT_COLOR)

def detect_and_process_eyes():
    """Main function to detect eyes and trigger alarm"""
    try:
        # Load settings at startup
        load_settings()
        
        # Check if dlib is available for better landmark detection
        try:
            import dlib
            dlib_available = True
            
            # Load face detector and landmark predictor
            detector = dlib.get_frontal_face_detector()
            predictor_path = "shape_predictor_68_face_landmarks.dat"
            if not os.path.exists(predictor_path):
                print(f"Warning: {predictor_path} not found.")
                print("Download from http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2")
                print("Then extract it to the current directory.")
                dlib_available = False
            else:
                predictor = dlib.shape_predictor(predictor_path)
                print("Using dlib for advanced facial landmark detection")
        except ImportError:
            dlib_available = False
            print("dlib not available. Using OpenCV Haar cascades instead.")
        
        # Load Haar cascades for face and eye detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Initialize camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return
        
        # Get frame dimensions
        _, frame = cap.read()
        frame_height, frame_width = frame.shape[:2]
        
        # Variables to track eye state
        eye_closed_counter = 0
        global alarm_thread, alarm_active, MENU_ACTIVE, MENU_SELECTED_ITEM, MENU_ITEMS
        
        # Notification system
        notification = {"active": False, "message": "", "color": UI_ACCENT_COLOR, "start_time": 0, "duration": 0}
        
        print("Eye monitor started. Press 'q' to quit, 'm' to access menu.")
        
        # Frame counter for animated effects
        frame_count = 0
        
        while True:
            # Read frame from camera
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break
            
            # Increment frame counter
            frame_count += 1
            
            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply CLAHE for better contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            
            # Variable to track if eyes are open in current frame
            current_eyes_open = False
            current_ear = None
            
            # Only process eye detection when not in menu
            if not MENU_ACTIVE:
                # Detect faces
                faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(120, 120))
                
                for (x, y, w, h) in faces:
                    # Draw stylish face boundary
                    # Modern rounded rectangle effect
                    cv2.rectangle(frame, (x, y), (x+w, y+h), UI_ACCENT_COLOR, 2)
                    
                    # Get face ROI
                    face_gray = gray[y:y+h, x:x+w]
                    face_color = frame[y:y+h, x:x+w]
                    
                    if dlib_available:
                        # Convert to dlib rectangle
                        dlib_rect = dlib.rectangle(x, y, x+w, y+h)
                        
                        # Get facial landmarks
                        landmarks = predictor(frame, dlib_rect)
                        
                        # Extract eye coordinates (36-41: left eye, 42-47: right eye)
                        left_eye = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)])
                        right_eye = np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)])
                        
                        # Calculate eye aspect ratio
                        left_ear = eye_aspect_ratio(left_eye)
                        right_ear = eye_aspect_ratio(right_eye)
                        avg_ear = (left_ear + right_ear) / 2.0
                        current_ear = avg_ear
                        
                        # Check if eyes are open based on menu settings
                        if avg_ear > MENU_ITEMS[0]["value"]:  # Use configured EAR threshold
                            current_eyes_open = True
                        
                        # Only show visualization if enabled in menu
                        if MENU_ITEMS[3]["value"]:  # Visualization enabled
                            # Visualize eye landmarks with modern styling
                            for eye in [left_eye, right_eye]:
                                # Create a more appealing eye visualization
                                hull = cv2.convexHull(eye)
                                
                                # Determine eye state color
                                if avg_ear > MENU_ITEMS[0]["value"]:
                                    eye_state_color = UI_SUCCESS_COLOR  # Open eyes - green
                                    glow_color = (100, 255, 100)        # Green glow
                                else:
                                    eye_state_color = UI_DANGER_COLOR   # Closed eyes - red
                                    glow_color = (100, 100, 255)        # Red glow
                                
                                # Draw filled area with transparency
                                overlay = frame.copy()
                                cv2.drawContours(overlay, [hull], -1, eye_state_color, -1)
                                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                                
                                # Animated glow effect based on frame count
                                pulse = abs(np.sin(frame_count * 0.1)) * 2 + 1
                                # Only add glow effect if eyes are closed for a while
                                if not current_eyes_open and eye_closed_counter > 1:
                                    cv2.drawContours(frame, [hull], -1, glow_color, int(pulse))
                                
                                # Draw a more stylish contour
                                cv2.drawContours(frame, [hull], -1, UI_ACCENT_COLOR, 2)
                                
                                # Draw small circles at eye corners for style
                                cv2.circle(frame, tuple(eye[0]), 3, UI_ACCENT_COLOR, -1)  # Left corner
                                cv2.circle(frame, tuple(eye[3]), 3, UI_ACCENT_COLOR, -1)  # Right corner
                    
                    else:
                        # Use Haar cascades for eye detection with modern styling
                        eyes = eye_cascade.detectMultiScale(face_gray, 1.1, 5, minSize=(20, 20))
                        if len(eyes) >= 1:
                            current_eyes_open = True
                            
                            # Only show visualization if enabled in menu
                            if MENU_ITEMS[3]["value"]:  # Visualization enabled
                                for (ex, ey, ew, eh) in eyes:
                                    # Create eye rect coordinates
                                    eye_x1, eye_y1 = x+ex, y+ey
                                    eye_x2, eye_y2 = x+ex+ew, y+ey+eh
                                    
                                    # Draw eye outline with modern styling
                                    # Filled area with transparency
                                    overlay = frame.copy()
                                    cv2.rectangle(overlay, (eye_x1, eye_y1), (eye_x2, eye_y2), UI_SUCCESS_COLOR, -1)
                                    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                                    
                                    # Draw stylish double border
                                    cv2.rectangle(frame, (eye_x1, eye_y1), (eye_x2, eye_y2), UI_ACCENT_COLOR, 2)
                                    
                                    # Add corner accents for modern look
                                    corner_len = min(ew, eh) // 4
                                    # Top-left corner
                                    cv2.line(frame, (eye_x1, eye_y1), (eye_x1 + corner_len, eye_y1), UI_SUCCESS_COLOR, 2)
                                    cv2.line(frame, (eye_x1, eye_y1), (eye_x1, eye_y1 + corner_len), UI_SUCCESS_COLOR, 2)
                                    # Top-right corner
                                    cv2.line(frame, (eye_x2, eye_y1), (eye_x2 - corner_len, eye_y1), UI_SUCCESS_COLOR, 2)
                                    cv2.line(frame, (eye_x2, eye_y1), (eye_x2, eye_y1 + corner_len), UI_SUCCESS_COLOR, 2)
                                    # Bottom-left corner
                                    cv2.line(frame, (eye_x1, eye_y2), (eye_x1 + corner_len, eye_y2), UI_SUCCESS_COLOR, 2)
                                    cv2.line(frame, (eye_x1, eye_y2), (eye_x1, eye_y2 - corner_len), UI_SUCCESS_COLOR, 2)
                                    # Bottom-right corner
                                    cv2.line(frame, (eye_x2, eye_y2), (eye_x2 - corner_len, eye_y2), UI_SUCCESS_COLOR, 2)
                                    cv2.line(frame, (eye_x2, eye_y2), (eye_x2, eye_y2 - corner_len), UI_SUCCESS_COLOR, 2)
                
                # Update eye closed counter
                if not current_eyes_open:
                    eye_closed_counter += 1
                    
                    # Add flashing alert when eyes closed for too long
                    alert_style = MENU_ITEMS[5]["value"]  # Get alert style from menu
                    if eye_closed_counter >= MENU_ITEMS[1]["value"]:  # Use configured closed frames threshold
                        # Choose alert style based on menu setting
                        show_flashing = alert_style == 0 or alert_style == 2  # Flashing or Both
                        show_text = alert_style == 1 or alert_style == 2  # Text Only or Both
                        
                        # Flashing effect
                        if show_flashing:
                            # Flashing effect based on frame count
                            if frame_count % 10 < 5:  # Alternate every 5 frames
                                # Create warning overlay
                                overlay = frame.copy()
                                cv2.rectangle(overlay, (0, 0), (frame_width, frame_height), UI_DANGER_COLOR, -1)
                                # Apply flashing with transparency
                                cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
                        
                        # Alert text
                        if show_text:
                            # Draw alert text with shadow
                            alert_text = "WAKE UP!"
                            text_size = cv2.getTextSize(alert_text, UI_FONT, 1.2, 3)[0]
                            text_x = (frame_width - text_size[0]) // 2
                            text_y = (frame_height - text_size[1]) // 2
                            # Text shadow
                            cv2.putText(frame, alert_text, (text_x+3, text_y+3), UI_FONT, 1.2, (0, 0, 0), 3)
                            # Text with slight animation
                            intensity = int(128 + 127 * np.sin(frame_count * 0.2))
                            alert_color = (0, intensity, 255)
                            cv2.putText(frame, alert_text, (text_x, text_y), UI_FONT, 1.2, alert_color, 3)
                else:
                    eye_closed_counter = 0
                    if alarm_active:
                        stop_alarm()
                
                # Trigger alarm if eyes closed for too long and alarm is enabled
                if eye_closed_counter >= MENU_ITEMS[1]["value"] and not alarm_active and MENU_ITEMS[2]["value"]:
                    alarm_thread = threading.Thread(target=sound_alarm)
                    alarm_thread.daemon = True
                    alarm_thread.start()
            
            # Draw status panel
            draw_status_panel(frame, current_ear, eye_closed_counter, current_eyes_open)
            
            # Display notification if active
            if notification["active"]:
                current_time = time.time()
                if current_time - notification["start_time"] < notification["duration"]:
                    frame = display_notification(frame, notification["message"], color=notification["color"])
                else:
                    notification["active"] = False
            
            # Draw menu if active
            if MENU_ACTIVE:
                draw_menu(frame)
            
            # Display the frame
            cv2.imshow('Eye Monitor', frame)
            
            # Check for key presses
            key = cv2.waitKey(1) & 0xFF
            
            # Handle key presses
            if key == ord('q'):  # Quit application
                break
            elif key == ord('m'):  # Toggle menu
                MENU_ACTIVE = not MENU_ACTIVE
            
            # Menu navigation and control when menu is active
            if MENU_ACTIVE:
                if key == ord('w') or key == 0x26:  # Up arrow or W
                    MENU_SELECTED_ITEM = max(0, MENU_SELECTED_ITEM - 1)
                elif key == ord('s') or key == 0x28:  # Down arrow or S
                    MENU_SELECTED_ITEM = min(len(MENU_ITEMS) - 1, MENU_SELECTED_ITEM + 1)
                elif key == ord('t'):  # Toggle for toggle items
                    item = MENU_ITEMS[MENU_SELECTED_ITEM]
                    if "type" in item and item["type"] == "toggle":
                        item["value"] = not item["value"]
                elif key == ord('o'):  # Change option for option items
                    item = MENU_ITEMS[MENU_SELECTED_ITEM]
                    if "type" in item and item["type"] == "options":
                        options_count = len(item["options"])
                        item["value"] = (item["value"] + 1) % options_count
                elif key == ord('s'):  # Save settings
                    item = MENU_ITEMS[MENU_SELECTED_ITEM]
                    if "type" in item and item["type"] == "action" and item["name"] == "Save Settings":
                        if save_settings():
                            notification = {
                                "active": True, 
                                "message": "Settings saved successfully!", 
                                "color": UI_SUCCESS_COLOR,
                                "start_time": time.time(),
                                "duration": 2.0
                            }
                            MENU_ACTIVE = False
                elif key == ord('r'):  # Reset to defaults
                    item = MENU_ITEMS[MENU_SELECTED_ITEM]
                    if "type" in item and item["type"] == "action" and item["name"] == "Reset to Defaults":
                        if reset_to_defaults():
                            notification = {
                                "active": True, 
                                "message": "Settings reset to defaults", 
                                "color": UI_ACCENT_COLOR,
                                "start_time": time.time(),
                                "duration": 2.0
                            }
                elif key == ord('x'):  # Exit application
                    item = MENU_ITEMS[MENU_SELECTED_ITEM]
                    if "type" in item and item["type"] == "action" and item["name"] == "Exit Application":
                        break
                elif key == ord('a') or key == 0x25:  # Left arrow or A
                    # Adjust item value based on type
                    item = MENU_ITEMS[MENU_SELECTED_ITEM]
                    if "step" in item:
                        item["value"] = max(item["min"], item["value"] - item["step"])
                elif key == ord('d') or key == 0x27:  # Right arrow or D
                    # Adjust item value based on type
                    item = MENU_ITEMS[MENU_SELECTED_ITEM]
                    if "step" in item:
                        item["value"] = min(item["max"], item["value"] + item["step"])
                elif key == 13:  # Enter key (keep for backward compatibility)
                    # Execute action on Enter key
                    item = MENU_ITEMS[MENU_SELECTED_ITEM]
                    if "type" in item and item["type"] == "action":
                        if item["name"] == "Save Settings":
                            if save_settings():
                                notification = {
                                    "active": True, 
                                    "message": "Settings saved successfully!", 
                                    "color": UI_SUCCESS_COLOR,
                                    "start_time": time.time(),
                                    "duration": 2.0
                                }
                                MENU_ACTIVE = False
                        elif item["name"] == "Reset to Defaults":
                            if reset_to_defaults():
                                notification = {
                                    "active": True, 
                                    "message": "Settings reset to defaults", 
                                    "color": UI_ACCENT_COLOR,
                                    "start_time": time.time(),
                                    "duration": 2.0
                                }
                        elif item["name"] == "Exit Application":
                            break
                    elif "type" in item and item["type"] == "toggle":
                        item["value"] = not item["value"]
                    elif "type" in item and item["type"] == "options":
                        options_count = len(item["options"])
                        item["value"] = (item["value"] + 1) % options_count
        
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        if alarm_active:
            stop_alarm()
        
        # Save settings on exit if any were changed
        save_settings()
    
    except Exception as e:
        print(f"Error: {e}")
        if alarm_active:
            stop_alarm()

if __name__ == "__main__":
    detect_and_process_eyes() 