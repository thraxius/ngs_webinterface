# models.py
"""
Database models for NGS Webinterface
"""

from extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone


class Role(db.Model):
    """User roles for authorization"""
    __tablename__ = 'roles'
    __table_args__ = {'schema': 'ngs'}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    #description = db.Column(db.String(255))
    
    # Relationships
    users = db.relationship('User', back_populates='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    __table_args__ = {'schema': 'ngs'}
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('ngs.roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    role = db.relationship('Role', back_populates='users')
    jobs = db.relationship('AnalysisJob', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def is_admin(self):
        """Check if user has admin role"""
        return self.role and self.role.name == 'admin'


class AnalysisJob(db.Model):
    """Analysis job model for tracking NGS analysis runs"""
    __tablename__ = 'analysis_jobs'
    __table_args__ = {'schema': 'ngs'}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('ngs.users.id'), nullable=False, index=True)
    job_type = db.Column(db.String(50), nullable=False, index=True)  # 'wgs', 'species', etc.
    job_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    run_name = db.Column(db.String(255))
    parameters = db.Column(db.Text)  # JSON string with job parameters
    status = db.Column(db.String(20), default='queued', index=True)  # queued, running, finished, failed
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', back_populates='jobs')
    
    def __repr__(self):
        return f'<AnalysisJob {self.job_code} ({self.status})>'
    
    @property
    def is_running(self):
        """Check if job is currently running"""
        return self.status == 'running'
    
    @property
    def is_finished(self):
        """Check if job is finished (success or failure)"""
        return self.status in ['finished', 'failed']


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        import logging
        logging.getLogger('auth').error(f"Error loading user {user_id}: {e}")
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access attempts"""
    import logging
    logging.getLogger('auth').warning("Unauthorized access attempt")
    return "Bitte melden Sie sich an.", 401