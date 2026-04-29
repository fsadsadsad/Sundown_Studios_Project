from flask import request, jsonify, session
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta

# ── DB config (shared with userback.py) ──────────────────────────────────────
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'IhavenoideawhatImdoing00',
    'database': 'sundown_studios'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_location(cursor, campus, building, room):
    """Return LocationID, creating the row if it doesn't exist."""
    cursor.execute(
        "SELECT LocationID FROM Location WHERE Campus=%s AND Building=%s AND Room=%s",
        (campus, building, room)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO Location (Campus, Building, Room) VALUES (%s, %s, %s)",
        (campus, building, room)
    )
    return cursor.lastrowid


def _get_or_create_schedule(cursor, exam_date, exam_time):
    """Return SchedulesID, creating the row if it doesn't exist."""
    cursor.execute(
        "SELECT SchedulesID FROM Schedules WHERE exam_date=%s AND exam_time=%s",
        (exam_date, exam_time)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO Schedules (exam_date, exam_time) VALUES (%s, %s)",
        (exam_date, exam_time)
    )
    return cursor.lastrowid


def _get_or_create_class(cursor, subject):
    """Return ClassID, creating the row if it doesn't exist."""
    cursor.execute("SELECT ClassID FROM class WHERE ClassName=%s", (subject,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO class (ClassName) VALUES (%s)", (subject,))
    return cursor.lastrowid


def _get_or_create_exam(cursor, class_id, location_id, schedule_id, exam_name):
    """Return ExamID, creating the row if it doesn't exist."""
    cursor.execute(
        """SELECT ExamID FROM Exam
           WHERE ClassID=%s AND LocationID=%s AND SchedulesID=%s""",
        (class_id, location_id, schedule_id)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        """INSERT INTO Exam (ClassID, LocationID, SchedulesID, ExamName)
           VALUES (%s, %s, %s, %s)""",
        (class_id, location_id, schedule_id, exam_name)
    )
    return cursor.lastrowid


def _user_has_time_conflict(cursor, user_id, new_date, new_time_str):
    """
    Return True if the user already has an exam on new_date whose time is
    within 60 minutes (before or after) of new_time_str.
    """
    cursor.execute(
        """SELECT s.exam_date, s.exam_time
           FROM Registrations r
           JOIN Exam e       ON r.ExamID      = e.ExamID
           JOIN Schedules s  ON e.SchedulesID = s.SchedulesID
           WHERE r.UserID = %s AND s.exam_date = %s""",
        (user_id, new_date)
    )
    existing = cursor.fetchall()

    # new_time_str is "HH:MM" or "HH:MM:SS"
    new_dt = datetime.strptime(new_time_str[:5], "%H:%M")

    for _, existing_time in existing:
        # existing_time may be a timedelta (mysql connector) or time object
        if isinstance(existing_time, timedelta):
            total_seconds = int(existing_time.total_seconds())
            existing_dt = datetime(1900, 1, 1) + timedelta(seconds=total_seconds)
        else:
            existing_dt = datetime.strptime(str(existing_time)[:5], "%H:%M")

        diff = abs((new_dt - existing_dt).total_seconds()) / 60
        if diff < 60:
            return True, existing_dt.strftime("%H:%M")

    return False, None


# ── Routes ────────────────────────────────────────────────────────────────────

def logout():
    """Clear user session and logout."""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200


def schedule_exam():
    """
    POST /api/schedule
    Register the logged-in user for an exam slot.

    Expects JSON:
    {
        "user_id":  <int>,
        "date":     "YYYY-MM-DD",
        "time":     "HH:MM",
        "location": "Henderson" | "Charleston" | "North",
        "building": "Building A",
        "room":     "101",
        "subject":  "MATH",
        "proctor":  "Mr. Smith"
    }

    Business rules enforced here (in addition to DB triggers):
      1. No duplicate exam (same ExamID) per user.
      2. No exam within 60 minutes of an existing exam on the same date.
      3. Max 3 exams per user  (also enforced by DB trigger).
      4. Max 20 students per exam (also enforced by DB trigger).
    """
    try:
        data      = request.get_json()
        user_id   = data.get('user_id')
        exam_date = data.get('date', '').strip()
        exam_time = data.get('time', '').strip()
        location  = data.get('location', '').strip()
        building  = data.get('building', '').strip()
        room      = data.get('room', '').strip()
        subject   = data.get('subject', '').strip()
        proctor   = data.get('proctor', '').strip()

        # ── Basic validation ──────────────────────────────────────────────────
        if not all([user_id, exam_date, exam_time, location, subject]):
            return jsonify({'success': False,
                            'message': 'Date, time, location, and subject are required.'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed.'}), 500

        cursor = conn.cursor()

        # ── Resolve / create supporting rows ─────────────────────────────────
        location_id  = _get_or_create_location(cursor, location, building, room)
        schedule_id  = _get_or_create_schedule(cursor, exam_date, exam_time)
        class_id     = _get_or_create_class(cursor, subject)
        exam_name    = f"{subject} Exam"
        exam_id      = _get_or_create_exam(cursor, class_id, location_id,
                                           schedule_id, exam_name)

        # ── Rule 1: duplicate exam check ──────────────────────────────────────
        cursor.execute(
            "SELECT RegistrationsID FROM Registrations WHERE UserID=%s AND ExamID=%s",
            (user_id, exam_id)
        )
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({'success': False,
                            'message': 'You are already registered for this exact exam.'}), 409

        # ── Rule 2: 1-hour buffer check ───────────────────────────────────────
        conflict, conflict_time = _user_has_time_conflict(
            cursor, user_id, exam_date, exam_time
        )
        if conflict:
            cursor.close(); conn.close()
            return jsonify({
                'success': False,
                'message': (f'Time conflict: you already have an exam at {conflict_time} '
                            f'on {exam_date}. Exams must be at least 1 hour apart.')
            }), 409

        # ── Insert registration (DB triggers enforce 3-exam & 20-student caps) ─
        try:
            cursor.execute(
                "INSERT INTO Registrations (UserID, ExamID) VALUES (%s, %s)",
                (user_id, exam_id)
            )
            conn.commit()
        except mysql.connector.errors.DatabaseError as db_err:
            cursor.close(); conn.close()
            # Surface the trigger message directly to the client
            return jsonify({'success': False, 'message': str(db_err.msg)}), 409

        # ── Return the new registration with its details ──────────────────────
        reg_id = cursor.lastrowid
        cursor.close(); conn.close()

        return jsonify({
            'success': True,
            'message': 'Exam scheduled successfully.',
            'registration': {
                'id':       reg_id,
                'exam_id':  exam_id,
                'subject':  subject,
                'date':     exam_date,
                'time':     exam_time,
                'location': location,
                'building': building,
                'room':     room,
                'proctor':  proctor
            }
        }), 201

    except Exception as e:
        print(f"Error during schedule_exam: {e}")
        return jsonify({'success': False, 'message': 'An unexpected server error occurred.'}), 500


def get_user_exams():
    """
    GET /api/schedule?user_id=<id>
    Return all exams the user is registered for (up to 3).
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id is required.'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed.'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT r.RegistrationsID AS id,
                      e.ExamID          AS exam_id,
                      c.ClassName       AS subject,
                      s.exam_date       AS date,
                      s.exam_time       AS time,
                      l.Campus          AS location,
                      l.Building        AS building,
                      l.Room            AS room
               FROM Registrations r
               JOIN Exam      e ON r.ExamID      = e.ExamID
               JOIN class     c ON e.ClassID      = c.ClassID
               JOIN Schedules s ON e.SchedulesID  = s.SchedulesID
               JOIN Location  l ON e.LocationID   = l.LocationID
               WHERE r.UserID = %s
               ORDER BY s.exam_date, s.exam_time""",
            (user_id,)
        )
        exams = cursor.fetchall()
        cursor.close(); conn.close()

        # Convert date/timedelta to strings for JSON
        for ex in exams:
            ex['date'] = str(ex['date'])
            t = ex['time']
            if isinstance(t, timedelta):
                total = int(t.total_seconds())
                h, rem = divmod(total, 3600)
                m = rem // 60
                ex['time'] = f"{h:02d}:{m:02d}"
            else:
                ex['time'] = str(t)[:5]

        return jsonify({'success': True, 'exams': exams}), 200

    except Exception as e:
        print(f"Error during get_user_exams: {e}")
        return jsonify({'success': False, 'message': 'An unexpected server error occurred.'}), 500


def cancel_exam():
    """
    DELETE /api/schedule/<registration_id>
    Remove a registration, verifying it belongs to the requesting user.
    """
    try:
        data    = request.get_json()
        user_id = data.get('user_id')
        reg_id  = request.view_args.get('registration_id')

        if not user_id or not reg_id:
            return jsonify({'success': False, 'message': 'user_id and registration_id are required.'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed.'}), 500

        cursor = conn.cursor()

        # Confirm ownership before deleting
        cursor.execute(
            "SELECT RegistrationsID FROM Registrations WHERE RegistrationsID=%s AND UserID=%s",
            (reg_id, user_id)
        )
        if not cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({'success': False,
                            'message': 'Registration not found or not yours.'}), 404

        cursor.execute("DELETE FROM Registrations WHERE RegistrationsID=%s", (reg_id,))
        conn.commit()
        cursor.close(); conn.close()

        return jsonify({'success': True, 'message': 'Exam cancelled successfully.'}), 200

    except Exception as e:
        print(f"Error during cancel_exam: {e}")
        return jsonify({'success': False, 'message': 'An unexpected server error occurred.'}), 500
