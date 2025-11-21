from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import datetime
import cv2
import numpy as np
import base64
import time
import sqlite3

app = Flask(__name__)
CORS(app)

DB_PATH = "database.db"




# ================================
# ✅ CONNECT TO SQLITE DATABASE
# ================================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # so we can use dict(row)
    return conn


# ================================
# 🔵 ROOT API
# ================================
@app.route('/')
def home():
    return "🚀 Smart Attendance Backend Connected to SQLite"


# ================================
# 👨‍💼 ADMIN LOGIN
# ================================
@app.route('/admin-login', methods=['POST'])
def admin_login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM admins WHERE email=? AND password=?",
        (email, password)
    )
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

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

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM teachers WHERE email=? AND password=?",
        (email, password)
    )
    teacher = cursor.fetchone()
    cursor.close()
    conn.close()

    if teacher:
        return jsonify({"success": True, "token": "teacher_token"}), 200
    else:
        return jsonify({"success": False, "message": "Invalid teacher login"}), 401


# ================================
# 🎓 GET STUDENTS
# ================================
@app.route('/get-students', methods=['GET'])
def get_students():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    students = [dict(row) for row in rows]
    return jsonify(students)


# ================================
# 🎓 ADD STUDENT
# ================================
@app.route('/add-student', methods=['POST'])
def add_student():
    data = request.json
    name = data["name"]
    roll = data["roll"]
    branch = data["branch"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE roll=?", (roll,))
    exists = cursor.fetchone()

    if exists:
        cursor.close()
        conn.close()
        return jsonify({"message": "Student with this roll already exists"}), 400

    cursor.execute(
        "INSERT INTO students (name, roll, branch) VALUES (?, ?, ?)",
        (name, roll, branch)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Student added successfully"}), 200


# ================================
# 🗑 DELETE STUDENT
# ================================
@app.route('/delete-student/<roll>', methods=['DELETE'])
def delete_student(roll):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM students WHERE roll=?", (roll,))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Student deleted successfully"}), 200


# ================================
# 🕒 MARK ATTENDANCE (MANUAL)
# ================================
@app.route('/mark', methods=['POST'])
def mark_attendance():
    data = request.json
    name = data["name"]
    roll = data["roll"]

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM attendance WHERE roll=? AND date=?",
        (roll, today)
    )
    exists = cursor.fetchone()

    if exists:
        cursor.close()
        conn.close()
        return jsonify({"message": f"{name} already marked today"}), 200

    cursor.execute(
        "INSERT INTO attendance (name, roll, date, time) VALUES (?, ?, ?, ?)",
        (name, roll, today, now_time)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": f"{name} marked present"}), 200


# ================================
# 📅 GET ATTENDANCE HISTORY
# ================================
@app.route('/attendance-history', methods=['GET'])
def attendance_history():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM attendance ORDER BY date DESC")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    history = [dict(row) for row in rows]
    return jsonify(history)


# ================================
# 📊 DASHBOARD STATS
# ================================
@app.route('/dashboard-stats', methods=['GET'])
def dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()["total"]

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) AS present FROM attendance WHERE date=?", (today,))
    todays_attendance = cursor.fetchone()["present"]

    absent = total_students - todays_attendance

    cursor.close()
    conn.close()

    return jsonify({
        "success": True,
        "stats": {
            "totalStudents": total_students,
            "todaysAttendance": todays_attendance,
            "absentStudents": absent,
            "proxyAlerts": 0
        }
    })


# ============================================
# 🤖 FACE RECOGNITION WITH OPENCV + LBPH
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, "faces")
os.makedirs(FACES_DIR, exist_ok=True)

def preprocess_image_bgr(bgr_img):
    gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (200, 200))
    return gray

def decode_base64_image(image_b64):
    if "," in image_b64:
        image_b64 = image_b64.split(",")[1]
    try:
        img_data = base64.b64decode(image_b64)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    except:
        return None

def load_training_data():
    images, labels = [], []
    roll_to_label, label_to_roll = {}, {}
    current_label = 0

    for fname in os.listdir(FACES_DIR):
        path = os.path.join(FACES_DIR, fname)
        if not fname.endswith(".jpg"):
            continue

        roll = fname.split("_")[0]

        if roll not in roll_to_label:
            roll_to_label[roll] = current_label
            label_to_roll[current_label] = roll
            current_label += 1

        label = roll_to_label[roll]
        img = cv2.imread(path)
        if img is None:
            continue
        gray = preprocess_image_bgr(img)
        images.append(gray)
        labels.append(label)

    if len(images) == 0:
        return None, None, None

    return images, np.array(labels), label_to_roll

def train_lbph_model():
    data, labels, label_to_roll = load_training_data()
    if data is None:
        return None, None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(data, labels)
    return recognizer, label_to_roll

def mark_attendance_in_db(roll):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE roll=?", (roll,))
    student = cursor.fetchone()
    if not student:
        return False, "Student not found"

    name = student["name"]

    cursor.execute("SELECT * FROM attendance WHERE roll=? AND date=?", (roll, today))
    exists = cursor.fetchone()

    if exists:
        return True, f"{name} already marked today"

    cursor.execute(
        "INSERT INTO attendance (name, roll, date, time) VALUES (?, ?, ?, ?)",
        (name, roll, today, now_time)
    )
    conn.commit()

    return True, f"{name} marked present"


@app.route('/upload-face', methods=['POST'])
def upload_face():
    data = request.json
    roll = data.get("roll")
    image_b64 = data.get("image")

    if not roll or not image_b64:
        return jsonify({"success": False, "message": "roll and image are required"}), 400

    img = decode_base64_image(image_b64)
    if img is None:
        return jsonify({"success": False, "message": "Invalid image data"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE roll=?", (roll,))
    student = cursor.fetchone()
    cursor.close()
    conn.close()

    if not student:
        return jsonify({"success": False, "message": "Student not found"}), 404

    ts = int(time.time())
    filename = f"{roll}_{ts}.jpg"
    save_path = os.path.join(FACES_DIR, filename)
    cv2.imwrite(save_path, img)

    return jsonify({"success": True, "message": "Face saved"}), 200


@app.route('/recognize-face', methods=['POST'])
def recognize_face():
    data = request.json
    image_b64 = data.get("image")

    if not image_b64:
        return jsonify({"success": False, "match": False, "message": "image required"}), 400

    img = decode_base64_image(image_b64)
    if img is None:
        return jsonify({"success": False, "match": False, "message": "Invalid image"}), 400

    gray = preprocess_image_bgr(img)

    recognizer, label_to_roll = train_lbph_model()
    if recognizer is None:
        return jsonify({"success": False, "match": False, "message": "No training data"}), 400

    label, confidence = recognizer.predict(gray)
    THRESHOLD = 80.0

    if confidence > THRESHOLD:
        return jsonify({"success": True, "match": False, "message": "Unknown face"}), 200

    roll = label_to_roll[label]
    ok, msg = mark_attendance_in_db(roll)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE roll=?", (roll,))
    student = cursor.fetchone()
    name = student["name"] if student else None

    return jsonify({
        "success": ok,
        "match": True,
        "roll": roll,
        "name": name,
        "message": msg
    }), 200

print("Using DB at:", os.path.abspath(DB_PATH))#remove

# ================================
# 🌱 SEED DEFAULT ADMIN & TEACHER
# ================================
@app.route('/seed-users', methods=['POST'])
def seed_users():
    conn = get_db()
    cursor = conn.cursor()

    # default admin
    cursor.execute(
        "INSERT OR IGNORE INTO admins (email, password) VALUES (?, ?)",
        ("admin@gmail.com", "admin123")
    )

    # default teacher
    cursor.execute(
        "INSERT OR IGNORE INTO teachers (email, password) VALUES (?, ?)",
        ("teacher@gmail.com", "teacher123")
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Default admin and teacher created (if they didn't already exist).",
        "admin": {"email": "admin@gmail.com", "password": "admin123"},
        "teacher": {"email": "teacher@gmail.com", "password": "teacher123"}
    }), 200


# ================================
# 🔧 INIT DB (CREATE TABLES)
# ================================

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll TEXT UNIQUE,
            branch TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll TEXT,
            date TEXT,
            time TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("Tables created successfully!")

with app.app_context():
    init_db()

# ================================
# 🚀 RUN SERVER (LOCAL)
# ================================
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
