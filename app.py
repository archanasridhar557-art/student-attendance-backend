from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime

app = Flask(__name__)
CORS(app)  # Allows requests from frontend (React)

# --- In-memory data (temporary for testing) ---
attendance_data = []
students = []

# ✅ Root route
@app.route('/')
def home():
    return "✅ Smart Attendance Backend Running"

# =========================
# 👨‍💼 ADMIN LOGIN ROUTE
# =========================
@app.route('/admin-login', methods=['POST'])
def admin_login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    # 🔐 Static test credentials
    if email == "admin@college.com" and password == "admin123":
        return jsonify({
            "success": True,
            "token": "secure_admin_token_123",
            "message": "Login successful"
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "Invalid credentials"
        }), 401

# =========================
# 👨‍🏫 TEACHER LOGIN ROUTE
# =========================
@app.route('/teacher-login', methods=['POST'])
def teacher_login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if email == "teacher@college.com" and password == "teacher123":
        return jsonify({
            "success": True,
            "token": "secure_teacher_token_123",
            "message": "Login successful"
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "Invalid credentials"
        }), 401

# =========================
# 🎓 STUDENT ROUTES
# =========================
@app.route('/get-students', methods=['GET'])
def get_students():
    return jsonify(students)

@app.route('/add-student', methods=['POST'])
def add_student():
    data = request.json
    if not data.get('name') or not data.get('roll') or not data.get('branch'):
        return jsonify({"message": "All fields (name, roll, branch) are required"}), 400

    # Prevent duplicate roll numbers
    if any(s['roll'] == data['roll'] for s in students):
        return jsonify({"message": "Student with this roll already exists"}), 400

    students.append(data)
    return jsonify({"message": "Student added successfully"}), 200

@app.route('/delete-student/<roll>', methods=['DELETE'])
def delete_student(roll):
    global students
    students = [s for s in students if s['roll'] != roll]
    return jsonify({"message": "Student deleted successfully"}), 200

# =========================
# 🕒 ATTENDANCE ROUTES
# =========================
@app.route('/mark', methods=['POST'])
def mark_attendance():
    data = request.json
    name = data.get('name')
    roll = data.get('roll')

    if not name or not roll:
        return jsonify({"message": "Missing name or roll"}), 400

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Prevent duplicate attendance same day
    for entry in attendance_data:
        if entry["roll"] == roll and entry["time"].split(" ")[0] == timestamp.split(" ")[0]:
            return jsonify({"message": f"{name} already marked today"}), 200

    attendance_data.append({"name": name, "roll": roll, "time": timestamp})
    return jsonify({"message": f"{name} marked present at {timestamp}"}), 200

@app.route('/get_attendance', methods=['GET'])
def get_attendance():
    return jsonify(attendance_data)

# ✅ For Report Page Compatibility
@app.route('/attendance-history', methods=['GET'])
def attendance_history():
    return jsonify(attendance_data)


# =========================
# 📊 DASHBOARD STATS ROUTE
# =========================
@app.route('/dashboard-stats', methods=['GET'])
def dashboard_stats():
    total_students = len(students)
    
    # Count today's attendance
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    todays_attendance = sum(1 for entry in attendance_data if entry["time"].startswith(today))
    absent_students = total_students - todays_attendance if total_students > 0 else 0

    # You can enhance proxy detection later — for now, we use dummy value
    proxy_alerts = 0

    return jsonify({
        "success": True,
        "stats": {
            "totalStudents": total_students,
            "todaysAttendance": todays_attendance,
            "absentStudents": absent_students,
            "proxyAlerts": proxy_alerts
        }
    }), 200


# =========================
# 🚀 Run Flask Server
# =========================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
