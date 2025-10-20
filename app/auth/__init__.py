# auth/__init__.py
"""
Auth module initialization
Exports the auth blueprint
"""

from .routes import auth_bp

__all__ = ['auth_bp']