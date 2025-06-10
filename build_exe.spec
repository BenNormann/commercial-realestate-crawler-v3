# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get the project root directory
project_root = os.path.abspath('.')

# Collect all data files
datas = []

# Add config directory (but exclude debug files)
config_dir = os.path.join(project_root, 'config')
if os.path.exists(config_dir):
    # Only add .json files from config, exclude .log files
    for file in os.listdir(config_dir):
        if file.endswith('.json'):
            datas.append((os.path.join(config_dir, file), 'config'))

# Add chromedriver if it exists
chromedriver_path = os.path.join(project_root, 'chromedriver.exe')
if os.path.exists(chromedriver_path):
    datas.append((chromedriver_path, '.'))

# Add any other data files you might have
# datas.append((os.path.join(project_root, 'assets'), 'assets'))

# Hidden imports for PyQt5, Selenium, and other dependencies
hiddenimports = [
    'PyQt5.QtCore',
    'PyQt5.QtGui', 
    'PyQt5.QtWidgets',
    'PyQt5.sip',
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.chrome.service',
    'selenium.webdriver.chrome.options',
    'selenium.webdriver.common.by',
    'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions',
    'selenium.common.exceptions',
    'requests',
    'json',
    'datetime',
    'smtplib',
    'email.mime.text',
    'email.mime.multipart',
    'subprocess',
    'threading',
    'time',
    'os',
    'sys',
    'pathlib',
    'userinfo',
    'debug.logger',
    'scraper.scraper_manager',
    'scraper.loopnet_scraper',
    'scraper.commercialmls_scraper',
    'utils.email_sender',
    'task_scheduler.task_manager'
]

# Collect all submodules from your project (excluding service folder)
hiddenimports.extend(collect_submodules('scraper'))
hiddenimports.extend(collect_submodules('utils'))
hiddenimports.extend(collect_submodules('debug'))
hiddenimports.extend(collect_submodules('task_scheduler'))

block_cipher = None

a = Analysis(
    ['gui/app.py'],  # Main entry point
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'service',          # Exclude unused service folder
        'debug.*.log',      # Exclude debug log files
        '*.log',            # Exclude all log files
        'userinfo copy.py', # Exclude credentials backup file
        'test',             # Exclude test files if any
        'tests',            # Exclude tests folder if any
        '.git',             # Exclude git folder
        '.gitignore',       # Exclude gitignore
        'README.md',        # Exclude readme
        '__pycache__',      # Exclude cache
        '*.pyc',            # Exclude compiled python files
        '*.pyo',            # Exclude optimized python files
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CommercialRealEstateCrawler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: icon='path/to/icon.ico'
) 