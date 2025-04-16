"""
Service package for the Commercial Real Estate Crawler.

This package provides functionality for managing the Windows service.
"""

from .service import (
    install_service_gui as install_service,
    remove_service_gui as remove_service,
    start_service_gui as start_service,
    stop_service_gui as stop_service,
    get_service_status,
    show_installation_progress_dialog
)

# Version information
__version__ = '1.0.0' 