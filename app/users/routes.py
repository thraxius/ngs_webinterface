# users/routes.py
"""
Routes for user management
"""

import logging
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import User, AnalysisJob

logger = logging.getLogger('users')

users_bp = Blueprint('users', __name__)


def require_admin(func):
    """Decorator to require admin role"""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            logger.warning(f"Non-admin user {current_user.username if current_user.is_authenticated else 'anonymous'} attempted admin action")
            return jsonify({'error': 'Keine Berechtigung'}), 403
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@users_bp.route('/api/users')
@login_required
@require_admin
def api_users():
    """API endpoint for user management with proper authorization"""
    try:
        # Get all users with their roles
        users = db.session.query(User).all()
        
        users_data = []
        for user in users:
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email if hasattr(user, 'email') else None,
                'role': user.role.name if user.role else None,
                'is_current_user': user.id == current_user.id,
                'created_at': user.created_at.strftime('%d.%m.%Y %H:%M') if hasattr(user, 'created_at') and user.created_at else 'Unbekannt'
            }
            users_data.append(user_data)
        
        # Sort by username
        users_data.sort(key=lambda x: x['username'].lower())
        
        logger.info(f"Admin {current_user.username} fetched user list ({len(users_data)} users)")
        return jsonify({'users': users_data})
        
    except Exception as e:
        logger.error(f"Error in api_users: {e}")
        return jsonify({'error': 'Fehler beim Laden der Benutzer'}), 500


@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@require_admin
def api_get_user(user_id):
    """API endpoint to get a single user with validation"""
    try:
        user = User.query.get_or_404(user_id)
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email if hasattr(user, 'email') else '',
            'role': 'admin' if user.role and user.role.name == 'admin' else 'user'
        }
        
        logger.info(f"Admin {current_user.username} fetched user data for {user.username}")
        return jsonify(user_data)
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return jsonify({'error': 'Fehler beim Laden des Benutzers'}), 500


@users_bp.route('/api/users', methods=['POST'])
@login_required
@require_admin
def api_create_user():
    """API endpoint to create a new user with proper validation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(key in data for key in ['username', 'email', 'password']):
            return jsonify({'error': 'Fehlende Pflichtfelder'}), 400
        
        # Validate username is not empty
        if not data['username'].strip():
            return jsonify({'error': 'Benutzername darf nicht leer sein'}), 400
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Benutzername bereits vergeben'}), 400
        
        # Check if email already exists (if provided)
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'E-Mail bereits vergeben'}), 400

        # Get next available ID
        last_user = User.query.order_by(User.id.desc()).first()
        next_id = (last_user.id + 1) if last_user else 1
        
        # Create new user
        new_user = User(
            id=next_id,
            username=data['username'].strip(),
            email=data['email'].strip() if data.get('email') else None,
            password_hash=generate_password_hash(data['password']),
            role_id=1 if data.get('role') == 'admin' else 2
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} created new user {new_user.username} with ID {next_id}")
        return jsonify({
            'message': 'Benutzer erfolgreich angelegt',
            'user_id': next_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Fehler beim Anlegen des Benutzers'}), 500


@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@require_admin
def api_update_user(user_id):
    """API endpoint to update a user with proper validation"""
    try:
        data = request.get_json()
        user = User.query.get_or_404(user_id)
        
        # Validate username uniqueness if changed
        if data.get('username') and data['username'] != user.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({'error': 'Benutzername bereits vergeben'}), 400
        
        # Validate email uniqueness if changed
        if data.get('email') and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'E-Mail bereits vergeben'}), 400
        
        # Update fields
        if data.get('username'):
            user.username = data['username'].strip()
        if data.get('email') is not None:
            user.email = data['email'].strip() if data['email'] else None
        
        # Update password if provided
        if data.get('password'):
            user.password_hash = generate_password_hash(data['password'])
            
        # Update role
        if data.get('role'):
            user.role_id = 1 if data['role'] == 'admin' else 2
        
        db.session.commit()
        logger.info(f"Admin {current_user.username} updated user {user.username}")
        return jsonify({'message': 'Benutzer erfolgreich aktualisiert'})
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Fehler beim Aktualisieren'}), 500


@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@require_admin
def api_delete_user(user_id):
    """API endpoint to delete a user with proper validation"""
    try:
        # Prevent self-deletion
        if current_user.id == user_id:
            return jsonify({'error': 'Du kannst dich nicht selbst löschen'}), 400
        
        # Get user to delete
        user = User.query.get_or_404(user_id)
        username = user.username
        
        # Optional: Check if user has running jobs
        running_jobs = AnalysisJob.query.filter_by(
            user_id=user_id,
            status='running'
        ).count()
        
        if running_jobs > 0:
            return jsonify({'error': f'Benutzer hat {running_jobs} laufende Analyse(n)'}), 400
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} deleted user {username} (ID: {user_id})")
        return jsonify({'message': f'Benutzer {username} wurde gelöscht'})
        
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Fehler beim Löschen des Benutzers'}), 500


@users_bp.route('/api/change_password', methods=['POST'])
@login_required
def api_change_password():
    """API endpoint to change own password with proper validation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(key in data for key in ['current_password', 'new_password', 'confirm_password']):
            return jsonify({'error': 'Fehlende Pflichtfelder'}), 400
        
        # Validate current password
        if not check_password_hash(current_user.password_hash, data['current_password']):
            logger.warning(f"User {current_user.username} provided wrong current password")
            return jsonify({'error': 'Aktuelles Passwort ist falsch'}), 400
        
        # Validate new password match
        if data['new_password'] != data['confirm_password']:
            return jsonify({'error': 'Neue Passwörter stimmen nicht überein'}), 400
        
        # Validate password strength
        if len(data['new_password']) < 6:
            return jsonify({'error': 'Passwort muss mindestens 6 Zeichen lang sein'}), 400
        
        # Update password
        current_user.password_hash = generate_password_hash(data['new_password'])
        db.session.commit()
        
        logger.info(f"User {current_user.username} changed their password")
        return jsonify({'message': 'Passwort erfolgreich geändert'})
        
    except Exception as e:
        logger.error(f"Error changing password for {current_user.username}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Fehler beim Ändern des Passworts'}), 500