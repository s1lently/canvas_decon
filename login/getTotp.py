import pyotp
import json

def generate_token(otp_key):
    """
    Generates a TOTP token from the provided OTP key string.

    Args:
        otp_key (str): The TOTP secret key string (directly from account_info.json)

    Returns:
        str: The current TOTP token, or None if an error occurs.
    """
    try:
        totp = pyotp.TOTP(otp_key)
        return totp.now()
    except Exception as e:
        print(f"Error generating token from otp_key: {e}")
        return None
