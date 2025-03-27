"""Model Server/Deployment."""

import asyncio
from pathlib import Path

import cv2
import mediapipe as mp
import ray
from ray import serve
from requests import Request
from skimage.metrics import structural_similarity as ssim

from backend.model_server.img_processing import FaceProcessor, ImageProcessor

user_dir = Path.cwd() / "user_data"

# Initialize Ray Serve
ray.init(ignore_reinit_error=True)
serve.start()

MIN_SIMILARITY_SCORE = 0.1

@serve.deployment
class IDOCRProcessor:
    """Ray Serve Deployment to process ID images."""

    def __init__(self) -> None:
        """Preload Models."""
        self.image_processor = ImageProcessor()
        self.face_processor = FaceProcessor()

    async def __call__(self, request: Request) -> dict[str, str | None]:
        """Handle incoming requests for ID OCR processing."""
        try:
            data = await request.json()
            uid = Path(data.get("uid", ""))
            loop = asyncio.get_event_loop()
            extracted_text = await loop.run_in_executor(None, self.id_ocr, uid)
        except RuntimeError as e:
            return {"error": f"Failed to process request: {e!s}"}
        else:
            return extracted_text

    def id_ocr(self, uid: Path) -> tuple[str, Path | None]:
        """Process ID Card, extract OCR text, and save the facial image."""
        # Perform OCR
        doc_path = user_dir /uid / "id_proof.jpg"
        extracted_text, processed_image_path = self.image_processor.perform_ocr(doc_path)

        # Extract Face
        face_save_path = user_dir / uid / "Extracted_ID_Face.jpg"
        id_face = self.face_processor.extract_face(processed_image_path, face_save_path)

        if id_face is None:
            return extracted_text, None

        return extracted_text


@serve.deployment
class VideoOTPProcessor:
    """Ray Serve Deployment to process OTP from video."""

    def __init__(self) -> None:
        """Pre-Loading Models."""
        self.cv2_module = cv2
        self.mp_module = mp
        self.face_cascade = self.cv2_module.CascadeClassifier(
            self.cv2_module.data.haarcascades + "haarcascade_frontalface_default.xml",
        )
        self.ssim = ssim

    async def __call__(self, request: Request) -> dict[str, list[int]]:
        """Handle the incoming request."""
        try:
            data = await request.json()
            uid = Path(data.get("uid", ""))
            video_path = user_dir / uid /  "recorded_videos" / "live_recording.mp4"
            loop = asyncio.get_event_loop()
            otp_sequence = await loop.run_in_executor(
                None,
                self.process_video_and_generate_otp,
                video_path,
                uid,
            )
        except RuntimeError as e:
            return {"error": f"Failed to process request: {e!s}"}
        else:
            return {"otp": otp_sequence}

    def compare_faces(self, uid: Path, webcam_image_path: Path) -> bool:
        """Compare already extracted face images using ORB feature matching."""
        # Load images in grayscale
        id_face = self.cv2_module.imread(str(user_dir / uid /"Extracted_ID_Face.jpg"), self.cv2_module.IMREAD_GRAYSCALE)
        webcam_face = self.cv2_module.imread(str(webcam_image_path), self.cv2_module.IMREAD_GRAYSCALE)

        # Compute SSIM similarity score
        similarity_score, _ = self.ssim(id_face, webcam_face, full=True)

        return similarity_score >= MIN_SIMILARITY_SCORE


    def process_video_and_generate_otp(self, video_path: str, uid: Path) -> list[int]:
        """Process Video and generate OTP."""
        mp_hands = self.mp_module.solutions.hands
        cap = self.cv2_module.VideoCapture(video_path)
        sequence_generated = []
        finger_tips = [4, 8, 12, 16, 20]
        face_valid_path = user_dir / uid / "face_valid"
        face_valid_path.mkdir(parents=True, exist_ok=True)

        with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5, max_num_hands=2) as hands:
            frame_index = 0
            total_frames = int(cap.get(self.cv2_module.CAP_PROP_FRAME_COUNT))
            selected_frames = [0, total_frames // 2, total_frames - 1]

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_index in selected_frames:
                    gray = self.cv2_module.cvtColor(frame, self.cv2_module.COLOR_BGR2GRAY)
                    faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))

                    if faces is not None and len(faces) > 0:
                        offset = 50
                        x, y, w, h = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
                        face = frame[max(y - offset, 0) : min(y + h + offset, frame.shape[0]), max(x - offset, 0) : min(x + w + offset, frame.shape[1])]
                        face_resized = self.cv2_module.resize(face, (200, 200))
                        self.cv2_module.imwrite(str(face_valid_path / f"face_{frame_index}.jpg"), face_resized)

                rgb_frame = self.cv2_module.cvtColor(frame, self.cv2_module.COLOR_BGR2RGB)
                results = hands.process(rgb_frame)

                total_fingers = 0
                if results.multi_hand_landmarks:
                    for hand, handedness in zip(results.multi_hand_landmarks, results.multi_handedness, strict=False):
                        hand_label = handedness.classification[0].label  # 'Left' or 'Right'

                        thumb_up = hand.landmark[4].x < hand.landmark[2].x if hand_label == "Right" else hand.landmark[4].x > hand.landmark[2].x

                        # other fingers
                        fingers_up = sum(
                            1 if hand.landmark[tip].y < hand.landmark[tip - 1].y else 0
                            for tip in finger_tips[1:]  # exclude thumb
                        )

                        total_fingers += fingers_up + (1 if thumb_up else 0)

                sequence_generated.append(min(max(total_fingers, 0), 9))
                frame_index += 1
        image_extensions = (".jpg", ".jpeg", ".png")
        flag=True
        for image_path in face_valid_path.iterdir():
            if image_path.suffix.lower() in image_extensions and image_path.is_file():
                flag = flag & self.compare_faces(uid,image_path)

        cap.release()
        return sequence_generated if flag else []

id_processor_app = IDOCRProcessor.bind()
video_otp_processor_app = VideoOTPProcessor.bind()

serve.run(id_processor_app)
serve.run(video_otp_processor_app)
