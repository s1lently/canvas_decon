import pyotp
import json

def generate_token(otp_keys_data):
    """
    Generates a TOTP token from the provided otp_keys data structure.
    
    Args:
        otp_keys_data (list): The list of key objects (dicts) from the config.
        
    Returns:
        str: The current TOTP token, or None if an error occurs.
    """
    try:
        otpauth_url = otp_keys_data[0]['otpauthstr']
        secret = otpauth_url.split('secret=')[1]
        totp = pyotp.TOTP(secret)
        return totp.now()
    except Exception as e:
        print(f"Error generating token from otp_keys data: {e}")
        return None
