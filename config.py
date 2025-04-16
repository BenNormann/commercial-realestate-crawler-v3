import os

# Configuration file path (in user's home directory to ensure write permissions)
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".commercialrealestate")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Default configuration
DEFAULT_CONFIG = {
    'property_types': ['Office', 'Retail', 'Industrial'],
    'min_price': '',
    'max_price': '',
    'location': 'Seattle, WA',
    'websites': ['commercialmls.com', 'loopnet.com'],
    'days_back': 1,
    'save_credentials': False,
    'send_email': False,
    'dark_mode': True,
    # New background task configuration options
    'enable_background': False,
    'background_time': '03:00',
    'hide_terminal': True
} 