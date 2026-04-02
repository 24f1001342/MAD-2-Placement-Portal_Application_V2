from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity,get_jwt
from extensions import db
from sqlalchemy import select, or_
from functools import wraps
import json
import redis

admin_bp = Blueprint('admin', __name__)

r = redis.Redis(host='localhost', port=6379, db=0)

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        identity = get_jwt_identity()
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    from models import User, Student, Company, PlacementDrive, Application, Placement

    cached = r.get('admin_dashboard')
    if cached:
        return jsonify(json.loads(cached)), 200


    total_students = db.session.execute(select(Student)).scalars().all()
    total_companies = db.session.execute(select(Company)).scalars().all()
    total_drives = db.session.execute(select(PlacementDrive)).scalars().all()
    total_applications = db.session.execute(select(Application)).scalars().all()
    total_placements = db.session.execute(select(Placement)).scalars().all()

    pending_companies = db.session.execute(
        select(Company).join(User).where(
            User.is_approved == False,
            User.is_blacklisted == False
        )
    ).scalars().all()

    pending_drives = db.session.execute(
        select(PlacementDrive).where(PlacementDrive.status == 'Pending')
    ).scalars().all()

    data={
        'total_students': len(total_students),
        'total_companies': len(total_companies),
        'total_drives': len(total_drives),
        'total_applications': len(total_applications),
        'total_placements': len(total_placements),
        'pending_companies': [{'id': c.id, 'company_name': c.company_name, 'industry': c.industry} for c in pending_companies],
        'pending_drives': [{'id': d.id, 'job_title': d.job_title, 'company': d.company.company_name} for d in pending_drives]
    }
    r.setex('admin_dashboard', 600, json.dumps(data))
    return jsonify(data), 200



@admin_bp.route('/companies', methods=['GET'])
@admin_required
def companies():
    from models import Company, User
    search = request.args.get('search', '')
    query = select(Company).distinct()
    if search:
        query = query.where(or_(
            Company.company_name.ilike(f'%{search}%'),
            Company.industry.ilike(f'%{search}%')
        ))
    companies = db.session.execute(query).scalars().all()
    return jsonify([{
        'id': c.id,
        'company_name': c.company_name,
        'industry': c.industry or '—',
        'hr_contact': c.hr_contact or '—',
        'website': c.website or '—',
        'location': c.location or '—',
        'is_approved': c.user.is_approved,
        'is_blacklisted': c.user.is_blacklisted
    } for c in companies]), 200


@admin_bp.route('/company/<int:id>/approve', methods=['POST'])
@admin_required
def approve_company(id):
    from models import Company, User
    company = db.session.get(Company, id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    user = db.session.get(User, company.user_id)
    user.is_approved = True
    db.session.commit()
    return jsonify({'message': f'{company.company_name} approved'}), 200


@admin_bp.route('/company/<int:id>/reject', methods=['POST'])
@admin_required
def reject_company(id):
    from models import Company, User
    company = db.session.get(Company, id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    user = db.session.get(User, company.user_id)
    user.is_approved = False
    db.session.commit()
    return jsonify({'message': f'{company.company_name} rejected'}), 200


@admin_bp.route('/company/<int:id>/blacklist', methods=['POST'])
@admin_required
def blacklist_company(id):
    from models import Company, User
    company = db.session.get(Company, id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    user = db.session.get(User, company.user_id)
    user.is_blacklisted = not user.is_blacklisted
    db.session.commit()
    status = 'blacklisted' if user.is_blacklisted else 'unblacklisted'
    return jsonify({'message': f'{company.company_name} {status}'}), 200


@admin_bp.route('/company/<int:id>/delete', methods=['DELETE'])
@admin_required
def delete_company(id):
    from models import Company, User
    company = db.session.get(Company, id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    user = db.session.get(User, company.user_id)
    db.session.delete(company)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Company deleted'}), 200


@admin_bp.route('/students', methods=['GET'])
@admin_required
def students():
    from models import Student, User
    search = request.args.get('search', '')
    query = select(Student).distinct()
    if search:
        query = query.join(User).where(or_(
            Student.full_name.ilike(f'%{search}%'),
            Student.roll_number.ilike(f'%{search}%'),
            User.email.ilike(f'%{search}%')
        ))
    students = db.session.execute(query).scalars().all()
    return jsonify([{
        'id': s.id,
        'full_name': s.full_name,
        'roll_number': s.roll_number,
        'email': s.user.email,
        'degree': s.degree or '—',
        'branch': s.branch or '—',
        'cgpa': s.cgpa or '—',
        'is_blacklisted': s.user.is_blacklisted
    } for s in students]), 200


@admin_bp.route('/student/<int:id>/blacklist', methods=['POST'])
@admin_required
def blacklist_student(id):
    from models import Student, User
    student = db.session.get(Student, id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    user = db.session.get(User, student.user_id)
    user.is_blacklisted = not user.is_blacklisted
    db.session.commit()
    status = 'blacklisted' if user.is_blacklisted else 'unblacklisted'
    return jsonify({'message': f'{student.full_name} {status}'}), 200


@admin_bp.route('/student/<int:id>/delete', methods=['DELETE'])
@admin_required
def delete_student(id):
    from models import Student, User
    student = db.session.get(Student, id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    user = db.session.get(User, student.user_id)
    db.session.delete(student)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Student deleted'}), 200


@admin_bp.route('/drives', methods=['GET'])
@admin_required
def drives():
    from models import PlacementDrive
    drives = db.session.execute(select(PlacementDrive)).scalars().all()
    return jsonify([{
        'id': d.id,
        'job_title': d.job_title,
        'company': d.company.company_name,
        'deadline': d.application_deadline.strftime('%Y-%m-%d'),
        'status': d.status,
        'salary_range': d.salary_range or '—'
    } for d in drives]), 200


@admin_bp.route('/drive/<int:id>/approve', methods=['POST'])
@admin_required
def approve_drive(id):
    from models import PlacementDrive
    drive = db.session.get(PlacementDrive, id)
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    drive.status = 'Approved'
    db.session.commit()
    return jsonify({'message': f'{drive.job_title} approved'}), 200


@admin_bp.route('/drive/<int:id>/reject', methods=['POST'])
@admin_required
def reject_drive(id):
    from models import PlacementDrive
    drive = db.session.get(PlacementDrive, id)
    if not drive:
        return jsonify({'error': 'Drive not found'}), 404
    drive.status = 'Rejected'
    db.session.commit()
    return jsonify({'message': f'{drive.job_title} rejected'}), 200


@admin_bp.route('/applications', methods=['GET'])
@admin_required
def applications():
    from models import Application
    applications = db.session.execute(select(Application)).scalars().all()
    return jsonify([{
        'id': a.id,
        'student': a.student.full_name,
        'roll_number': a.student.roll_number,
        'drive': a.placement_drive.job_title,
        'company': a.placement_drive.company.company_name,
        'status': a.status,
        'applied_at': a.applied_at.strftime('%Y-%m-%d')
    } for a in applications]), 200


@admin_bp.route('/placements', methods=['GET'])
@admin_required
def placements():
    from models import Placement
    placements = db.session.execute(select(Placement)).scalars().all()
    return jsonify([{
        'id': p.id,
        'student': p.student.full_name,
        'company': p.company.company_name,
        'job_title': p.job_title,
        'salary': p.salary or '—',
        'placed_at': p.placed_at.strftime('%Y-%m-%d')
    } for p in placements]), 200