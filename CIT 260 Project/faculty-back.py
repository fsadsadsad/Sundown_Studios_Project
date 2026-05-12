from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from datetime import timedelta
import os

app = Flask(__name__)
app.secret_key = 'csn-faculty-secret-2026'
CORS(app, supports_credentials=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Database config ───────────────────────────────────────────────────────────
# Matches the credentials used in regiback.py
db_config = {
    'host':     'localhost',
    'user':     'root',
    'password': 'IhavenoideawhatImdoing00',
    'database': 'sundown_studios'
}

def get_db():
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        print(f'DB connection error: {e}')
        return None

def _time_str(t):
    """Convert timedelta or time object to HH:MM string."""
    if isinstance(t, timedelta):
        total = int(t.total_seconds())
        h, rem = divmod(total, 3600)
        return f'{h:02d}:{rem // 60:02d}'
    return str(t)[:5]

# ── Serve the faculty page ────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'faculty.html')

# ── Exams ─────────────────────────────────────────────────────────────────────

@app.route('/api/faculty/exams', methods=['GET'])
def get_exams():
    """Return all exams with subject, schedule, location, and enrollment count."""
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            e.ExamID,
            c.ClassName          AS subject,
            e.ExamName,
            l.Campus             AS location,
            l.Building           AS building,
            l.Room               AS room,
            s.exam_date          AS date,
            s.exam_time          AS time,
            COUNT(r.RegistrationsID) AS enrollment
        FROM Exam e
        JOIN class     c ON e.ClassID      = c.ClassID
        JOIN Location  l ON e.LocationID   = l.LocationID
        JOIN Schedules s ON e.SchedulesID  = s.SchedulesID
        LEFT JOIN Registrations r ON e.ExamID = r.ExamID
        GROUP BY e.ExamID
        ORDER BY s.exam_date, s.exam_time
    """)
    exams = cursor.fetchall()
    cursor.close()
    conn.close()

    for ex in exams:
        ex['date'] = str(ex['date'])
        ex['time'] = _time_str(ex['time'])

    return jsonify({'success': True, 'exams': exams}), 200


@app.route('/api/faculty/exams', methods=['POST'])
def add_exam():
    """Create a new exam entry (and its supporting class/location/schedule rows)."""
    data     = request.get_json() or {}
    subject  = data.get('subject', '').strip()
    exam_date = data.get('date', '').strip()
    exam_time = data.get('time', '').strip()
    location = data.get('location', '').strip()
    building = data.get('building', '').strip()
    room     = data.get('room', '').strip()

    if not subject or not exam_date or not exam_time:
        return jsonify({'success': False,
                        'message': 'Subject, date, and time are required'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = conn.cursor()

    # Get or create class
    cursor.execute('SELECT ClassID FROM class WHERE ClassName = %s', (subject,))
    row = cursor.fetchone()
    class_id = row[0] if row else None
    if class_id is None:
        cursor.execute('INSERT INTO class (ClassName) VALUES (%s)', (subject,))
        class_id = cursor.lastrowid

    # Get or create location
    cursor.execute(
        'SELECT LocationID FROM Location WHERE Campus=%s AND Building=%s AND Room=%s',
        (location, building, room)
    )
    row = cursor.fetchone()
    location_id = row[0] if row else None
    if location_id is None:
        cursor.execute(
            'INSERT INTO Location (Campus, Building, Room) VALUES (%s, %s, %s)',
            (location, building, room)
        )
        location_id = cursor.lastrowid

    # Get or create schedule
    cursor.execute(
        'SELECT SchedulesID FROM Schedules WHERE exam_date=%s AND exam_time=%s',
        (exam_date, exam_time)
    )
    row = cursor.fetchone()
    schedule_id = row[0] if row else None
    if schedule_id is None:
        cursor.execute(
            'INSERT INTO Schedules (exam_date, exam_time) VALUES (%s, %s)',
            (exam_date, exam_time)
        )
        schedule_id = cursor.lastrowid

    # Create exam
    exam_name = f'{subject} Exam'
    cursor.execute(
        'INSERT INTO Exam (ClassID, LocationID, SchedulesID, ExamName) VALUES (%s, %s, %s, %s)',
        (class_id, location_id, schedule_id, exam_name)
    )
    exam_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'success': True, 'message': 'Exam added', 'exam_id': exam_id}), 201

# ── Students in an exam ───────────────────────────────────────────────────────

@app.route('/api/faculty/exams/<int:exam_id>/students', methods=['GET'])
def get_exam_students(exam_id):
    """Return all students (id + email) enrolled in the given exam."""
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id AS user_id, u.username AS email
        FROM Registrations r
        JOIN user u ON r.UserID = u.id
        WHERE r.ExamID = %s
        ORDER BY u.username
    """, (exam_id,))
    students = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({'success': True, 'students': students}), 200


@app.route('/api/faculty/exams/<int:exam_id>/students', methods=['POST'])
def add_student_to_exam(exam_id):
    """Enroll a student in an exam."""
    data    = request.get_json() or {}
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'success': False, 'message': 'user_id is required'}), 400

    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = conn.cursor()

    # Duplicate check
    cursor.execute(
        'SELECT RegistrationsID FROM Registrations WHERE UserID=%s AND ExamID=%s',
        (user_id, exam_id)
    )
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'success': False,
                        'message': 'Student is already enrolled in this exam'}), 409

    try:
        cursor.execute(
            'INSERT INTO Registrations (UserID, ExamID) VALUES (%s, %s)',
            (user_id, exam_id)
        )
        conn.commit()
    except mysql.connector.errors.DatabaseError as e:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': str(e.msg)}), 409

    cursor.close()
    conn.close()
    return jsonify({'success': True, 'message': 'Student added to exam'}), 201


@app.route('/api/faculty/exams/<int:exam_id>/students/<int:user_id>', methods=['DELETE'])
def remove_student_from_exam(exam_id, user_id):
    """Remove a student from an exam."""
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM Registrations WHERE ExamID=%s AND UserID=%s',
        (exam_id, user_id)
    )
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()

    if affected == 0:
        return jsonify({'success': False, 'message': 'Registration not found'}), 404
    return jsonify({'success': True, 'message': 'Student removed from exam'}), 200

# ── Subjects & location lookup ────────────────────────────────────────────────

@app.route('/api/faculty/subjects', methods=['GET'])
def get_subjects():
    """Return all subjects (classes) for the subject dropdown."""
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT ClassID, ClassName FROM class ORDER BY ClassName')
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({'success': True, 'subjects': subjects}), 200


@app.route('/api/faculty/subjects/<int:class_id>/location', methods=['GET'])
def get_subject_location(class_id):
    """
    Return the location of the first existing exam for this subject so the
    right-panel location fields can be auto-populated when a subject is selected.
    Returns null if no exam for this subject exists yet.
    """
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT l.Campus AS location, l.Building AS building, l.Room AS room
        FROM Exam e
        JOIN Location l ON e.LocationID = l.LocationID
        WHERE e.ClassID = %s
        LIMIT 1
    """, (class_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return jsonify({'success': True, 'location': row}), 200

# ── Users list ────────────────────────────────────────────────────────────────

@app.route('/api/faculty/users', methods=['GET'])
def get_all_users():
    """Return all registered users for the add-student dropdown."""
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, username AS email FROM user ORDER BY username')
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({'success': True, 'users': users}), 200

# ── Logout ────────────────────────────────────────────────────────────────────

@app.route('/api/faculty/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'}), 200

# ── Health check ─────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'faculty server running'}), 200

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5001)
