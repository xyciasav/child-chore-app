import os
ADMIN_PASSCODE = os.getenv("ADMIN_PASSCODE", "parent123")


def check_admin_passcode(passcode: str) -> bool:
    """Check if the provided passcode matches the admin passcode."""
    return passcode == ADMIN_PASSCODE

