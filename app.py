from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import os
import datetime
import cv2
import numpy as np
import base64
import time

app = Flask(__name__)
CORS(app)

# ================================
# ✅ CONNECT TO RAILWAY DATABASE
# ================================
def get_db():
    return pymysql.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT")),
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
# 🕒 MARK ATTENDANCE (MANUAL)
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


# ============================================
# 🤖 FACE RECOGNITION WITH OPENCV + LBPH
# ============================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, "faces")

os.makedirs(FACES_DIR, exist_ok=True)  # ensure folder exists


def preprocess_image_bgr(bgr_img):
    """
    Convert BGR image to grayscale and resize to fixed size.
    We assume the image is mostly a face (no fancy detection).
    """
    gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (200, 200))  # fixed size
    return gray


def decode_base64_image(image_b64):
    """
    image_b64 is expected like: 'data:image/jpeg;base64,...'
    or plain base64 string.
    """
    if "," in image_b64:
        image_b64 = image_b64.split(",")[1]
    try:
        img_data = base64.b64decode(image_b64)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print("Error decoding base64:", e)
        return None


def load_training_data():
    """
    Load all images from faces/ directory,
    build X (images) and y (labels) for LBPH,
    and a map label -> roll.
    Filenames format: <roll>_timestamp.jpg
    """
    images = []
    labels = []
    roll_to_label = {}
    label_to_roll = {}
    current_label = 0

    for fname in os.listdir(FACES_DIR):
        path = os.path.join(FACES_DIR, fname)
        if not os.path.isfile(path):
            continue
        if not (fname.lower().endswith(".jpg") or fname.lower().endswith(".png")):
            continue

        # filename: roll_timestamp.jpg -> roll
        parts = fname.split("_")
        if len(parts) < 2:
            continue
        roll = parts[0]

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

    return images, np.array(labels, dtype=np.int32), label_to_roll


def train_lbph_model():
    data, labels, label_to_roll = load_training_data()
    if data is None or labels is None or label_to_roll is None:
        return None, None

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(data, labels)
    return recognizer, label_to_roll


def mark_attendance_in_db(roll):
    """
    Helper: mark attendance for given roll by looking up student name.
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    db = get_db()
    cursor = db.cursor()

    # find student
    cursor.execute("SELECT * FROM students WHERE roll=%s", (roll,))
    student = cursor.fetchone()
    if not student:
        cursor.close()
        db.close()
        return False, "Student not found"

    name = student["name"]

    # check if already marked
    cursor.execute(
        "SELECT * FROM attendance WHERE roll=%s AND date=%s",
        (roll, today)
    )
    exists = cursor.fetchone()
    if exists:
        cursor.close()
        db.close()
        return True, f"{name} already marked today"

    # insert
    cursor.execute(
        "INSERT INTO attendance (name, roll, date, time) VALUES (%s, %s, %s, NOW())",
        (name, roll, today)
    )
    db.commit()

    cursor.close()
    db.close()
    return True, f"{name} marked present"


# ================================
# 📸 UPLOAD FACE FOR A STUDENT
# ================================
@app.route('/upload-face', methods=['POST'])
def upload_face():
    """
    Body JSON: { "roll": "...", "image": "<base64 string>" }
    Saves the image to faces/<roll>_<timestamp>.jpg
    """
    data = request.json
    roll = data.get("roll")
    image_b64 = data.get("image")

    if not roll or not image_b64:
        return jsonify({"success": False, "message": "roll and image are required"}), 400

    img = decode_base64_image(image_b64)
    if img is None:
        return jsonify({"success": False, "message": "Invalid image data"}), 400

    # ensure student exists
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students WHERE roll=%s", (roll,))
    student = cursor.fetchone()
    cursor.close()
    db.close()

    if not student:
        return jsonify({"success": False, "message": "Student not found for this roll"}), 404

    # save image
    ts = int(time.time())
    filename = f"{roll}_{ts}.jpg"
    save_path = os.path.join(FACES_DIR, filename)
    cv2.imwrite(save_path, img)

    return jsonify({"success": True, "message": "Face image saved for training"}), 200


# ================================
# 🎯 RECOGNIZE FACE & MARK ATTENDANCE
# ================================
@app.route('/recognize-face', methods=['POST'])
def recognize_face():
    """
    Body JSON: { "image": "<base64>" }
    Trains LBPH model on existing faces and tries to match.
    If match found -> marks attendance.
    """
    data = request.json
    image_b64 = data.get("image")

    if not image_b64:
        return jsonify({"success": False, "match": False, "message": "image is required"}), 400

    img = decode_base64_image(image_b64)
    if img is None:
        return jsonify({"success": False, "match": False, "message": "Invalid image data"}), 400

    gray = preprocess_image_bgr(img)

    recognizer, label_to_roll = train_lbph_model()
    if recognizer is None or label_to_roll is None:
        return jsonify({
            "success": False,
            "match": False,
            "message": "No training data available. Upload faces first."
        }), 400

    label, confidence = recognizer.predict(gray)
    print("Prediction:", label, "conf:", confidence)

    # smaller confidence = better match. Threshold around 70–90 is common.
    THRESHOLD = 80.0
    if confidence > THRESHOLD:
        return jsonify({
            "success": True,
            "match": False,
            "message": "Unknown face / no close match"
        }), 200

    roll = label_to_roll.get(label)
    if not roll:
        return jsonify({
            "success": False,
            "match": False,
            "message": "Matched label but roll not found"
        }), 500

    ok, msg = mark_attendance_in_db(roll)

    # fetch name again for response
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students WHERE roll=%s", (roll,))
    student = cursor.fetchone()
    cursor.close()
    db.close()

    name = student["name"] if student else None

    return jsonify({
        "success": ok,
        "match": True,
        "roll": roll,
        "name": name,
        "message": msg
    }), 200

#temp
@app.route('/env')
def env_test():
    return {
        "MYSQLHOST": os.getenv("MYSQLHOST"),
        "MYSQLUSER": os.getenv("MYSQLUSER"),
        "MYSQLPASSWORD": os.getenv("MYSQLPASSWORD"),
        "MYSQLDATABASE": os.getenv("MYSQLDATABASE"),
        "MYSQLPORT": os.getenv("MYSQLPORT")
    }


# ================================
# 🚀 RUN SERVER (LOCAL)
# ================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
