"""
Setup for the Commercial Real Estate Crawler GUI.
This file is used for development purposes.
"""

import os
import sys
from setuptools import setup, find_packages

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Get version from __init__.py
with open(os.path.join(os.path.dirname(__file__), '__init__.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip('"\'')
            break

setup(
    name='commercial-realestate-crawler-gui',
    version=version,
    description='GUI for Commercial Real Estate Crawler',
    author='Your Name',
    packages=find_packages(),
    install_requires=[
        'PyQt5>=5.15.0',
        'selenium>=4.0.0',
        'pywin32>=300',
        'schedule>=1.1.0',
        'beautifulsoup4>=4.10.0',
    ],
    python_requires='>=3.8',
) 