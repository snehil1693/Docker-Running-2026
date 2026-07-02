
import mysql.connector
import smtplib
import sqlite3
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# ======================
# DB CONFIG (Prod)
# ======================
DB_HOST = "127.0.0.1"
DB_PORT = 3307
DB_USER = "bn_moodle"
DB_PASSWORD = "moodle_db_password"
DB_NAME = "bitnami_moodle"

# ======================
# COURSE CONFIG
# ======================
COURSE_ID = 2
COURSE_NAME = "Visit Health Cloud Security Training"
DEADLINE = datetime(2025, 12, 15)  # <-- update if deadline changes

# ======================
# EMAIL CONFIG
# ======================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "snehil.shubham@getvisitapp.com"      # <-- replace with sender Gmail
SMTP_PASSWORD = "pntpxewztwzecwqd"     # <-- replace with Gmail App Password

# ======================
# REMINDER DB CONFIG
# ======================
REMINDER_DB = "reminders.db"

# ======================
# INIT LOCAL DB
# ======================
conn = sqlite3.connect(REMINDER_DB)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS reminders
                  (email TEXT, type TEXT, sent_at TEXT)''')
conn.commit()
conn.close()

def send_email(to_email, subject, body):
    msg = MIMEText(body, "plain")
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"📧 Sent: {subject} → {to_email}")

def reminder_already_sent(email, reminder_type):
    conn = sqlite3.connect(REMINDER_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reminders WHERE email=? AND type=?", (email, reminder_type))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_reminder_sent(email, reminder_type):
    conn = sqlite3.connect(REMINDER_DB)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reminders VALUES (?, ?, ?)", (email, reminder_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_users():
    db = mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.id, u.firstname, u.lastname, u.email
        FROM mdl_user u
        JOIN mdl_user_enrolments ue ON ue.userid = u.id
        JOIN mdl_enrol e ON e.id = ue.enrolid
        WHERE e.courseid = %s
    """, (COURSE_ID,))
    users = cursor.fetchall()
    db.close()
    return users

def has_completed(user_id):
    db = mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    cursor = db.cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM mdl_course_completions
        WHERE course = %s AND userid = %s AND timecompleted IS NOT NULL
    """, (COURSE_ID, user_id))
    result = cursor.fetchone()[0]
    db.close()
    return result > 0

def main():
    today = datetime.now().date()
    days_left = (DEADLINE.date() - today).days

    users = get_users()
    print(f"✅ Found {len(users)} users in course {COURSE_ID}")

    for user_id, firstname, lastname, email in users:
        if not email:
            continue

        full_name = f"{firstname} {lastname}"

        if has_completed(user_id):
            print(f"✔️ {full_name} ({email}) already completed the course.")
            continue

        # 1. Welcome Mail (only once)
        if not reminder_already_sent(email, "welcome"):
            subject = f"Welcome to {COURSE_NAME}"
            body = (
                 f"Dear {full_name},\n\n"
                 f"You have been enrolled in the {COURSE_NAME}. Please note that the deadline "
                 f"for completing this course is {DEADLINE.date()}.\n\n"
                 "We request you to complete the module before the deadline to remain "
                 "compliant with our internal security requirements.\n\n"
                 "You can access the course using the link below:\n"
                 "https://lms.getvisitapp.com/course/view.php?id=2"
                  )
            send_email(email, subject, body)
            mark_reminder_sent(email, "welcome")


        # 2. Reminder (15 days before deadline)
        if days_left == 15 and not reminder_already_sent(email, "15_day"):
            subject = f"Reminder: {COURSE_NAME} – 15 days left"
            body = f"Dear {full_name},\n\nThis is a reminder to complete {COURSE_NAME}. The deadline is {DEADLINE.date()}.\n\nPlease complete it on time."
            send_email(email, subject, body)
            mark_reminder_sent(email, "15_day")

        # 3. Final Reminder (2 days before deadline)
        if days_left == 2 and not reminder_already_sent(email, "2_day"):
            subject = f"Final Reminder: {COURSE_NAME} – Deadline Approaching"
            body = f"Dear {full_name},\n\nOnly 2 days left to complete {COURSE_NAME}. The deadline is {DEADLINE.date()}.\n\nPlease complete it urgently."
            send_email(email, subject, body)
            mark_reminder_sent(email, "2_day")

if __name__ == "__main__":
    main()
