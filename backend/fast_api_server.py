"""FASTAPI SERVER."""

import asyncio
import sys
from http import HTTPStatus
from pathlib import Path

import httpx
import toml
from aiocache import cached
from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel, Field
from rich.console import Console

from backend.otp_validation import is_valid_otp

sys.path.append(str(Path(__file__).parent.resolve().parent))
from unified_logging.config_types import LoggingConfigs
from unified_logging.logging_client import setup_network_logger_client

# Load and configure logging
CONFIG_FILE_PATH = Path.cwd() / "unified_logging" / "configs.toml"
logging_configs = LoggingConfigs.load_from_path(CONFIG_FILE_PATH)
setup_network_logger_client(logging_configs, logger)
logger.info("Backend started.")

console = Console()
config = toml.load("route_config.toml")
RAY_OTP_SERVICE_URL = config["server"]["RAY_OTP_SERVICE_URL"]
RAY_OCR_SERVICE_URL = config["server"]["RAY_OCR_SERVICE_URL"]
app = FastAPI()

class OCRRequest(BaseModel):
    """Schema for OCR validation request."""

    uid: str = Field(..., min_length=1, max_length=255, description="Path to the user file.")

class OTPRequest(BaseModel):
    """Schema for OTP validation request."""

    otp: str = Field(..., min_length=1, max_length=4, description="OTP should be exactly 4 digits.")
    uid: str = Field(..., min_length=1, max_length=255, description="Path to the user file.")

class FaceValid(BaseModel):
    """Schema for face similarity validation."""

    uid: Path = Field(..., min_length=1, max_length=255, description="Path to the user file.")
    ref_path:Path = Field(..., min_length=1, max_length=255, description="Path to the user reference file.")

@app.post("/validate-otp")
@cached(ttl=60)
async def validate_otp(request: OTPRequest) -> dict[str, bool]:
    """Validate OTP by processing the video file asynchronously."""
    logger.info(f"Received OTP validation request for UID: {request.uid}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(RAY_OTP_SERVICE_URL, json=request.model_dump())
        generated_otp=[]
        if response.status_code == HTTPStatus.OK:
            console.print(response.json())
            generated_otp = response.json().get("otp")
            logger.info(f"OTP response received successfully for UID: {request.uid}")
    console.print(generated_otp)
    is_valid = await asyncio.to_thread(is_valid_otp, generated_otp, list(request.otp))
    logger.info(f"OTP validation result for UID {request.uid}: {is_valid}")
    return {"valid": is_valid}

@app.post("/ocr-content")
@cached(ttl=60)
async def ocr_content(request: OCRRequest) -> dict:
    """Validate OCR by processing the document file asynchronously."""
    logger.info(f"Received OCR request for UID: {request.uid}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(RAY_OCR_SERVICE_URL, json=request.model_dump())
        generated_ocr=""
        valid=False
        if response.status_code == HTTPStatus.OK:
            console.print(response.json())
            generated_ocr = response.json().get("ocr_text")
            valid=True
            logger.info(f"OCR response received successfully for UID: {request.uid}")
    return {"text": generated_ocr, "valid":valid}

if __name__ == "__main__":
    logger.info("Starting FastAPI server on 127.0.0.1:8000")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
