# users/__init__.py
"""
Users module initialization
Exports the users blueprint
"""

from .routes import users_bp

__all__ = ['users_bp']