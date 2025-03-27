"""Load Test Ray Server."""
import json

from locust import HttpUser, between, task


class IDOCRProcessorTest(HttpUser):
    """Locust test class for IDOCRProcessor."""

    wait_time = between(1, 3)

    @task
    def test_id_ocr_processor(self) -> None:
        """Task to test ID OCR processing endpoint."""
        payload = json.dumps({"uid": "ashisht"})
        headers = {"Content-Type": "application/json"}
        self.client.post("http://localhost:8055/IDOCRProcessor", data=payload, headers=headers)


class VideoOTPProcessorTest(HttpUser):
    """Locust test class for VideoOTPProcessor."""

    wait_time = between(1, 3)

    @task
    def test_video_otp_processor(self) -> None:
        """Task to test video OTP processing endpoint."""
        payload = json.dumps({"uid": "ashisht"})
        headers = {"Content-Type": "application/json"}
        self.client.post("http://localhost:8055/VideoOTPProcessor", data=payload, headers=headers)
