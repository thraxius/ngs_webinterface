# extensions.py
"""
Centralized Flask extensions initialization
Prevents circular imports by creating extension instances here
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialize extensions (but don't bind to app yet)
db = SQLAlchemy()
login_manager = LoginManager()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
login_manager.login_message_category = 'info'