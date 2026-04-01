from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from sqlalchemy import select, or_
from functools import wraps
from datetime import datetime
import os

student_bp = Blueprint('student', __name__)


def student_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'student':
            return jsonify({'error': 'Student access required'}), 403
        identity = get_jwt_identity()
        from models import User
        user = db.session.get(User, int(identity))
        if user.is_blacklisted:
            return jsonify({'error': 'Account blacklisted'}), 403
        return f(*args, **kwargs)
    return decorated


def get_student_profile():
    identity = get_jwt_identity()
    from models import Student
    return db.session.execute(
        select(Student).filter_by(user_id=int(identity))
    ).scalar_one_or_none()


@student_bp.route('/dashboard', methods=['GET'])
@student_required
def dashboard():
    from models import Student, PlacementDrive, Application, Company
    student = get_student_profile()

    search = request.args.get('search', '')
    query = select(PlacementDrive).join(Company).where(
        PlacementDrive.status == 'Approved',
        PlacementDrive.application_deadline >= datetime.now()
    ).distinct()

    if search:
        query = query.where(or_(
            PlacementDrive.job_title.ilike(f'%{search}%'),
            PlacementDrive.required_skills.ilike(f'%{search}%'),
            Company.company_name.ilike(f'%{search}%')
        ))

    drives = db.session.execute(query).scalars().all()

    applications = db.session.execute(
        select(Application).filter_by(student_id=student.id)
    ).scalars().all()

    applied_drive_ids = [a.placement_drive_id for a in applications]

    return jsonify({
        'student': {
            'id': student.id,
            'full_name': student.full_name,
            'roll_number': student.roll_number,
            'degree': student.degree or '—',
            'branch': student.branch or '—',
            'cgpa': student.cgpa or '—',
            'skills': student.skills or '—',
            'resume': student.resume_filename or None
        },
        'drives': [{
            'id': d.id,
            'job_title': d.job_title,
            'company': d.company.company_name,
            'salary_range': d.salary_range or '—',
            'required_skills': d.required_skills or '—',
            'eligibility_criteria': d.eligibility_criteria or '—',
            'deadline': d.application_deadline.strftime('%Y-%m-%d'),
            'already_applied': d.id in applied_drive_ids
        } for d in drives],
        'applications': [{
            'id': a.id,
            'job_title': a.placement_drive.job_title,
            'company': a.placement_drive.company.company_name,
            'status': a.status,
            'applied_at': a.applied_at.strftime('%Y-%m-%d')
        } for a in applications]
    }), 200


@student_bp.route('/apply/<int:drive_id>', methods=['POST'])
@student_required
def apply(drive_id):
    from models import PlacementDrive, Application
    student = get_student_profile()

    drive = db.session.execute(
        select(PlacementDrive).where(
            PlacementDrive.id == drive_id,
            PlacementDrive.status == 'Approved'
        )
    ).scalar_one_or_none()

    if not drive:
        return jsonify({'error': 'Drive not found or not available'}), 404

    existing = db.session.execute(
        select(Application).where(
            Application.student_id == student.id,
            Application.placement_drive_id == drive_id
        )
    ).scalar_one_or_none()

    if existing:
        return jsonify({'error': 'Already applied for this drive'}), 409

    new_application = Application(
        student_id=student.id,
        placement_drive_id=drive_id,
        status='Applied'
    )
    db.session.add(new_application)
    db.session.commit()
    return jsonify({'message': f'Successfully applied for {drive.job_title}'}), 201


@student_bp.route('/applications', methods=['GET'])
@student_required
def applications():
    from models import Application
    student = get_student_profile()
    applications = db.session.execute(
        select(Application).filter_by(student_id=student.id)
    ).scalars().all()

    return jsonify([{
        'id': a.id,
        'job_title': a.placement_drive.job_title,
        'company': a.placement_drive.company.company_name,
        'salary_range': a.placement_drive.salary_range or '—',
        'status': a.status,
        'applied_at': a.applied_at.strftime('%Y-%m-%d'),
        'note': a.note or ''
    } for a in applications]), 200


@student_bp.route('/placements', methods=['GET'])
@student_required
def placements():
    from models import Placement
    student = get_student_profile()
    placements = db.session.execute(
        select(Placement).filter_by(student_id=student.id)
    ).scalars().all()

    return jsonify([{
        'id': p.id,
        'job_title': p.job_title,
        'company': p.company.company_name,
        'salary': p.salary or '—',
        'placed_at': p.placed_at.strftime('%Y-%m-%d'),
        'status': p.status
    } for p in placements]), 200


@student_bp.route('/profile', methods=['PUT'])
@student_required
def edit_profile():
    from models import Student
    student = get_student_profile()
    data = request.get_json()

    student.full_name = data.get('full_name', student.full_name).strip()
    student.degree = data.get('degree', student.degree)
    student.branch = data.get('branch', student.branch)
    student.skills = data.get('skills', student.skills)
    cgpa = data.get('cgpa')
    if cgpa is not None:
        student.cgpa = float(cgpa)

    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'}), 200


@student_bp.route('/profile/resume', methods=['POST'])
@student_required
def upload_resume():
    student = get_student_profile()

    if 'resume' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    resume = request.files['resume']
    if not resume.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files allowed'}), 400

    filename = f"{student.roll_number}_resume.pdf"
    upload_folder = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'resumes')
    os.makedirs(upload_folder, exist_ok=True)
    resume.save(os.path.join(upload_folder, filename))

    student.resume_filename = filename
    db.session.commit()
    return jsonify({'message': 'Resume uploaded successfully'}), 200