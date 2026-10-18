
import argparse, os, random, statistics, sys, time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ap = argparse.ArgumentParser()
ap.add_argument("--students", type=int, default=3000)
ap.add_argument("--companies", type=int, default=100)
ap.add_argument("--drives", type=int, default=1500)
ap.add_argument("--apps", type=int, default=30000)
ap.add_argument("--runs", type=int, default=30)
args = ap.parse_args()

# Point the app at a throw-away DB BEFORE importing it.
from config import Config
Config.SQLALCHEMY_DATABASE_URI = "sqlite:///bench.db"

import app as portal                      # creates tables + seeds admin in bench.db
from extensions import db
from models import User, Student, Company, PlacementDrive, Application, Placement
from werkzeug.security import generate_password_hash
import redis

r = redis.Redis(host="localhost", port=6379, db=0)
flask_app = portal.flask_app
random.seed(42)

PW = "bench123"
PW_HASH = generate_password_hash(PW)       # one hash reused for every seeded user (fast)
now = datetime.now()

with flask_app.app_context():
    if db.session.query(Student).count() == 0:
        print(f"Seeding {args.students} students, {args.companies} companies, "
              f"{args.drives} drives, {args.apps} applications ...")
        t0 = time.perf_counter()
        base = db.session.query(User).count()

        db.session.bulk_insert_mappings(User, [
            dict(username=f"s{i}", email=f"s{i}@bench.test", password_hash=PW_HASH,
                 role="student", is_approved=True, is_blacklisted=False, created_at=now)
            for i in range(args.students)])
        db.session.bulk_insert_mappings(User, [
            dict(username=f"c{i}", email=f"c{i}@bench.test", password_hash=PW_HASH,
                 role="company", is_approved=(i % 10 != 0), is_blacklisted=False, created_at=now)
            for i in range(args.companies)])
        db.session.commit()

        s_users = [u.id for u in db.session.query(User).filter(User.role == "student")]
        c_users = [u.id for u in db.session.query(User).filter(User.role == "company")]
        db.session.bulk_insert_mappings(Student, [
            dict(user_id=uid, full_name=f"Student {i}", roll_number=f"R{i:06d}",
                 degree="B.E.", branch="CSE", cgpa=round(random.uniform(6, 10), 2),
                 skills="python,sql,c++", created_at=now)
            for i, uid in enumerate(s_users)])
        db.session.bulk_insert_mappings(Company, [
            dict(user_id=uid, company_name=f"Company {i}", industry=random.choice(["IT", "Finance", "Core"]),
                 created_at=now)
            for i, uid in enumerate(c_users)])
        db.session.commit()

        company_ids = [c.id for c in db.session.query(Company)]
        student_ids = [s.id for s in db.session.query(Student)]
        db.session.bulk_insert_mappings(PlacementDrive, [
            dict(company_id=random.choice(company_ids), job_title=f"Role {i}",
                 required_skills="python,sql", eligibility_criteria="CGPA >= 7",
                 salary_range="6-10 LPA",
                 application_deadline=now + timedelta(days=random.randint(5, 90)),
                 status=random.choices(["Approved", "Pending", "Closed"], [70, 20, 10])[0],
                 created_at=now)
            for i in range(args.drives)])
        db.session.commit()

        drive_ids = [d.id for d in db.session.query(PlacementDrive)]
        pairs = set()
        while len(pairs) < args.apps:
            pairs.add((random.choice(student_ids), random.choice(drive_ids)))
        db.session.bulk_insert_mappings(Application, [
            dict(student_id=s, placement_drive_id=d,
                 status=random.choice(["Applied", "Shortlisted", "Interview", "Selected", "Rejected"]),
                 applied_at=now)
            for s, d in pairs])
        db.session.commit()
        print(f"Seeded in {time.perf_counter() - t0:.1f}s")
    else:
        print("bench.db already seeded, reusing it")

    counts = {m.__tablename__: db.session.query(m).count()
              for m in (Student, Company, PlacementDrive, Application)}
    approved = db.session.query(PlacementDrive).filter(PlacementDrive.status == "Approved").count()

client = flask_app.test_client()

def login(email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, (res.status_code, res.get_json())
    return {"Authorization": f"Bearer {res.get_json()['token']}"}

admin_h = login("admin@example.com", "admin123")
student_h = login("s0@bench.test", PW)

def timed(url, headers, key):
    ts_cold, ts_warm = [], []
    for _ in range(args.runs):
        for k in r.keys(key + "*"):
            r.delete(k)
        t = time.perf_counter(); res = client.get(url, headers=headers); ts_cold.append((time.perf_counter() - t) * 1000)
        assert res.status_code == 200, res.status_code
    client.get(url, headers=headers)  # make sure it is cached
    for _ in range(args.runs):
        t = time.perf_counter(); res = client.get(url, headers=headers); ts_warm.append((time.perf_counter() - t) * 1000)
        assert res.status_code == 200, res.status_code
    return statistics.median(ts_cold), statistics.median(ts_warm)

print(f"\nDataset: {counts['student']} students, {counts['company']} companies, "
      f"{counts['placement_drive']} drives ({approved} approved), {counts['application']} applications")
print(f"Median of {args.runs} runs each (in-process requests, Redis cache)\n")
print(f"{'endpoint':<28}{'cache miss':>12}{'cache hit':>12}{'faster':>10}{'speedup':>10}")
for name, url, hdr, key in [
    ("/api/admin/dashboard", "/api/admin/dashboard", admin_h, "admin_dashboard"),
    ("/api/student/dashboard", "/api/student/dashboard", student_h, "approved_drives_"),
]:
    cold, warm = timed(url, hdr, key)
    print(f"{name:<28}{cold:>10.1f}ms{warm:>10.1f}ms{(cold - warm) / cold * 100:>9.0f}%{cold / warm:>9.1f}x")