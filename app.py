# app.py
"""
Main application entry point
Flask application factory pattern
"""

import os
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import pytz
from flask import Flask
from dotenv import load_dotenv

from config import Config
from extensions import db, login_manager

logger = logging.getLogger('app')

# Load environment variables
load_dotenv()


def create_app(config_class=Config):
    """
    Application factory function
    Creates and configures the Flask application
    """
    app = Flask(
        __name__,
        template_folder="templates",  # zentraler Template-Ordner
        static_folder="static"        # zentraler Static-Ordner
    )
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register template filters
    register_template_filters(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Log application startup
    logger.info("Flask application created and configured")
    return app


def setup_logging(app):
    """Setup application logging with rotation"""
    log_dir = '/var/log/ngs_webinterface'
    
    # Create log directory if it doesn't exist
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            logger.info(f"Created log directory: {log_dir}")
        except Exception as e:
            logger.error(f"Failed to create log directory: {e}")
            # Fallback to local logs directory
            log_dir = os.path.join(os.path.dirname(__file__), 'logs')
            os.makedirs(log_dir, exist_ok=True)

    # Formatter for all logs
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Different log files configuration
    loggers_config = {
        'app': {
            'file': 'app.log',
            'level': logging.INFO
        },
        'analysis': {
            'file': 'analysis.log',
            'level': logging.INFO
        },
        'auth': {
            'file': 'auth.log',
            'level': logging.INFO
        },
        'ssh': {
            'file': 'ssh_wrapper.log',
            'level': logging.INFO
        },
        'core': {
            'file': 'core.log',
            'level': logging.INFO,
        },
        'history': {
            'file': 'history.log',
            'level': logging.INFO
        },
        'users': {
            'file': 'users.log',
            'level': logging.INFO
        },
        'logs': {
            'file': 'logs.log',
            'level': logging.INFO
        }
    }

    # Setup each logger
    for logger_name, config in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(config['level'])
        
        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()
        
        try:
            handler = RotatingFileHandler(
                os.path.join(log_dir, config['file']),
                maxBytes=1024 * 1024,  # 1MB
                backupCount=10
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            logger.info(f"Logger {logger_name} initialized")
        except Exception as e:
            logger.error(f"Failed to setup logger {logger_name}: {e}")
    
    # Setup Flask app logger
    if not app.debug:
        try:
            app_handler = RotatingFileHandler(
                os.path.join(log_dir, 'app.log'),
                maxBytes=1024 * 1024,
                backupCount=10
            )
            app_handler.setFormatter(formatter)
            app_handler.setLevel(logging.INFO)
            app.logger.addHandler(app_handler)
            app.logger.setLevel(logging.INFO)
        except Exception as e:
            print(f"Failed to setup app logger: {e}")


def register_template_filters(app):
    """Register custom template filters"""
    
    @app.template_filter('localize')
    def localize_datetime_clean(dt):
        """
        Convert UTC datetime to German local time (CET/CEST)
        """
        if dt is None:
            return ""
        
        try:
            # Check if it's currently DST (Daylight Saving Time)
            german_tz = pytz.timezone('Europe/Berlin')
            now = datetime.now()
            is_dst = german_tz.localize(now).dst() != timedelta(0)
            
            # CET (Winter) = UTC+1, CEST (Summer) = UTC+2
            offset_hours = 2 if is_dst else 1
            corrected_dt = dt - timedelta(hours=offset_hours)
            
            return corrected_dt.strftime('%d.%m.%Y %H:%M')
        except Exception as e:

            logger.error(f"Error localizing datetime: {e}")
            return dt.strftime('%d.%m.%Y %H:%M') if dt else ""
    
    @app.template_filter('format_date')
    def format_date(dt, format='%d.%m.%Y'):
        """Format date with custom format"""
        if dt is None:
            return ""
        try:
            return dt.strftime(format)
        except Exception as e:

            logger.error(f"Error formatting date: {e}")
            return str(dt)
    
    @app.template_filter('format_time')
    def format_time(dt, format='%H:%M:%S'):
        """Format time with custom format"""
        if dt is None:
            return ""
        try:
            return dt.strftime(format)
        except Exception as e:

            logger.error(f"Error formatting time: {e}")
            return str(dt)


def register_blueprints(app):
    """Register application blueprints"""
    from app.auth import auth_bp
    from app.analysis import analysis_bp
    from app.history import history_bp
    from app.users import users_bp
    from app.logs import logs_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(logs_bp)
    
    logger.info('Blueprints registered: auth, analysis, history, users, logs')


def register_error_handlers(app):
    """Register global error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):

        logger.warning(f"404 error: {error}")
        return "Seite nicht gefunden", 404
    
    @app.errorhandler(500)
    def internal_error(error):

        logger.error(f"500 error: {error}", exc_info=True)
        db.session.rollback()
        return "Interner Serverfehler", 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        
        logger.error(f"Unexpected error: {error}", exc_info=True)
        db.session.rollback()
        return "Ein unerwarteter Fehler ist aufgetreten", 500


# Create application instance
app = create_app()


if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)