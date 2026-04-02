from extensions import db
from sqlalchemy import select
from datetime import datetime, timedelta
import csv
import os


def create_tasks(celery, app):

    @celery.task(name='tasks.send_daily_reminders')
    def send_daily_reminders():
        with app.app_context():
            from models import Application
            from flask_mail import Message
            from extensions import mail

            interviews = db.session.execute(
                select(Application).where(Application.status == 'Interview')
            ).scalars().all()

            for app_record in interviews:
                student = app_record.student
                drive = app_record.placement_drive
                if student.user.email:
                    try:
                        msg = Message(
                            subject='Interview Reminder',
                            recipients=[student.user.email],
                            body=f"Hi {student.full_name},\n\nReminder: You have an interview scheduled for {drive.job_title} at {drive.company.company_name}.\n\nGood luck!"
                        )
                        mail.send(msg)
                    except Exception as e:
                        print(f"Email failed: {e}")

        return 'Interview reminders sent'

    @celery.task(name='tasks.send_monthly_report')
    def send_monthly_report():
        with app.app_context():
            from models import PlacementDrive, Application, Placement, Company
            from flask_mail import Message
            from extensions import mail

            now = datetime.now()
            companies = db.session.execute(select(Company)).scalars().all()

            for company in companies:
                if not company.user.is_approved:
                    continue

                drives = db.session.execute(
                    select(PlacementDrive).filter_by(company_id=company.id)
                ).scalars().all()

                total_apps = sum(len(d.applications) for d in drives)
                total_placed = sum(
                    1 for d in drives
                    for a in d.applications
                    if a.status == 'Selected'
                )

                report_html = f"""
                <h1>Monthly Placement Report - {now.strftime('%B %Y')}</h1>
                <h2>{company.company_name}</h2>
                <p>Total Drives: {len(drives)}</p>
                <p>Total Applications: {total_apps}</p>
                <p>Total Selected: {total_placed}</p>
                """

                try:
                    msg = Message(
                        subject=f'Monthly Placement Report - {now.strftime("%B %Y")}',
                        recipients=[company.user.email],
                        html=report_html
                    )
                    mail.send(msg)
                except Exception as e:
                    print(f"Report email failed for {company.company_name}: {e}")

        return 'Monthly reports sent'

    @celery.task(name='tasks.export_applications_csv')
    def export_applications_csv(id, role='student'):
        with app.app_context():
            from models import Student, Application, Company, PlacementDrive

            export_folder = os.path.join(os.path.dirname(__file__), 'static', 'exports')
            os.makedirs(export_folder, exist_ok=True)
            filename = f"export_{role}_{id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
            filepath = os.path.join(export_folder, filename)

            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                if role == 'student':
                    student = db.session.get(Student, id)
                    applications = db.session.execute(
                        select(Application).filter_by(student_id=id)
                    ).scalars().all()
                    writer.writerow(['Student ID', 'Company', 'Drive Title', 'Status', 'Applied At'])
                    for a in applications:
                        writer.writerow([
                            student.roll_number,
                            a.placement_drive.company.company_name,
                            a.placement_drive.job_title,
                            a.status,
                            a.applied_at.strftime('%Y-%m-%d')
                        ])
                else:
                    company = db.session.get(Company, id)
                    drives = db.session.execute(
                        select(PlacementDrive).filter_by(company_id=id)
                    ).scalars().all()
                    writer.writerow(['Drive Title', 'Applicant', 'Roll No', 'Status', 'Applied At'])
                    for drive in drives:
                        for a in drive.applications:
                            writer.writerow([
                                drive.job_title,
                                a.student.full_name,
                                a.student.roll_number,
                                a.status,
                                a.applied_at.strftime('%Y-%m-%d')
                            ])

        return {'filename': filename}

    return send_daily_reminders, send_monthly_report, export_applications_csv