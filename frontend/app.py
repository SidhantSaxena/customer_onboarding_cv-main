"""Frontend Homepage."""
import sys
from pathlib import Path

import streamlit as st
from components.login import login_page
from components.registration import register_page
from loguru import logger

sys.path.append(str(Path(__file__).parent.resolve().parent))
from unified_logging.config_types import LoggingConfigs
from unified_logging.logging_client import setup_network_logger_client

# Page config
st.set_page_config(page_title="Customer Onboarding", layout="centered", initial_sidebar_state="collapsed")

# Load and configure logging
CONFIG_FILE_PATH = Path.cwd() / "unified_logging" / "configs.toml"
logging_configs = LoggingConfigs.load_from_path(CONFIG_FILE_PATH)
setup_network_logger_client(logging_configs, logger)
logger.info("Frontend started.")

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "login"
    logger.info("Session state initialized with default page: login")

if "registration_step" not in st.session_state:
    st.session_state.registration_step = 1

if "username" not in st.session_state:
    st.session_state.username = ""

if "phone" not in st.session_state:
    st.session_state.phone = ""

if "dob" not in st.session_state:
    st.session_state.dob = None

if "password" not in st.session_state:
    st.session_state.password = ""

if "confirm_password" not in st.session_state:
    st.session_state.confirm_password = ""

if "fname" not in st.session_state:
    st.session_state.fname = ""

if "ocr" not in st.session_state:
    st.session_state.ocr = ""


logger.info(f"User navigating to {st.session_state.page} page.")

if st.session_state.page == "register":
    register_page()
elif st.session_state.page == "login":
    login_page()
