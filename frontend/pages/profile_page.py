"""Display user profile with uploaded document and recorded video."""
import time
from pathlib import Path

import cv2
import streamlit as st
import yaml

st.set_page_config(page_title="Profile Page", layout="wide", initial_sidebar_state="collapsed")
user_data_dir = Path.cwd() / "user_data"
user_folder = user_data_dir / st.session_state.username
yaml_file_path = user_folder / "user_info.yaml"
step_in = 1

def logout() -> None:
    """Reset session state variables and mark the user for redirection."""
    st.session_state.page = "login"
    st.session_state.registration_step = step_in
    st.session_state.username = ""
    st.session_state.phone = ""
    st.session_state.dob = None
    st.session_state.password = ""
    st.session_state.confirm_password = ""
    st.session_state.fname = ""
    if "login_step" in st.session_state:
        st.session_state.login_step = step_in
    if "login_username" in st.session_state:
        st.session_state.login_username = ""
    if "login_password" in st.session_state:
        st.session_state.login_password = ""
    st.session_state.logout_triggered = True # track logout status

st.button("Logout", on_click=logout)

# Handle redirection after the callback execution
if st.session_state.get("logout_triggered", False):
    st.switch_page("app.py")

if not yaml_file_path.exists():
    st.error("User information not found.")
    st.stop()

with yaml_file_path.open() as yaml_file:
    user_data = yaml.safe_load(yaml_file)
col1, col2 = st.tabs(["User Details","Uploaded Document"])
with col1:
    st.write(f"**Username:** {user_data.get('username', 'N/A')}")
    st.write(f"**Full Name:** {user_data.get('fname', 'N/A')}")
    st.write(f"**Phone Number:** {user_data.get('phone_no', 'N/A')}")
    st.write(f"**Date of Birth:** {user_data.get('dob', 'N/A')}")

with col2:
    col3, col4 = st.tabs(["Uploaded Document","Most recent Recording"])
    with col3:
        document_path = user_folder / "Processed_ID_Card_Best_angle.jpg"
        if document_path.exists():
            st.image(document_path, caption="Uploaded Document", use_container_width=True)
        else:
            st.error("Document not found.")
    with col4:
        st.subheader("Recorded Video")
        video_path = user_folder / "recorded_videos/live_recording.mp4"
        if video_path.exists():
            st.subheader("Recorded Video")

            def play_video() -> None:
                """Plays the recorded video frame by frame."""
                cap = cv2.VideoCapture(st.session_state.video_path)

                if not cap.isOpened():
                    st.error("Error opening video file.")
                    return

                frame_placeholder = st.empty()  # Placeholder for displaying frames

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break  # Stop when the video ends

                    # Convert BGR (OpenCV format) to RGB (Streamlit format)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Display frame
                    frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

                    # Delay to simulate video playback speed
                    time.sleep(1 / 20)  # Assuming 20 FPS

                cap.release()  # Release video capture
                st.success("Video playback finished.")

            # Play video initially
            play_video()

            # Replay button
            if st.button("Replay Video"):
                play_video()
        else:
            st.warning("No recorded video found.")
