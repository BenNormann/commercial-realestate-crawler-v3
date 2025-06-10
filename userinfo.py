"""
Store user email credentials for sending property notifications.
This file should be added to .gitignore to prevent accidental commits of sensitive information.
"""

# Default values - these will be set by the configuration GUI
EMAIL = ""
EMAIL_PASSWORD = ""

def get_email_credentials():
    """
    Return the current email credentials
    
    Returns:
        tuple: (email, password)
    """
    return EMAIL, EMAIL_PASSWORD

def set_email_credentials(email, password):
    """
    Update the email credentials and save them to the file
    
    Args:
        email (str): User's email address
        password (str): User's email password or app password
    """
    global EMAIL, EMAIL_PASSWORD
    EMAIL = ""
    EMAIL_PASSWORD = ""
