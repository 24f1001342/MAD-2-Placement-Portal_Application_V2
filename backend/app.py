from flask import Flask
from extensions import db, jwt, mail, cors
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    from resources.auth import auth_bp
    from resources.admin import admin_bp
    from resources.company import company_bp
    from resources.student import student_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(company_bp, url_prefix='/api/company')
    app.register_blueprint(student_bp, url_prefix='/api/student')

    with app.app_context():
        import models
        db.create_all()
        seed_admin()

    return app


def seed_admin():
    from models import User
    from sqlalchemy import select
    existing = db.session.execute(select(User).filter_by(role='admin')).scalar_one_or_none()
    if not existing:
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_approved=True,
            is_blacklisted=False
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Admin seeded | email: admin@example.com | password: admin123')


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)