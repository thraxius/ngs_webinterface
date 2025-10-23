# logs/routes.py
"""
Routes for log file management
"""

import os
import logging
from flask import Blueprint, jsonify
from flask_login import login_required, current_user

logger = logging.getLogger('logs')

logs_bp = Blueprint('logs', __name__)


def require_admin(func):
    """Decorator to require admin role"""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            logger.warning(f"Non-admin user {current_user.username if current_user.is_authenticated else 'anonymous'} attempted admin action")
            return jsonify({'error': 'Keine Berechtigung'}), 403
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@logs_bp.route('/api/logs/<log_type>')
@login_required
@require_admin
def api_logs(log_type):
    """API endpoint to fetch log files with proper authorization"""
    log_files = {
        'analysis': 'analysis.log',
        'auth': 'auth.log',
        'ssh': 'ssh_wrapper.log',
        'app': 'app.log',
        'core': 'core.log',
        'history': 'history.log',
        'users': 'users.log',
        'logs': 'logs.log'
    }

    if log_type not in log_files:
        logger.warning(f"Invalid log type requested: {log_type}")
        return jsonify({'error': 'Ungültiger Log-Typ'}), 400

    try:
        log_path = os.path.join('/var/log/ngs_webinterface', log_files[log_type])
        
        if not os.path.exists(log_path):
            logger.warning(f"Log file not found: {log_path}")
            return jsonify({'content': f'Log-Datei {log_type} nicht gefunden'})

        # Read last 1000 lines
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            content = ''.join(lines[-1000:])

        logger.info(f"Admin {current_user.username} accessed {log_type} log")
        return jsonify({'content': content})

    except (OSError, PermissionError) as e:
        logger.error(f"Error reading log file {log_type}: {e}")
        return jsonify({'error': 'Fehler beim Lesen der Log-Datei'}), 500
    except Exception as e:
        logger.error(f"Unexpected error reading log file {log_type}: {e}")
        return jsonify({'error': 'Unerwarteter Fehler beim Lesen der Log-Datei'}), 500