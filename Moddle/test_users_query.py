
#!/usr/bin/env python3
import mysql.connector

# -------------------
# Database Configuration
# -------------------
DB_HOST = "127.0.0.1"
DB_PORT = 3307
DB_USER = "bn_moodle"
DB_PASS = "moodle_db_password"
DB_NAME = "bitnami_moodle"

COURSE_ID = 6   # 🔹 Change this to your actual course ID

# -------------------
# Main
# -------------------
conn = mysql.connector.connect(
    host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME
)
cur = conn.cursor(dictionary=True)

cur.execute("""
    SELECT u.id as user_id, u.firstname, u.lastname, u.email, c.fullname as course_name
    FROM mdl_user u
    JOIN mdl_user_enrolments ue ON ue.userid = u.id
    JOIN mdl_enrol e ON e.id = ue.enrolid
    JOIN mdl_course c ON c.id = e.courseid
    WHERE c.id = %s
""", (COURSE_ID,))

users = cur.fetchall()
conn.close()

print(f"✅ Found {len(users)} users in course {COURSE_ID}")
for user in users:
    print(f"- {user['firstname']} {user['lastname']} ({user['email']})")