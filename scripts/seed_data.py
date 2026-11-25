#!/usr/bin/env python
"""
Standalone seed script that initializes Django and runs the seed_data management command.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    print("Running seed_data management command...")
    call_command('seed_data')
