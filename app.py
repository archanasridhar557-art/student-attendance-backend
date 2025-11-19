from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import datetime

app = Flask(__name__)
CORS(app)

# ================================
# ✅ CONNECT TO HOSTINGER DATABASE
# ================================
db = pymysql.connect(
    host="srv-db2045.hstgr.io",          # ← your Hostinger DB host
    user="u497160458",                   # ← your Hostinger DB username
    password="Attendence@557",         # ← CHANGE THIS
    database="u497160458_attendance_db"  # ← your Hostinger DB name
)

cursor = db.cursor()


# ================================
# 🔵 ROOT API
# ================================
@app.route('/')
def home():
    return "🚀 Smart Attendance Backend Connected to MySQL"


# ================================
# 👨‍💼 ADMIN LOGIN
# ================================
@app.route('/admin-login', methods=['POST'])
def admin_login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    cursor.execute(
        "SELECT * FROM admins WHERE email=%s AND password=%s",
        (email, password)
    )
    admin = cursor.fetchone()

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

    cursor.execute(
        "SELECT * FROM teachers WHERE email=%s AND password=%s",
        (email, password)
    )
    teacher = cursor.fetchone()

    if teacher:
        return jsonify({"success": True, "token": "teacher_token"}), 200
    else:
        return jsonify({"success": False, "message": "Invalid teacher login"}), 401


# ================================
# 🎓 GET STUDENTS
# ================================
@app.route('/get-students', methods=['GET'])
def get_students():
    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()

    students_list = []
    for s in rows:
        students_list.append({
            "id": s[0],
            "name": s[1],
            "roll": s[2],
            "branch": s[3]
        })

    return jsonify(students_list)


# ================================
# 🎓 ADD STUDENT
# ================================
@app.route('/add-student', methods=['POST'])
def add_student():
    data = request.json
    name = data["name"]
    roll = data["roll"]
    branch = data["branch"]

    # Prevent duplicate roll
    cursor.execute("SELECT * FROM students WHERE roll=%s", (roll,))
    exists = cursor.fetchone()
    if exists:
        return jsonify({"message": "Student with this roll already exists"}), 400

    cursor.execute(
        "INSERT INTO students (name, roll, branch) VALUES (%s, %s, %s)",
        (name, roll, branch)
    )
    db.commit()

    return jsonify({"message": "Student added successfully"}), 200


# ================================
# 🗑 DELETE STUDENT
# ================================
@app.route('/delete-student/<roll>', methods=['DELETE'])
def delete_student(roll):
    cursor.execute("DELETE FROM students WHERE roll=%s", (roll,))
    db.commit()
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

    # Prevent double entry
    cursor.execute(
        "SELECT * FROM attendance WHERE roll=%s AND date=%s",
        (roll, today)
    )
    exists = cursor.fetchone()

    if exists:
        return jsonify({"message": f"{name} already marked today"}), 200

    cursor.execute(
        "INSERT INTO attendance (name, roll, date, time) VALUES (%s, %s, %s, NOW())",
        (name, roll, today)
    )
    db.commit()

    return jsonify({"message": f"{name} marked present"}), 200


# ================================
# 📅 GET ATTENDANCE HISTORY
# ================================
@app.route('/attendance-history', methods=['GET'])
def attendance_history():
    cursor.execute("SELECT * FROM attendance ORDER BY date DESC")
    rows = cursor.fetchall()

    attendance_list = []
    for a in rows:
        attendance_list.append({
            "id": a[0],
            "name": a[1],
            "roll": a[2],
            "date": str(a[3]),
            "time": str(a[4])
        })

    return jsonify(attendance_list)


# ================================
# 📊 DASHBOARD STATS
# ================================
@app.route('/dashboard-stats', methods=['GET'])
def dashboard_stats():
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date=%s", (today,))
    todays_attendance = cursor.fetchone()[0]

    absent = total_students - todays_attendance

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
# 🚀 RUN SERVER
# ================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
