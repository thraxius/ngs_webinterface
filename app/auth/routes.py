# auth/routes.py
"""
Authentication routes (login, register, logout)
Extracted from original auth.py
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

from extensions import db
from models import User

logger = logging.getLogger('auth')

auth_bp = Blueprint('auth', __name__)


# Login Form Klasse definieren
class LoginForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Anmelden')

# Register Form Klasse definieren (nach LoginForm)
class RegistrationForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired()])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    password2 = PasswordField('Passwort wiederholen', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrieren')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if current_user.is_authenticated:
        return redirect(url_for('analysis.analysis'))
    
    # Login Form erstellen
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            logger.info(f"User {username} logged in successfully")
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('analysis.analysis'))
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            flash('Ungültiger Benutzername oder Passwort', 'danger')
    
    # Form an Template übergeben
    return render_template('login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register route"""
    if current_user.is_authenticated:
        return redirect(url_for('analysis.analysis'))
    
    # Registration Form erstellen
    form = RegistrationForm()
    
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        # Validation
        if not all([username, email, password]):
            flash('Bitte alle Felder ausfüllen', 'danger')
            return render_template('register.html', form=form)
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben', 'danger')
            return render_template('register.html', form=form)
        
        if User.query.filter_by(email=email).first():
            flash('E-Mail bereits registriert', 'danger')
            return render_template('register.html', form=form)
        
        try:
            # Get next available ID
            last_user = User.query.order_by(User.id.desc()).first()
            next_id = (last_user.id + 1) if last_user else 1
            
            # Create new user (default role_id=2 for regular user)
            new_user = User(
                id=next_id,
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role_id=2  # Regular user role
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"New user registered: {username} (ID: {next_id})")
            flash('Registrierung erfolgreich! Du kannst dich jetzt anmelden.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Error during registration: {e}")
            db.session.rollback()
            flash('Fehler bei der Registrierung', 'danger')
    
    # Form an Template übergeben
    return render_template('register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout route"""
    username = current_user.username
    logout_user()
    logger.info(f"User {username} logged out")
    flash('Erfolgreich abgemeldet', 'info')
    return redirect(url_for('auth.login'))