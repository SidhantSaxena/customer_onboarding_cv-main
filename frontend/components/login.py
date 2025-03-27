"""Handle functionalities related to Login."""
import sys
from pathlib import Path

import streamlit as st
import yaml
from components.registration import hash_password, record_live_video
from loguru import logger

sys.path.append(str(Path(__file__).parent.resolve().parent.parent))
from unified_logging.config_types import LoggingConfigs
from unified_logging.logging_client import setup_network_logger_client

# Load and configure logging
CONFIG_FILE_PATH = Path.cwd() / "unified_logging" / "configs.toml"
logging_configs = LoggingConfigs.load_from_path(CONFIG_FILE_PATH)
setup_network_logger_client(logging_configs, logger)
logger.info("Login module initialized.")

login_step_fin = 2
login_step_in = 1
def switch_to_register() -> None:
    """Change current page to the registration page."""
    st.session_state.page = "register"
    st.session_state.registration_step = 1
    st.session_state.username = ""
    st.session_state.phone = ""
    st.session_state.dob = None
    logger.debug("Switching Page for registration.")

def authenticate_user(user_data_dir: Path, username: str, password: str) -> bool:
    """Verify username and password using SHA-256 hashing."""
    user_folder = user_data_dir / username
    yaml_file_path = user_folder / "user_info.yaml"
    logger.info(f"Authenticating user: {username}")
    if not yaml_file_path.exists():
        logger.warning(f"Authentication failed. User '{username}' not found.")
        return False  # User does not exist

    with yaml_file_path.open() as yaml_file:
        user_data = yaml.safe_load(yaml_file)

    stored_hashed_password = user_data.get("password")
    if not stored_hashed_password:
        logger.error(f"Authentication failed. No password stored for user '{username}'.")
        return False  # No password found

    # Hash input password and compare it with stored hash
    hashed_input_password = hash_password(password)
    logger.info(f"Authentication status: {stored_hashed_password == hashed_input_password}")
    return stored_hashed_password == hashed_input_password

def login_page() -> None:
    """Allow an existing user to login with two-step authentication."""
    st.title("User Login")

    user_data_dir = Path.cwd() / "user_data"

    if "login_step" not in st.session_state:
        st.session_state.login_step = login_step_in
        logger.info("Session state initialized.")
    if "login_username" not in st.session_state:
        st.session_state.login_username = ""
    if "login_password" not in st.session_state:
        st.session_state.login_password = ""

    if st.session_state.login_step == login_step_in:
        col1, col2, col3, col4 = st.columns(4)
        with col4:
            st.button("New User? Register Here", on_click=switch_to_register)
        # Username and Password Authentication
        st.session_state.login_username = st.text_input("Username", value=st.session_state.login_username)
        st.session_state.login_password = st.text_input("Password", type="password", value=st.session_state.login_password)

        if st.button("Login"):
            # This authenticate_user() functionality can be moved to backend via API
            logger.info(f"Login request from {st.session_state.login_username}")
            if authenticate_user(user_data_dir, st.session_state.login_username, st.session_state.login_password):
                st.toast("Password Verified")
                st.session_state.username = st.session_state.login_username
                st.session_state.login_step = login_step_fin  # Move to next step
            else:
                st.error("Invalid username or password. Please try again.")

    elif st.session_state.login_step == login_step_fin:
        # Live Video Verification
        logger.info(f"User '{st.session_state.login_username}' reached face verification step.")
        st.success(f"Welcome {st.session_state.login_username}! Proceeding with face verification.")
        user_folder = user_data_dir / st.session_state.login_username
        record_live_video(user_folder)
        logger.info(f"Face verification process started for user '{st.session_state.login_username}'.")




