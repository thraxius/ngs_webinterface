# create_admin_user.py
from app import create_app, db
from app.models import User, Role
from werkzeug.security import generate_password_hash

app = create_app()
app.app_context().push()

admin_role = Role.query.filter_by(name='admin').first()
if not admin_role:
    admin_role = Role(name='admin')
    db.session.add(admin_role)
    db.session.commit()

admin = User(
    username='odin',
    email='admin@example.com',
    password_hash=generate_password_hash('hlidskialf39'),
    role=admin_role
)
db.session.add(admin)
db.session.commit()
print("Admin angelegt.")
