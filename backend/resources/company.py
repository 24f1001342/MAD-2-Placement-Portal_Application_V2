from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from extensions import db
from sqlalchemy import select
from functools import wraps
from datetime import datetime

company_bp = Blueprint('company', __name__)


def company_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        claims = get_jwt()
        if claims.get('role') != 'company':
            return jsonify({'error': 'Company access required'}), 403
        identity = get_jwt_identity()
        from models import User
        user = db.session.get(User, int(identity))
        if not user.is_approved:
            return jsonify({'error': 'Account pending approval'}), 403
        if user.is_blacklisted:
            return jsonify({'error': 'Account blacklisted'}), 403
        return f(*args, **kwargs)
    return decorated


def get_company_profile():
    identity = get_jwt_identity()
    from models import Company
    return db.session.execute(
        select(Company).filter_by(user_id=int(identity))
    ).scalar_one_or_none()


@company_bp.route('/dashboard', methods=['GET'])
@company_required
def dashboard():
    from models import PlacementDrive, Application
    company = get_company_profile()
    drives = db.session.execute(
        select(PlacementDrive).filter_by(company_id=company.id)
    ).scalars().all()

    drive_data = []
    for drive in drives:
        app_count = len(drive.applications)
        drive_data.append({
            'id': drive.id,
            'job_title': drive.job_title,
            'status': drive.status,
            'deadline': drive.application_deadline.strftime('%Y-%m-%d'),
            'salary_range': drive.salary_range or '—',
            'app_count': app_count
        })

    return jsonify({
        'company': {
            'id': company.id,
            'company_name': company.company_name,
            'industry': company.industry or '—',
            'hr_contact': company.hr_contact or '—',
            'website': company.website or '—',
            'location': company.location or '—',
            'description': company.description or '—'
        },
        'drives': drive_data
    }), 200


@company_bp.route('/drive', methods=['POST'])
@company_required
def create_drive():
    from models import PlacementDrive
    company = get_company_profile()
    data = request.get_json()

    job_title = data.get('job_title', '').strip()
    job_description = data.get('job_description', '').strip()
    eligibility_criteria = data.get('eligibility_criteria', '').strip()
    required_skills = data.get('required_skills', '').strip()
    salary_range = data.get('salary_range', '').strip()
    deadline_str = data.get('application_deadline', '')

    if not job_title or not deadline_str:
        return jsonify({'error': 'Job title and deadline are required'}), 400

    try:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid deadline format. Use YYYY-MM-DD'}), 400

    new_drive = PlacementDrive(
        company_id=company.id,
        job_title=job_title,
        job_description=job_description,
        eligibility_criteria=eligibility_criteria,
        required_skills=required_skills,
        salary_range=salary_range,
        application_deadline=deadline,
        status='Pending'
    )
    db.session.add(new_drive)
    db.session.commit()
    return jsonify({'message': 'Drive created. Awaiting admin approval.', 'id': new_drive.id}), 201


@company_bp.route('/drive/<int:drive_id>', methods=['PUT'])
@company_required
def edit_drive(drive_id):
    from models import PlacementDrive
    company = get_company_profile()
    drive = db.session.execute(
        select(PlacementDrive).where(
            PlacementDrive.id == drive_id,
            PlacementDrive.company_id == company.id
        )
    ).scalar_one_or_none()

    if not drive:
        return jsonify({'error': 'Drive not found'}), 404

    data = request.get_json()
    drive.job_title = data.get('job_title', drive.job_title).strip()
    drive.job_description = data.get('job_description', drive.job_description)
    drive.eligibility_criteria = data.get('eligibility_criteria', drive.eligibility_criteria)
    drive.required_skills = data.get('required_skills', drive.required_skills)
    drive.salary_range = data.get('salary_range', drive.salary_range)
    drive.status = 'Pending'

    deadline_str = data.get('application_deadline')
    if deadline_str:
        try:
            drive.application_deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid deadline format'}), 400

    db.session.commit()
    return jsonify({'message': 'Drive updated and resubmitted for approval'}), 200


@company_bp.route('/drive/<int:drive_id>/close', methods=['POST'])
@company_required
def close_drive(drive_id):
    from models import PlacementDrive
    company = get_company_profile()
    drive = db.session.execute(
        select(PlacementDrive).where(
            PlacementDrive.id == drive_id,
            PlacementDrive.company_id == company.id
        )
    ).scalar_one_or_none()

    if not drive:
        return jsonify({'error': 'Drive not found'}), 404

    drive.status = 'Closed'
    db.session.commit()
    return jsonify({'message': 'Drive closed'}), 200


@company_bp.route('/drive/<int:drive_id>/delete', methods=['DELETE'])
@company_required
def delete_drive(drive_id):
    from models import PlacementDrive
    company = get_company_profile()
    drive = db.session.execute(
        select(PlacementDrive).where(
            PlacementDrive.id == drive_id,
            PlacementDrive.company_id == company.id
        )
    ).scalar_one_or_none()

    if not drive:
        return jsonify({'error': 'Drive not found'}), 404

    db.session.delete(drive)
    db.session.commit()
    return jsonify({'message': 'Drive deleted'}), 200


@company_bp.route('/drive/<int:drive_id>/applications', methods=['GET'])
@company_required
def drive_applications(drive_id):
    from models import PlacementDrive, Application
    company = get_company_profile()
    drive = db.session.execute(
        select(PlacementDrive).where(
            PlacementDrive.id == drive_id,
            PlacementDrive.company_id == company.id
        )
    ).scalar_one_or_none()

    if not drive:
        return jsonify({'error': 'Drive not found'}), 404

    applications = db.session.execute(
        select(Application).filter_by(placement_drive_id=drive_id)
    ).scalars().all()

    return jsonify([{
        'id': a.id,
        'student_name': a.student.full_name,
        'roll_number': a.student.roll_number,
        'cgpa': a.student.cgpa or '—',
        'skills': a.student.skills or '—',
        'resume': a.student.resume_filename or None,
        'status': a.status,
        'applied_at': a.applied_at.strftime('%Y-%m-%d'),
        'note': a.note or ''
    } for a in applications]), 200


@company_bp.route('/application/<int:app_id>', methods=['PUT'])
@company_required
def update_application(app_id):
    from models import Application, PlacementDrive, Placement
    company = get_company_profile()
    application = db.session.get(Application, app_id)

    if not application:
        return jsonify({'error': 'Application not found'}), 404

    drive = db.session.get(PlacementDrive, application.placement_drive_id)
    if not drive or drive.company_id != company.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    new_status = data.get('status')
    valid_statuses = ['Applied', 'Shortlisted', 'Interview', 'Selected', 'Rejected']

    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    application.status = new_status
    application.note = data.get('note', application.note)

    if new_status == 'Selected':
        salary = data.get('salary', '').strip() or drive.salary_range
        existing = db.session.execute(
            select(Placement).filter_by(application_id=application.id)
        ).scalar_one_or_none()
        if existing:
            existing.salary = salary
        else:
            new_placement = Placement(
                student_id=application.student_id,
                application_id=application.id,
                company_id=company.id,
                job_title=drive.job_title,
                salary=salary
            )
            db.session.add(new_placement)
    else:
        existing = db.session.execute(
            select(Placement).filter_by(application_id=application.id)
        ).scalar_one_or_none()
        if existing:
            db.session.delete(existing)

    db.session.commit()
    return jsonify({'message': f'Application status updated to {new_status}'}), 200

@company_bp.route('/export', methods=['POST'])
@company_required
def export_csv():
    company = get_company_profile()
    from app import export_applications_csv
    task = export_applications_csv.delay(company.id, 'company')
    return jsonify({
        'message': 'Export started. Check static/exports/ when done.',
        'task_id': task.id
    }), 202