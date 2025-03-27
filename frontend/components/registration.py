"""Handle functionalities related to Registration."""
import hashlib
import secrets
import sys
import time
from pathlib import Path
from typing import BinaryIO

import cv2
import httpx
import streamlit as st
import yaml
from loguru import logger

sys.path.append(str(Path(__file__).parent.resolve().parent.parent))
from unified_logging.config_types import LoggingConfigs
from unified_logging.logging_client import setup_network_logger_client

FASTAPI_PROCESS_URL = "http://127.0.0.1:8000/validate-otp"
FASTAPI_OCR_URL = "http://127.0.0.1:8000/ocr-content"
# Registration steps
reg_step_1 = 1  # Doc and user name
reg_step_2 = 2  # Remaining account details
reg_step_3 = 3  # Video verification



# Load and configure logging
CONFIG_FILE_PATH = Path.cwd() / "unified_logging" / "configs.toml"
logging_configs = LoggingConfigs.load_from_path(CONFIG_FILE_PATH)
setup_network_logger_client(logging_configs, logger)
logger.info("Registration module initialized.")

def hash_password(password: str) -> str:
    """Hash password using SHA-256 encoding."""
    logger.info("Hashing Password.")
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp() -> str:
    """Generate a 4-digit OTP where consecutive digits are not the same, using a cryptographically secure method."""
    logger.info("Generating OTP for video verification.")
    digits = [secrets.choice("12345")]  # Start with a digit (1-9)
    max_len = 4
    while len(digits) < max_len:
        next_digit = secrets.choice("12345") # Generate next digit (1-9)
        if next_digit not in digits:  # Ensure no consecutive digits are the same
            digits.append(next_digit)

    return "".join(digits)

def switch_to_login() -> None:
    """Change current page to the login page."""
    logger.info("Switching back to login page.")
    st.session_state.page = "login"

def purge_output_folder(output_folder: Path) -> None:
    """Delete all files in the output folder before recording a new video."""
    logger.info(f"Deleting content of {output_folder}")
    for file in output_folder.glob("*"):
        file.unlink()



def record_live_video(user_folder: Path) -> None:
    """Record a 5-second live video and store it in a user-specific folder."""
    logger.info(f"Starting video recording for user: {st.session_state.username}")
    st.write("Record OTP")
    st.write("Please ensure that your hand is centred near the camera and atleast part of your wrist is visible.")

    frame_placeholder = st.empty()  # To show frames live

    video_folder = user_folder / "recorded_videos"
    video_folder.mkdir(exist_ok=True)  # Ensure video directory exists

    video_filename = "live_recording.mp4"
    video_path = video_folder / video_filename

    if st.button("Start Recording"):
        otp = generate_otp()
        st.markdown(f"**Your OTP is: :green[{otp}]**")
        progress_bar = st.progress(0)
        purge_output_folder(video_folder)
        st.toast("Recording video for 5 seconds...")

        cap = cv2.VideoCapture(0)  # Open webcam
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # MP4 codec
        fps = 20.0
        frame_width = int(cap.get(3))
        frame_height = int(cap.get(4))

        out = cv2.VideoWriter(str(video_path), fourcc, fps, (frame_width, frame_height))

        start_time = time.time()
        max_time = 7
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > max_time:
                break

            ret, frame = cap.read()
            if not ret:
                st.write("Failed to capture frame.")
                break

            out.write(frame)  # Write frame to video file

            # Convert frame from BGR to RGB for Streamlit display
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)  # Show frame live

            # Update progress bar
            progress_bar.progress(min(int((elapsed_time / 5) * 100), 100))

        cap.release()  # Release webcam
        out.release()  # Release video writer
        if video_path.exists():
            st.toast("Recording uploaded. Please wait while we process")
            progress_bar.empty()  # Reset progress bar

            # Update YAML to mark registration complete
            yaml_file_path = user_folder / "user_info.yaml"
            with yaml_file_path.open() as yaml_file:
                user_data = yaml.safe_load(yaml_file)

            user_data["reg_complete"] = True
            with yaml_file_path.open("w") as yaml_file:
                yaml.dump(user_data, yaml_file)

            st.toast(":green[Video captured successfully!]")

            # Store video path in session state and navigate to review page
            st.session_state.video_path = str(video_path)
            try:
                with httpx.Client(timeout=1000.0) as client:
                    process_response = client.post(FASTAPI_PROCESS_URL, json ={"otp": otp,"uid":st.session_state.username}).json()
                if process_response.get("valid"):
                    logger.info("OTP validation successful. Redirecting to profile page.")
                    st.switch_page("pages/profile_page.py")
                else:
                    logger.warning("Invalid otp provided")
                    st.toast(":red[Invalid Response received]")
            except ConnectionError: # raise connection errors
                logger.error("Backend connection failed.")
                st.toast("Backend connection failed")
            except Exception:  # raise unexpected errors
                st.toast("An unexpected error occurred. Check log")
                raise

def check_username_availability(user_data_dir: Path, username: str) -> bool:
    """Check if a username is available."""
    user_folder = user_data_dir / username
    yaml_file_path = user_folder / "user_info.yaml"

    if user_folder.exists() and yaml_file_path.exists():
        with yaml_file_path.open() as yaml_file:
            user_data = yaml.safe_load(yaml_file)

        if user_data.get("reg_complete", False):
            return False  # Username already exists and is registered
    return True

def save_user_document(user_data_dir: Path, document: BinaryIO) -> None:
    """Save the document for the user."""
    user_folder = user_data_dir / st.session_state.username
    user_folder.mkdir(parents=True, exist_ok=True)

    with (user_folder / "id_proof.jpg").open("wb") as f:
        f.write(document.read())

    logger.info(f"Document saved for {st.session_state.username}")
    try:
        with httpx.Client(timeout=1000.0) as client:
            process_response = client.post(FASTAPI_OCR_URL, json ={"uid":st.session_state.username}).json()
        if process_response.get("valid"):
            st.toast(":green[Document Registered successfully]")
            st.session_state.ocr = process_response.get("text")
            st.session_state.registration_step = reg_step_2
        else:
            st.toast("Invalid Doc data. Try Again")
    except ConnectionError: # raise connection errors
        st.toast("Backend connection failed")
    except Exception:  # raise unexpected errors
        st.toast("An unexpected error occurred. Check log")
        raise



def save_reg_info(user_data_dir: Path) -> None:
    """Save remaining user information after document upload."""
    st.session_state.fname = st.text_input("Full Name", value=st.session_state.fname)
    st.session_state.phone = st.text_input("Phone Number", value=st.session_state.phone)
    st.session_state.dob = st.date_input("Date of Birth", value=st.session_state.dob)
    st.session_state.password = st.text_input("Password", type="password", value=st.session_state.password)
    st.session_state.confirm_password = st.text_input("Confirm Password", type="password", value=st.session_state.confirm_password)
    user_data_dir = Path.cwd() / "user_data"
    user_folder = user_data_dir / st.session_state.username
    document_path = user_folder / "Processed_ID_Card_Best_angle.jpg"
    col7,col8 = st.columns(2)
    with col7:
        if document_path.exists():
            st.image(document_path, caption="Uploaded Document")
        else:
            st.write("Document not found.")
    with col8:
        st.markdown(f":green[OCR data:] {st.session_state.ocr}")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("Back"):
            st.session_state.registration_step = reg_step_1
    with col5:
        if st.button("Next"):
            if not (st.session_state.phone and st.session_state.dob and st.session_state.password):
                st.toast(":red[Please fill in all fields.]")
                return

            if st.session_state.password != st.session_state.confirm_password:
                st.toast(":red[Passwords do not match.]")
                return

            user_folder = user_data_dir / st.session_state.username
            yaml_file_path = user_folder / "user_info.yaml"

            user_info = {
                "fname": st.session_state.fname,
                "username": st.session_state.username,
                "phone_no": st.session_state.phone,
                "dob": str(st.session_state.dob),
                "password": hash_password(st.session_state.password),
                "reg_complete": False,
            }
            with yaml_file_path.open("w") as yaml_file:
                yaml.dump(user_info, yaml_file)
            st.session_state.registration_step = reg_step_3

def register_page() -> None:
    """Load all the components in the registration page."""
    st.title("User Registration")

    user_data_dir = Path.cwd() / "user_data"
    user_data_dir.mkdir(exist_ok=True)

    if st.session_state.registration_step == reg_step_1:
        st.session_state.username = st.text_input("Username", value=st.session_state.username)
        st.write("Please ensure uploaded document is under 35KB and is in landscape format")
        document = st.file_uploader("Upload Document", type=["jpg", "png"])
        col1, col2, col3, col4 = st.columns(4)
        with col4:
            st.button("Already Registered? Login Here", on_click=switch_to_login)

        with col1:
            if st.button("Next"):
                if not st.session_state.username or not document:
                    st.toast(":red[Please fill all the fields]")
                    return

                if not check_username_availability(user_data_dir, st.session_state.username):
                    st.toast(":red[Username already taken. Please choose another.]")
                    return

                save_user_document(user_data_dir, document)


    elif st.session_state.registration_step == reg_step_2:
        logger.info("Going to 2nd page")
        save_reg_info(user_data_dir)


    elif st.session_state.registration_step == reg_step_3:
        logger.info("Going to 3rd page")
        if st.button("Back"):
            st.session_state.registration_step = reg_step_2
        user_folder = user_data_dir / st.session_state.username
        record_live_video(user_folder)
