from flask import Flask,send_from_directory
from extensions import db, jwt, mail, cors
from config import Config
from celery import Celery
from celery.schedules import crontab
import os

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker='redis://localhost:6379/0',
        backend='redis://localhost:6379/0')

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


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
    existing = db.session.execute(
        select(User).filter_by(role='admin')
    ).scalar_one_or_none()
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


flask_app = create_app()
celery = make_celery(flask_app)

from tasks import create_tasks
send_daily_reminders, send_monthly_report, export_applications_csv = create_tasks(celery, flask_app)


# use crontab for real scheduling in production
# celery.conf.beat_schedule = {
#     'daily-reminder': {
#         'task': 'tasks.send_daily_reminders',
#         'schedule': crontab(minute=0, hour=8),
#     },
#     'monthly-report': {
#         'task': 'tasks.send_monthly_report',
#         'schedule': crontab(day_of_month=1, hour=0, minute=0),
#     },
# }

celery.conf.beat_schedule = {
    'daily-reminder': {
        'task': 'tasks.send_daily_reminders',
        'schedule': 10.0,   # every 10 seconds - shows live firing
    },
    'monthly-report': {
        'task': 'tasks.send_monthly_report',
        'schedule': 10.0,
    },
}

@flask_app.route('/resume/<filename>')
def serve_resume(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)


@flask_app.route('/manifest')
def manifest():
    return send_from_directory(Config.FRONTEND_DIR, 'manifest.json')



@flask_app.route('/')
def index():
    return send_from_directory(Config.FRONTEND_DIR,'index.html')    

@flask_app.route('/app.js')
def appjs():
    return send_from_directory(Config.FRONTEND_DIR, 'app.js')
if __name__ == '__main__':
    flask_app.run(debug=True)