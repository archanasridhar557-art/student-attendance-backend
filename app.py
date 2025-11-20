from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import os
import datetime

app = Flask(__name__)
CORS(app)

# ================================
# ✅ CONNECT TO RAILWAY DATABASE
# ================================
def get_db():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT")),
        cursorclass=pymysql.cursors.DictCursor
    )


# ================================
# 🔵 ROOT API
# ================================
@app.route('/')
def home():
    return "🚀 Smart Attendance Backend Connected to Railway MySQL"


# ================================
# 👨‍💼 ADMIN LOGIN
# ================================
@app.route('/admin-login', methods=['POST'])
def admin_login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM admins WHERE email=%s AND password=%s",
        (email, password)
    )
    admin = cursor.fetchone()
    cursor.close()
    db.close()

    if admin:
        return jsonify({"success": True, "token": "admin_token"}), 200
    else:
        return jsonify({"success": False, "message": "Invalid admin login"}), 401


# ================================
# 👨‍🏫 TEACHER LOGIN
# ================================
@app.route('/teacher-login', methods=['POST'])
def teacher_login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM teachers WHERE email=%s AND password=%s",
        (email, password)
    )
    teacher = cursor.fetchone()
    cursor.close()
    db.close()

    if teacher:
        return jsonify({"success": True, "token": "teacher_token"}), 200
    else:
        return jsonify({"success": False, "message": "Invalid teacher login"}), 401


# ================================
# 🎓 GET STUDENTS
# ================================
@app.route('/get-students', methods=['GET'])
def get_students():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(rows)


# ================================
# 🎓 ADD STUDENT
# ================================
@app.route('/add-student', methods=['POST'])
def add_student():
    data = request.json
    name = data["name"]
    roll = data["roll"]
    branch = data["branch"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM students WHERE roll=%s", (roll,))
    exists = cursor.fetchone()

    if exists:
        cursor.close()
        db.close()
        return jsonify({"message": "Student with this roll already exists"}), 400

    cursor.execute(
        "INSERT INTO students (name, roll, branch) VALUES (%s, %s, %s)",
        (name, roll, branch)
    )
    db.commit()

    cursor.close()
    db.close()

    return jsonify({"message": "Student added successfully"}), 200


# ================================
# 🗑 DELETE STUDENT
# ================================
@app.route('/delete-student/<roll>', methods=['DELETE'])
def delete_student(roll):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM students WHERE roll=%s", (roll,))
    db.commit()

    cursor.close()
    db.close()

    return jsonify({"message": "Student deleted successfully"}), 200


# ================================
# 🕒 MARK ATTENDANCE
# ================================
@app.route('/mark', methods=['POST'])
def mark_attendance():
    data = request.json
    name = data["name"]
    roll = data["roll"]

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM attendance WHERE roll=%s AND date=%s",
        (roll, today)
    )
    exists = cursor.fetchone()

    if exists:
        cursor.close()
        db.close()
        return jsonify({"message": f"{name} already marked today"}), 200

    cursor.execute(
        "INSERT INTO attendance (name, roll, date, time) VALUES (%s, %s, %s, NOW())",
        (name, roll, today)
    )
    db.commit()

    cursor.close()
    db.close()

    return jsonify({"message": f"{name} marked present"}), 200


# ================================
# 📅 GET ATTENDANCE HISTORY
# ================================
@app.route('/attendance-history', methods=['GET'])
def attendance_history():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM attendance ORDER BY date DESC")
    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(rows)


# ================================
# 📊 DASHBOARD STATS
# ================================
@app.route('/dashboard-stats', methods=['GET'])
def dashboard_stats():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()["total"]

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) AS present FROM attendance WHERE date=%s", (today,))
    todays_attendance = cursor.fetchone()["present"]

    absent = total_students - todays_attendance

    cursor.close()
    db.close()

    return jsonify({
        "success": True,
        "stats": {
            "totalStudents": total_students,
            "todaysAttendance": todays_attendance,
            "absentStudents": absent,
            "proxyAlerts": 0
        }
    })


# ================================
# 🚀 RUN SERVER (LOCAL)
# ================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
