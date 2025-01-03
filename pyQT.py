import sys
import cv2
import sqlite3
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton , QSizePolicy ,QHBoxLayout , QMessageBox,QScrollArea
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap 
import mediapipe as mp

from main import calculate_angle, biceps_curl_counter

class CurlCounterApp(QWidget):
    def __init__(self):
        super().__init__()
        # black BG
        self.setStyleSheet("background-color: black; color: white;")

        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

        # Initialize variables
        self.counter = 0
        self.stage = None
        
        self.cap = cv2.VideoCapture(0)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.history_visible = False 

        self.initUI()

    def initUI(self):
    # Main layout
        layout = QVBoxLayout()
        top_bar_layout = QHBoxLayout()
        self.view_data_button = QPushButton("View Stored Data")
        self.view_data_button.clicked.connect(self.display_data)
        self.view_data_button.setStyleSheet("font-size: 14px; padding: 5px; background-color: #333; color: white;")
        top_bar_layout.addWidget(self.view_data_button, alignment=Qt.AlignLeft)
        top_bar_layout.addStretch()  # Push the button to the left

        layout.addLayout(top_bar_layout)

        # Scrollable area for stored data
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.setWidgetResizable(True)
        self.data_container = QLabel("Stored data will appear here.")
        self.data_container.setAlignment(Qt.AlignTop)
        self.data_container.setStyleSheet("padding: 10px; font-size: 14px; color: #f0f0f0;")
        self.scroll_area.setWidget(self.data_container)
        self.scroll_area.hide()  # Initially hidden
        layout.addWidget(self.scroll_area)

        ##############################################################################################################################

        # Set background color to black
        self.setStyleSheet("background-color: #2f2f2f; color: white;")

        # Video display label (camera view)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_label, stretch=1)  # Reduce stretch factor for the video panel

        # Counter display label (Reps)
        self.counter_label = QLabel("REPS : 0")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.counter_label.setStyleSheet("font-size: 30px; font-weight: bold; color: yellow;")
        layout.addWidget(self.counter_label, stretch=1)

        # Add a spacer above buttons for positioning
        layout.addSpacing(20)

        # Buttons layout
        button_layout = QHBoxLayout()

        # Add spacers on both sides of the buttons
        button_layout.addStretch()

        # Start button
        self.start_button = QPushButton("Start Exercise")
        self.start_button.clicked.connect(self.start_exercise)
        self.start_button.setStyleSheet("""
            font-size: 20px; 
            padding: 15px; 
            background-color: green; 
            color: white; 
            border-radius: 10px; 
        """)
        self.start_button.setFixedSize(200, 60)  # Set fixed size for the button
        button_layout.addWidget(self.start_button)

        # Spacer between buttons
        button_layout.addSpacing(20)

        # Stop button
        self.stop_button = QPushButton("Stop Exercise")
        self.stop_button.clicked.connect(self.stop_exercise)
        self.stop_button.setStyleSheet("""
            font-size: 20px; 
            padding: 15px; 
            background-color: red; 
            color: white; 
            border-radius: 10px; 
        """)
        self.stop_button.setFixedSize(200, 60)  # Set fixed size for the button
        button_layout.addWidget(self.stop_button)

        # Add spacers on both sides of the buttons
        button_layout.addStretch()

        layout.addLayout(button_layout, stretch=1)

        # Add a small spacer at the bottom to prevent buttons from sticking to the window bottom
        layout.addSpacing(20)

        self.setLayout(layout)
        self.setWindowTitle("Biceps Curl Counter")


    # def start_exercise(self):
    #     # Start the timer and video feed
    #     self.timer.start(20)  # 20 ms for smooth video update

    def start_exercise(self):
    # Start the timer and video feed
        if not self.cap:  # Initialize video capture if not already active
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.critical(self, "Error", "Could not access the camera.")
                return

        self.timer.start(20)  # 20 ms for smooth video update
        self.counter = 0  # Reset the rep counter for the new session
        self.start_button.setEnabled(False)  # Disable the start button while session is active
        self.stop_button.setEnabled(True)  # Enable the stop button

    def stop_exercise(self):
        # Stop the timer and release the video feed
        self.timer.stop()
        if self.cap:  # Check if video capture is active
            self.cap.release()
            self.cap = None

        # Save the reps count to the database
        self.save_data_to_db(self.counter)

        # Clear the video feed display
        self.video_label.clear()  # Ensure no image is stuck on the screen

        # Reset button states for the next session
        self.start_button.setEnabled(True)  # Enable the start button
        self.stop_button.setEnabled(False)  # Disable the stop button

        # Prepare motivational text and facts
        tips = [
            "Maintain a full range of motion during each rep to maximize muscle engagement and growth.",
            "Keep your core engaged throughout the movement to prevent swinging or cheating with your back.",
            "Use a neutral grip (hammer curl) occasionally to target the brachialis, a key supporting muscle for bigger biceps.",
            "Don’t let the weights drop too quickly—control the descent to create more time under tension.",
            "Squeeze your biceps at the top of the curl for 1-2 seconds to enhance the contraction and build strength.",
            "Focus on your breathing: exhale as you lift the weights and inhale as you lower them for optimal performance.",
            "Avoid locking your elbows at the bottom; this keeps the tension on your biceps and reduces the risk of injury."
        ]

        motivational_messages = [
            "Keep pushing! You’re getting stronger with every session!",
            "Great effort! Remember: Progress, not perfection.",
            "Fantastic job! The journey to strength is built one rep at a time.",
            "You’ve got this! Keep those curls steady and strong next time.",
            "Awesome work! Never forget: Rest is as important as exercise."
        ]

        # Pick random tips and motivational messages
        import random
        selected_tip = random.choice(tips)
        selected_motivation = random.choice(motivational_messages)

        # Determine feedback based on the number of reps
        if self.counter < 12:
            feedback = "You did fewer than 12 reps. Aim higher in your next session for better results!"
        else:
            feedback = "Great job hitting your target! Keep challenging yourself to improve further."

        # Design the pop-up content with dark background and light text
        message_content = f"""
        <div style="font-family: Arial; font-size: 14px; color: #f0f0f0; background-color: #222; padding: 10px; border-radius: 8px;">
            <h2 style="color: #4CAF50; text-align: center;">Session Summary</h2>
            <p style="text-align: center; font-size: 18px; color: #ffffff;"><b>Reps Completed:</b> {self.counter}</p>
            <p style="text-align: center; color: #bbbbbb; font-size: 16px;">{feedback}</p>
            <hr style="border: 1px solid #4CAF50;">
            <h3 style="color: #FFD700; text-align: center;">💡 Tip of the Day</h3>
            <p style="text-align: justify; color: #e0e0e0;">{selected_tip}</p>
            <h3 style="color: #FFA500; text-align: center;">🌟 Motivation</h3>
            <p style="text-align: justify; color: #e0e0e0;">{selected_motivation}</p>
        </div>
        """

        # Create and display the QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Session Feedback")
        msg_box.setStyleSheet("background-color: #333333; border: 1px solid #4CAF50;")  # Dark background for the box
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(message_content)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    def create_database():
        # Connect to SQLite database (or create it if it doesn't exist)
        conn = sqlite3.connect('exercise_data.db')
        cursor = conn.cursor()

        # Create a table to store exercise session data (only storing reps)
        cursor.execute('''CREATE TABLE IF NOT EXISTS exercise_sessions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            reps INTEGER,
                            session_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )''')

        conn.commit()
        conn.close()

    # Call the function to create the database and table
    create_database()

    def save_data_to_db(self, reps):
        # Connect to SQLite database
        conn = sqlite3.connect('exercise_data.db')
        cursor = conn.cursor()

        # Insert reps into the table
        cursor.execute('''INSERT INTO exercise_sessions (reps)
                        VALUES (?)''', (reps,))

        conn.commit()
        conn.close()
      
    def display_data(self):
        if self.history_visible:
            self.scroll_area.hide()
            self.view_data_button.setText("View Stored Data")
        else:
            # Connect to SQLite database
            conn = sqlite3.connect('exercise_data.db')
            cursor = conn.cursor()

            # Retrieve data from the exercise_sessions table
            cursor.execute("SELECT * FROM exercise_sessions")
            rows = cursor.fetchall()

            # Format data with HTML for better appearance
            data_text = """
            <div style="font-family: Arial; font-size: 16px; color: #f7f5f5;">
                <h2 style="text-align: center; color: yellow;">Stored Exercise Data</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <th style="text-align: left; padding: 8px; background-color: #444; color: #f7f5f5;">Session No.</th>
                        <th style="text-align: left; padding: 8px; background-color: #444; color: #f7f5f5;">Reps</th>
                        <th style="text-align: left; padding: 8px; background-color: #444; color: #f7f5f5;">Session Time</th>
                    </tr>
            """
            for row in rows:
                data_text += f"""
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #666; color: #f7f5f5;">{row[0]}</td>
                        <td style="padding: 8px; border-bottom: 1px solid #666; color: #f7f5f5;">{row[1]}</td>
                        <td style="padding: 8px; border-bottom: 1px solid #666; color: #f7f5f5;">{row[2]}</td>
                    </tr>
                """
            data_text += """
                </table>
            </div>
            """
            conn.close()

            # Update the QLabel content
            self.data_container.setText(data_text)
            self.scroll_area.show()
            self.view_data_button.setText("Hide Stored Data")

        self.history_visible = not self.history_visible



            #------------------------------------------------------------------------------------------------------------------------



    def update_frame(self):
        # Capture frame from camera
        ret, frame = self.cap.read()
        if not ret:
            return
        
        # Resize the frame to match the display size
        frame = cv2.resize(frame, (self.video_label.width(), self.video_label.height()))

        # Process the frame (resize, RGB conversion)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image)

        # Check if pose landmarks were detected
        if results.pose_landmarks:
            # Extract coordinates
            landmarks = results.pose_landmarks.landmark
            shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                        landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            elbow = [landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                     landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
            wrist = [landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                     landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].y]

            # Calculate angle and update counter
            angle = calculate_angle(shoulder, elbow, wrist)
            self.counter, self.stage = biceps_curl_counter(angle, self.counter, self.stage)

            
            # Update counter label
            self.counter_label.setText(f"REPS : {self.counter}")

            # Draw landmarks
            mp.solutions.drawing_utils.draw_landmarks(
                image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

        # Convert image to QImage for PyQt display
        h, w, ch = image.shape
        bytes_per_line = ch * w
        qt_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

    def closeEvent(self, event):
        # Release resources on close
        self.cap.release()
        self.pose.close()
        event.accept()

# Main Application
app = QApplication(sys.argv)
window = CurlCounterApp()
window.show()
sys.exit(app.exec_())
