# Placement Portal Application V2
Modern Application Development II — IITM BS Data Science  
Student: Aiden Tomas George | 24f1001342

## Project Overview
A full-stack decoupled placement portal built with Flask REST API (backend) and Vue.js CDN (frontend). Supports three roles — Admin, Company, and Student — each with dedicated dashboards and role-based access control via JWT.

## Tech Stack
- **Backend:** Flask 3.x, SQLAlchemy 2.x, SQLite, Flask-JWT-Extended, Flask-CORS, Flask-Mail
- **Frontend:** Vue.js 3 (CDN), Axios, Bootstrap 5.3
- **Background Jobs:** Celery 5.x, Redis
- **Caching:** Redis

## Project Structure
```
placement_portal_v2/
├── backend/
│   ├── app.py              # Flask app + Celery setup
│   ├── config.py           # Configuration
│   ├── extensions.py       # db, jwt, mail, cors
│   ├── models.py           # Database models
│   ├── tasks.py            # Celery background tasks
│   ├── requirements.txt    # Python dependencies
│   └── resources/
│       ├── auth.py         # /api/auth/* routes
│       ├── admin.py        # /api/admin/* routes
│       ├── company.py      # /api/company/* routes
│       └── student.py      # /api/student/* routes
└── frontend/
    ├── index.html          # Vue.js SPA entry point
    └── manifest.json       # PWA manifest
```

## Setup and Running

### Prerequisites
- WSL2 (Ubuntu) with Python 3.12
- Redis installed in WSL

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Start Redis
```bash
redis-server --daemonize yes
```

### Start Flask
```bash
cd backend
python3 app.py
```

### Start Celery Worker
```bash
cd backend
celery -A app.celery worker --loglevel=info
```

### Start Celery Beat
```bash
cd backend
celery -A app.celery beat --loglevel=info
```

### Access the App
Open `http://localhost:5000` in your browser.

## Default Admin Credentials
- Email: `admin@example.com`
- Password: `admin123`

## Features
- JWT authentication with login rate limiting (5 attempts, 5-minute lockout)
- Admin: approve/reject companies and drives, manage users, view all records
- Company: post drives, manage applicants, update application status
- Student: apply to drives, track status, upload resume, view placement history
- Celery: interview reminders, monthly reports, async CSV export
- Redis: API response caching with cache invalidation
- PWA manifest for Add to Home Screen support