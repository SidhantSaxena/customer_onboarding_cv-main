"""VALIDATION UTILS."""


def is_valid_otp(otp_processed: list[int], expected_otp: list[int]) -> bool:
    """Check if the processed OTP matches the expected OTP."""
    last_occurrence = {str(val): idx for idx, val in enumerate(otp_processed)}
    sorted_values = sorted(last_occurrence.items(), key=lambda x: x[1])
    otp_generated = [val for val, _ in sorted_values if val in expected_otp]
    return expected_otp == otp_generated
