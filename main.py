#!/usr/bin/env python3
"""
Botsprinter - Printer Supplies Inventory Management System
Main entry point for the application.
"""

import sys
import os
import logging

logging.basicConfig(level=logging.ERROR)

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.botsprinter import main
except ImportError:
    # Fallback for direct execution
    from botsprinter import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logging.error(f"Ошибка запуска приложения: {e}")
        sys.exit(1)
