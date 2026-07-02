
import mysql.connector

# PROD DB config (from docker-compose.yml)
db_config = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "bn_moodle",
    "password": "moodle_db_password",
    "database": "bitnami_moodle"
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print(f"✅ Database connected! Current time: {result[0]}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Database connection failed: {e}")