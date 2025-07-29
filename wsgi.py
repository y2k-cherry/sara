#!/usr/bin/env python3
"""
WSGI Entry Point for Sara Bot
This file ensures Gunicorn can properly find and load the Flask application.
"""

from orchestrator_http import app

if __name__ == "__main__":
    app.run()
