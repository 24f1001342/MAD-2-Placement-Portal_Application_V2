from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from extensions import db
from sqlalchemy import select

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip()
    password = data.get('password', '')

    from models import User
    user = db.session.execute(select(User).filter_by(email=email)).scalar_one_or_none()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if user.is_blacklisted:
        return jsonify({'error': 'Account blacklisted'}), 403

    if not user.is_approved:
        return jsonify({'error': 'Account pending approval'}), 403

    token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
    return jsonify({'token': token, 'role': user.role}), 200


@auth_bp.route('/register/student', methods=['POST'])
def register_student():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    from models import User, Student

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    roll_number = data.get('roll_number', '').strip()
    degree = data.get('degree', '').strip()
    branch = data.get('branch', '').strip()
    cgpa = data.get('cgpa', None)
    skills = data.get('skills', '').strip()

    if not all([username, email, password, full_name, roll_number]):
        return jsonify({'error': 'Missing required fields'}), 400

    if db.session.execute(select(User).filter_by(email=email)).scalar_one_or_none():
        return jsonify({'error': 'Email already registered'}), 409

    if db.session.execute(select(Student).filter_by(roll_number=roll_number)).scalar_one_or_none():
        return jsonify({'error': 'Roll number already registered'}), 409

    new_user = User(
        username=username,
        email=email,
        role='student',
        is_approved=True,
        is_blacklisted=False
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.flush()

    new_student = Student(
        user_id=new_user.id,
        full_name=full_name,
        roll_number=roll_number,
        degree=degree,
        branch=branch,
        cgpa=float(cgpa) if cgpa else None,
        skills=skills
    )
    db.session.add(new_student)
    db.session.commit()

    return jsonify({'message': 'Registration successful'}), 201


@auth_bp.route('/register/company', methods=['POST'])
def register_company():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    from models import User, Company

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    company_name = data.get('company_name', '').strip()
    industry = data.get('industry', '').strip()
    hr_contact = data.get('hr_contact', '').strip()
    website = data.get('website', '').strip()
    description = data.get('description', '').strip()
    location = data.get('location', '').strip()

    if not all([username, email, password, company_name]):
        return jsonify({'error': 'Missing required fields'}), 400

    if db.session.execute(select(User).filter_by(email=email)).scalar_one_or_none():
        return jsonify({'error': 'Email already registered'}), 409

    new_user = User(
        username=username,
        email=email,
        role='company',
        is_approved=False,
        is_blacklisted=False
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.flush()

    new_company = Company(
        user_id=new_user.id,
        company_name=company_name,
        industry=industry,
        hr_contact=hr_contact,
        website=website,
        description=description,
        location=location
    )
    db.session.add(new_company)
    db.session.commit()

    return jsonify({'message': 'Registration submitted. Awaiting admin approval.'}), 201


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    identity = get_jwt_identity()
    from models import User
    user = db.session.get(User, int(idenitity))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role
    }), 200