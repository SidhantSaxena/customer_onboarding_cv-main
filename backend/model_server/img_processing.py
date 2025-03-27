"""Image processing module for OCR and face extraction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    from pathlib import Path

import ssl

import easyocr
import numpy as np
from rich.console import Console

ssl._create_default_https_context = ssl._create_unverified_context


console = Console()

MIN_WORD_LENGTH = 3
MIN_SIMILARITY_SCORE = 0.4
NAME_LENGTH = 3


class ImageProcessor:
    """Handles OCR and image preprocessing.

    - Converting Image to GrayScale, Blurring, and Noise Reduction.
    - Rotating Image in 4 angles to find best angle for image OCR data and face extraction.
    """

    def __init__(self) -> None:
        """Initialize the EasyOCR, CV2 Reader."""
        self.re = re
        self.cv2_module = cv2
        self.reader = easyocr.Reader(["en"])

    def extract_details(self, ocr_text: str) -> dict:
        """Extract Name, DOB, and Aadhaar Number from OCR text."""
        details = {"ocr_text": ocr_text, "Extracted_Name": None, "Extracted_DOB": None, "Extracted_Aadhaar_number": None}

        # Extract DOB (Common Formats)
        dob_match = self.re.search(r"DOB[:\s]*?(\d{2}/\d{2}/\d{4})", ocr_text)
        if dob_match:
            details["dob"] = dob_match.group(1)

        # Extract Aadhaar Number (12-Digit Format)
        aadhaar_match = self.re.search(r"\b\d{4} \d{4} \d{4}\b", ocr_text)
        if aadhaar_match:
            details["aadhaar_number"] = aadhaar_match.group(0)

        name = "best_textNot Found"
        if dob_match:
            words = ocr_text[: dob_match.start()].split()  # Take text before DOB and split into words
            name = " ".join(words[-3:]) if len(words) >= NAME_LENGTH else " ".join(words)
        details["name"] = name

        return details

    def get_text_score(self, text: str) -> float:
        """Assign a score to extracted text.

        Scoring is based on:
        1. Minimum word count.
        2. Avoiding words with mixed uppercase/lowercase patterns.
        3. Filtering out words shorter than 3 characters.
        4. Penalizing non-alphanumeric characters (slashes, special symbols).
        """
        words = text.split()

        # Score 1: Word Count (More words = Higher score)
        word_count_score = len(words) * 2

        # Score 2: Penalize excessive uppercase/lowercase mixing
        mix_penalty = 0
        for word in words:
            if self.re.search(r"(?:[A-Z][a-z]|[a-z][A-Z]){3,}", word):  # 3+ transitions
                mix_penalty += 2  # Reduce score for mixed-case words

        # Score 3: Word Length Bonus
        word_length_bonus = sum(len(word) for word in words) / 5

        # Score 4: Penalize Special Characters (slashes, backslashes, symbols)
        special_char_penalty = sum(3 for char in text if char in "/\\|@#%^&*()_+=[]{}<>")

        # Final Score
        return word_count_score + word_length_bonus - mix_penalty - special_char_penalty

    def rotate_image(self, image: np.ndarray, angle: int) -> np.ndarray:
        """Rotates an image without cropping."""
        h, w = image.shape[:2]

        new_matrix = self.cv2_module.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)

        cos, sin = np.abs(new_matrix[0, 0]), np.abs(new_matrix[0, 1])
        new_w = int(h * sin + w * cos)
        new_h = int(h * cos + w * sin)

        new_matrix[0, 2] += (new_w - w) / 2
        new_matrix[1, 2] += (new_h - h) / 2

        return self.cv2_module.warpAffine(image, new_matrix, (new_w, new_h))

    def preprocess_image(self, image_path: Path) -> tuple[np.ndarray | None, Path]:
        """Preprocess the image for better OCR accuracy."""
        image = self.cv2_module.imread(str(image_path))
        if image is None:
            return None, image_path

        gray = self.cv2_module.cvtColor(image, self.cv2_module.COLOR_BGR2GRAY)
        gray = self.cv2_module.bilateralFilter(gray, 9, 75, 75)

        processed_path = image_path.parent / "Processed_ID_Card.jpg"
        self.cv2_module.imwrite(str(processed_path), gray)
        return gray, processed_path

    def perform_ocr(self, image_path: Path) -> tuple[str, Path]:
        """Try OCR on different rotations and pick the best one."""
        gray, processed_path = self.preprocess_image(image_path)
        if gray is None:
            return "Image could not be processed.", processed_path

        rotations = [0, 90]
        best_score = float("-inf")
        for angle in rotations:
            rotated_text = " ".join(self.reader.readtext(self.rotate_image(gray, angle), detail=0))

            console.print(f"[cyan]Rotation:[/cyan] {angle}°")
            console.print(f"[green]Rotated Text:[/green] {rotated_text}")

            score = self.get_text_score(rotated_text)
            if angle == 0:
                score += 10  # Small bias towards 0°
            console.print(f"[yellow]Score:[/yellow] {score}")

            if score > best_score:
                best_score = score
                best_text = rotated_text
                best_angle = angle

        if best_score == float("-inf"):
            return "No meaningful text found.", processed_path

        extracted_details = self.extract_details(best_text)

        console.print(f"[cyan]Best Rotation:[/cyan] {best_angle}°")
        console.print(f"[green]Extracted Text:[/green] {best_text}")

        best_rotated_image = self.rotate_image(self.cv2_module.imread(str(image_path)), best_angle)
        final_processed_path = image_path.parent / "Processed_ID_Card_Best_angle.jpg"
        self.cv2_module.imwrite(str(final_processed_path), best_rotated_image)

        return extracted_details, final_processed_path


class FaceProcessor:
    """Handles face extraction and comparison using OpenCV.

    - Extracting faces from images.
    - Comparing faces using ORB feature matching.
    """

    def __init__(self) -> None:
        """Initialize the face detector using Haar cascade."""
        self.cv2_module = cv2
        self.face_cascade = self.cv2_module.CascadeClassifier(self.cv2_module.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.bf = self.cv2_module.BFMatcher(self.cv2_module.NORM_HAMMING, crossCheck=True)
        self.orb = self.cv2_module.ORB_create()

    def extract_face(self, image_path: Path, save_path: Path) -> np.ndarray | None:
        """Extract and save face, returning the face region."""
        image = self.cv2_module.imread(str(image_path))
        gray = self.cv2_module.cvtColor(image, self.cv2_module.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        console.print(f"[green]save_path:[/green] {save_path}")
        if len(faces) == 0:
            console.print(f"[red]⚠️ No face detected in image:[/red] {image_path}")
            return None

        # Select the largest detected face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face_image = image[y : y + h, x : x + w]

        face_image = self.cv2_module.resize(face_image, (200, 200))

        self.cv2_module.imwrite(str(save_path), face_image)

        return face_image
