"""
Service package for the Commercial Real Estate Crawler.

This package provides functionality for managing the Windows service.
"""

from .service import ScraperService, install

# Functions that should be available at package level
__all__ = ['ScraperService', 'install']

# Version information
__version__ = '1.0.0' 