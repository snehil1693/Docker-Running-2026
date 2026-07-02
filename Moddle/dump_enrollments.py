
#!/usr/bin/env python3
import os
import mysql.connector
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import xlsxwriter

# -------------------
# Email Configuration
# -------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "snehil.shubham@getvisitapp.com"
SMTP_PASS = "pntpxewztwzecwqd"  # Gmail App Password
TO_EMAIL = ["snehil.shubham@getvisitapp.com"]

# -------------------
# Database Configuration
# -------------------
DB_HOST = "127.0.0.1"
DB_PORT = 3307
DB_USER = "bn_moodle"
DB_PASS = "moodle_db_password"
DB_NAME = "bitnami_moodle"

# -------------------
# Output Directory
# -------------------
OUTPUT_DIR = "/home/ubuntu/moddle-docker/enrollment_dumps"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def table_exists(cursor, table_name):
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def dump_course_enrollments():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, fullname FROM mdl_course WHERE id > 1")
    courses = cur.fetchall()

    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(OUTPUT_DIR, f"course_enrollments_{date_str}.log")
    excel_file = os.path.join(OUTPUT_DIR, f"course_enrollments_{date_str}.xlsx")

    workbook = xlsxwriter.Workbook(excel_file)
    completion_enabled = table_exists(cur, "mdl_course_completion_criteria_progress")

    with open(log_file, "w") as f:
        f.write(f"Enrollment Report - {datetime.now()}\n\n")

        for course in courses:
            course_id = course["id"]
            course_name = course["fullname"]

            # Get enrolled users
            cur.execute("""
                SELECT u.id, u.firstname, u.lastname, u.email
                FROM mdl_user u
                JOIN mdl_user_enrolments ue ON u.id = ue.userid
                JOIN mdl_enrol e ON ue.enrolid = e.id
                WHERE e.courseid = %s
            """, (course_id,))
            enrolled_users = cur.fetchall()

            # Users who started
            cur.execute("""
                SELECT DISTINCT ra.userid
                FROM mdl_role_assignments ra
                JOIN mdl_context ctx ON ra.contextid = ctx.id
                JOIN mdl_course c ON ctx.instanceid = c.id
                WHERE ctx.contextlevel = 50 AND c.id = %s
            """, (course_id,))
            started_user_ids = [r["userid"] for r in cur.fetchall()]

            completed_user_ids = []
            if completion_enabled:
                try:
                    cur.execute("""
                        SELECT DISTINCT userid
                        FROM mdl_course_completions
                        WHERE course = %s AND timecompleted IS NOT NULL
                    """, (course_id,))
                    completed_user_ids = [r["userid"] for r in cur.fetchall()]
                except Exception:
                    completion_enabled = False

            started_users = [u for u in enrolled_users if u["id"] in started_user_ids and u["id"] not in completed_user_ids]
            completed_users = [u for u in enrolled_users if u["id"] in completed_user_ids]
            not_started_users = [u for u in enrolled_users if u["id"] not in started_user_ids and u["id"] not in completed_user_ids]

            # Write log section
            f.write(f"=== {course_name} (Course ID: {course_id}) ===\n")
            f.write(f"Total enrolled: {len(enrolled_users)}\n")
            f.write(f"Completed: {len(completed_users)}\n")
            f.write(f"Started (in progress): {len(started_users)}\n")
            f.write(f"Not started: {len(not_started_users)}\n\n")

            if not completion_enabled:
                f.write("⚠️ Note: Course completion tracking is disabled.\n\n")

            if not_started_users:
                f.write("🕒 Not Started:\n")
                for u in not_started_users:
                    f.write(f" - {u['firstname']} {u['lastname']} ({u['email']})\n")
                f.write("\n")

            if started_users:
                f.write("🚀 Started (In Progress):\n")
                for u in started_users:
                    f.write(f" - {u['firstname']} {u['lastname']} ({u['email']})\n")
                f.write("\n")

            if completed_users:
                f.write("✅ Completed:\n")
                for u in completed_users:
                    f.write(f" - {u['firstname']} {u['lastname']} ({u['email']})\n")
                f.write("\n")

            # Write Excel sheet
            sheet = workbook.add_worksheet(course_name[:30])
            sheet.write_row(0, 0, ["User ID", "Name", "Email", "Status"])
            row = 1
            for u in completed_users:
                sheet.write_row(row, 0, [u["id"], f"{u['firstname']} {u['lastname']}", u["email"], "Completed"])
                row += 1
            for u in started_users:
                sheet.write_row(row, 0, [u["id"], f"{u['firstname']} {u['lastname']}", u["email"], "In Progress"])
                row += 1
            for u in not_started_users:
                sheet.write_row(row, 0, [u["id"], f"{u['firstname']} {u['lastname']}", u["email"], "Not Started"])
                row += 1

            f.write("\n")

    workbook.close()
    cur.close()
    conn.close()

    send_email(log_file, excel_file)
    print(f"✅ Enrollment dump written to {log_file}")
    print(f"📊 Excel summary created at {excel_file}")
    print(f"📧 Email sent to: {', '.join(TO_EMAIL)}")


def send_email(log_path, excel_path):
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(TO_EMAIL)
    msg["Subject"] = "Daily Moodle Enrollment Report"

    body = "Attached are the daily enrollment summary reports (log and Excel)."
    msg.attach(MIMEText(body, "plain"))

    for file_path in [log_path, excel_path]:
        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}")
        msg.attach(part)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


if __name__ == "__main__":
    dump_course_enrollments()
