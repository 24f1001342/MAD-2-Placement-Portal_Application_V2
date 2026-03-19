from extensions import db
from flask_jwt_extended import JWTManager
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False) 
    is_approved = db.Column(db.Boolean, default=False)
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    company_profile = db.relationship('Company', backref='user', uselist=False)
    student_profile = db.relationship('Student', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} | {self.role}>'


class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(150), nullable=True)
    hr_contact = db.Column(db.String(150), nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    drives = db.relationship('PlacementDrive', backref='company', lazy=True)

    def __repr__(self):
        return f'<Company {self.company_name}>'


class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    degree = db.Column(db.String(100), nullable=True)
    branch = db.Column(db.String(100), nullable=True)
    cgpa = db.Column(db.Float, nullable=True)
    skills = db.Column(db.Text, nullable=True)
    resume_filename = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    applications = db.relationship('Application', backref='student', lazy=True)
    placements = db.relationship('Placement', backref='student', lazy=True)

    def __repr__(self):
        return f'<Student {self.full_name}>'


class PlacementDrive(db.Model):
    __tablename__ = 'placement_drive'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=True)
    eligibility_criteria = db.Column(db.Text, nullable=True)
    required_skills = db.Column(db.Text, nullable=True)
    salary_range = db.Column(db.String(100), nullable=True)
    application_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # Pending, Approved, Closed, Rejected
    created_at = db.Column(db.DateTime, default=datetime.now)

    applications = db.relationship('Application', backref='placement_drive', lazy=True)

    def __repr__(self):
        return f'<PlacementDrive {self.job_title}>'


class Application(db.Model):
    __tablename__ = 'application'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    placement_drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    status = db.Column(db.String(50), default='Applied')  # Applied, Shortlisted, Interview, Selected, Rejected
    note = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime, default=datetime.now)

    placement = db.relationship('Placement', backref='application', uselist=False)

    __table_args__ = (db.UniqueConstraint('student_id', 'placement_drive_id', name='unique_application'),)

    def __repr__(self):
        return f'<Application Student:{self.student_id} Drive:{self.placement_drive_id}>'


class Placement(db.Model):
    __tablename__ = 'placement'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    salary = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default='Placed')
    placed_at = db.Column(db.DateTime, default=datetime.now)

    company = db.relationship('Company', backref='placements')

    def __repr__(self):
        return f'<Placement Student:{self.student_id}>'