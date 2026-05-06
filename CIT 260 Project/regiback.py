from flask import request, jsonify, session
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta

  import smtplib
  import os
  from email.mime.multipart import MIMEMultipart
  from email.mime.text import MIMEText


  # ── Email helper ──────────────────────────────────────────────────────────────

  def _pad_id(registration_id):
      return f"CSN-{str(registration_id).zfill(6)}"


  def _format_date(date_str):
      from datetime import datetime as _dt
      try:
          return _dt.strptime(str(date_str), "%Y-%m-%d").strftime("%A, %B %-d, %Y")
      except Exception:
          return str(date_str)


  def _send_confirmation_email(student_email, registration_id, class_name,
                                exam_date, exam_time, campus, building, room):
      """
      Send a styled HTML confirmation email to the student after registration.
      Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables.
      """
      gmail_address = os.environ.get("GMAIL_ADDRESS")
      gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
      if not gmail_address or not gmail_password:
          print("Email credentials not configured — skipping confirmation email.")
          return

      confirmation_id = _pad_id(registration_id)
      formatted_date  = _format_date(exam_date)
      current_year    = __import__('datetime').datetime.now().year

      html_body = f"""
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8"/>
    <title>Exam Registration Confirmed</title>
    <style>
      body {{ margin:0; padding:0; background:#f4f7fc; font-family:'Segoe UI',Arial,sans-serif; color:#1a1a2e; }}
      .wrapper {{ max-width:600px; margin:40px auto; background:#fff; border-radius:8px; overflow:hidden; box-shadow:0 2px 16px rgba(0,61,165,.10); }}
      .header {{ background:#003DA5; padding:28px 32px; text-align:center; }}
      .header h1 {{ margin:0; color:#fff; font-size:22px; font-family:Georgia,serif; }}
      .header p {{ margin:6px 0 0; color:rgba(255,255,255,.80); font-size:14px; }}
      .card {{ margin:28px 32px; border:1px solid #c8d8ef; border-radius:8px; overflow:hidden; border-top:4px solid #003DA5; }}
      .card-header {{ background:#f0f5ff; padding:12px 20px; border-bottom:1px solid #c8d8ef; text-align:center; }}
      .card-header span {{ font-size:11px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#003DA5; }}
      .card-body {{ display:flex; padding:24px 20px; }}
      .col {{ flex:1; }}
      .col+.col {{ border-left:1px solid #e8eef8; padding-left:24px; }}
      .label {{ font-size:11px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:#6b7280; margin-bottom:4px; }}
      .value {{ font-size:17px; font-weight:600; color:#111827; line-height:1.4; }}
      .sub {{ font-size:15px; color:#374151; margin-top:2px; }}
      .block {{ margin-bottom:20px; }}
      .conf-id {{ font-family:'Courier New',monospace; background:#f3f4f6; border-radius:6px; padding:8px 12px; text-align:center; letter-spacing:4px; font-size:18px; color:#1f2937; font-weight:700; }}
      .note {{ background:#f9fafb; border-top:1px solid #e5e7eb; padding:18px 32px; text-align:center; font-size:13px; color:#6b7280; line-height:1.6; }}
      .foot {{ padding:16px 32px 28px; text-align:center; font-size:12px; color:#9ca3af; }}
    </style>
  </head>
  <body>
  <div class="wrapper">
    <div class="header">
      <h1>Registration Confirmed</h1>
      <p>Your exam slot has been successfully booked.</p>
    </div>
    <div class="card">
      <div class="card-header"><span>Official Booking Record</span></div>
      <div class="card-body">
        <div class="col">
          <div class="block"><div class="label">Course</div><div class="value">{class_name}</div></div>
          <div class="block"><div class="label">Date &amp; Time</div><div class="value">{formatted_date}</div><div class="sub">{exam_time}</div></div>
        </div>
        <div class="col">
          <div class="block"><div class="label">Location</div><div class="value">{campus} Campus</div><div class="sub">{building}</div><div class="sub">Room {room}</div></div>
          <div class="block"><div class="label">Confirmation ID</div><div class="conf-id">{confirmation_id}</div></div>
        </div>
      </div>
    </div>
    <div class="note">Please arrive at the testing center at least <strong>15 minutes</strong> before your scheduled time.<br/>Bring a valid photo ID.</div>
    <div class="foot">&copy; {current_year} College of Southern Nevada. All rights reserved.</div>
  </div>
  </body>
  </html>
  """

      text_body = (
          f"Registration Confirmed — Official Booking Record\n"
          f"==============================================\n\n"
          f"Course:          {class_name}\n"
          f"Date:            {formatted_date}\n"
          f"Time:            {exam_time}\n"
          f"Location:        {campus} Campus\n"
          f"Building:        {building}\n"
          f"Room:            {room}\n"
          f"Confirmation ID: {confirmation_id}\n\n"
          f"Please arrive at the testing center at least 15 minutes before your scheduled time.\n"
          f"Bring a valid photo ID.\n\n"
          f"\u00a9 {current_year} College of Southern Nevada. All rights reserved."
      )

      msg = MIMEMultipart("alternative")
      msg["Subject"] = f"Exam Registration Confirmed \u2014 {confirmation_id}"
      msg["From"]    = f"Confirmation CSN <{gmail_address}>"
      msg["To"]      = student_email
      msg.attach(MIMEText(text_body, "plain"))
      msg.attach(MIMEText(html_body, "html"))

      with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
          server.login(gmail_address, gmail_password)
          server.sendmail(gmail_address, student_email, msg.as_string())

      print(f"Confirmation email sent to {student_email} ({confirmation_id})")

  
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
           WHERE ClassID=%s AND LocationID=%s AND SchedulesID=%s AND ExamName=%s""",
        (class_id, location_id, schedule_id, exam_name)
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
        "user_id": <int>,
        "exam_id": <int>  # From dropdown selection
    }

    Or for manual entry:
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
        data = request.get_json()
        user_id = data.get('user_id')
        exam_id = data.get('exam_id')  # New parameter for dropdown selection

        if exam_id:
            # Registration via dropdown selection
            if not user_id or not exam_id:
                return jsonify({'success': False,
                                'message': 'user_id and exam_id are required.'}), 400

            conn = get_db_connection()
            if not conn:
                return jsonify({'success': False, 'message': 'Database connection failed.'}), 500

            cursor = conn.cursor()

            # Get exam details
            cursor.execute("""
                SELECT e.ExamID, c.ClassName, l.Campus, l.Building, l.Room, s.exam_date, s.exam_time
                FROM Exam e
                JOIN class c ON e.ClassID = c.ClassID
                JOIN Location l ON e.LocationID = l.LocationID
                JOIN Schedules s ON e.SchedulesID = s.SchedulesID
                WHERE e.ExamID = %s
            """, (exam_id,))
            exam_row = cursor.fetchone()
            if not exam_row:
                cursor.close(); conn.close()
                return jsonify({'success': False, 'message': 'Exam not found.'}), 404

            exam_date = str(exam_row[5])
            exam_time = str(exam_row[6])[:5]  # HH:MM
            subject = exam_row[1]
            location = exam_row[2]
            building = exam_row[3]
            room = exam_row[4]
            proctor = ''

        else:
            # Manual entry (original logic)
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
                'proctor':  proctor or ''
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


def get_classes(get_db_connection):
    """
    Fetch all classes from the database
    Returns JSON: {"success": true, "classes": [{"ClassID": 1, "ClassName": "ENG"}, ...]}
    """
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Query all classes from the class table
        query = "SELECT ClassID, ClassName FROM class ORDER BY ClassName ASC"
        cursor.execute(query)
        classes = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'classes': classes
        }), 200
    
    except Exception as e:
        print(f"Error fetching classes: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while fetching classes'}), 500


def get_exams_by_class(class_id, get_db_connection):
    """
    Fetch all exams for a specific class ID from the database
    Returns JSON: {"success": true, "exams": [{"ExamID": 1, "ExamName": "Midterm"}, ...]}
    """
    try:
        if not class_id:
            return jsonify({'success': False, 'message': 'Class ID is required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Query all exams for the given ClassID
        query = "SELECT ExamID, ExamName FROM Exam WHERE ClassID = %s ORDER BY ExamName ASC"
        cursor.execute(query, (class_id,))
        exams = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'exams': exams
        }), 200
    
    except Exception as e:
        print(f"Error fetching exams: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while fetching exams'}), 500


def get_campuses_by_exam(class_id, exam_id, get_db_connection):
    """
    Fetch all unique campuses for a specific class and exam
    Returns JSON: {"success": true, "campuses": [{"LocationID": 1, "Campus": "Henderson"}, ...]}
    """
    try:
        if not class_id or not exam_id:
            return jsonify({'success': False, 'message': 'Class ID and Exam ID are required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Query distinct campuses for the given ClassID and ExamID
        query = """
            SELECT DISTINCT l.LocationID, l.Campus 
            FROM Location l
            INNER JOIN Exam e ON l.LocationID = e.LocationID
            WHERE e.ClassID = %s AND e.ExamID = %s
            ORDER BY l.Campus ASC
        """
        cursor.execute(query, (class_id, exam_id))
        campuses = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'campuses': campuses
        }), 200
    
    except Exception as e:
        print(f"Error fetching campuses: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while fetching campuses'}), 500


def get_dates_by_campus(class_id, exam_id, location_id, get_db_connection):
    """
    Fetch all unique dates for a specific class, exam, and campus
    Returns JSON: {"success": true, "dates": [{"SchedulesID": 1, "exam_date": "2026-05-10"}, ...]}
    """
    try:
        if not class_id or not exam_id or not location_id:
            return jsonify({'success': False, 'message': 'Class ID, Exam ID, and Location ID are required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Query distinct dates for the given ClassID, ExamID, and LocationID
        query = """
            SELECT DISTINCT s.SchedulesID, s.exam_date 
            FROM Schedules s
            INNER JOIN Exam e ON s.SchedulesID = e.SchedulesID
            WHERE e.ClassID = %s AND e.ExamID = %s AND e.LocationID = %s
            ORDER BY s.exam_date ASC
        """
        cursor.execute(query, (class_id, exam_id, location_id))
        dates = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'dates': dates
        }), 200
    
    except Exception as e:
        print(f"Error fetching dates: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while fetching dates'}), 500


def get_times_by_date(class_id, exam_id, location_id, schedule_id, get_db_connection):
    """
    Fetch all times for a specific class, exam, campus, and date
    Returns JSON: {"success": true, "times": [{"SchedulesID": 1, "exam_time": "08:00:00"}, ...]}
    """
    try:
        print(f"get_times_by_date called with: class_id={class_id}, exam_id={exam_id}, location_id={location_id}, schedule_id={schedule_id}")
        
        if not class_id or not exam_id or not location_id or not schedule_id:
            print("Missing required parameters")
            return jsonify({'success': False, 'message': 'All parameters are required'}), 400
        
        connection = get_db_connection()
        if not connection:
            print("Database connection failed")
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # First get the selected date
        print(f"Getting date for schedule_id: {schedule_id}")
        cursor.execute("SELECT exam_date FROM Schedules WHERE SchedulesID = %s", (schedule_id,))
        date_result = cursor.fetchone()
        print(f"Date result: {date_result}")
        
        if not date_result:
            print("Invalid schedule ID")
            return jsonify({'success': False, 'message': 'Invalid schedule ID'}), 400
        
        selected_date = date_result['exam_date']
        print(f"Selected date: {selected_date}")
        
        # Query all schedules with the same date that have exams matching the criteria
        query = """
            SELECT DISTINCT s.SchedulesID, s.exam_time 
            FROM Schedules s
            INNER JOIN Exam e ON s.SchedulesID = e.SchedulesID
            WHERE s.exam_date = %s 
            AND e.ClassID = %s 
            AND e.ExamID = %s 
            AND e.LocationID = %s
            ORDER BY s.exam_time ASC
        """
        print(f"Executing query with params: {selected_date}, {class_id}, {exam_id}, {location_id}")
        cursor.execute(query, (selected_date, class_id, exam_id, location_id))
        times = cursor.fetchall()
        print(f"Times found: {times}")

        # Convert TIMEDIFF / time objects into JSON-safe strings
        for item in times:
            exam_time = item.get('exam_time')
            if isinstance(exam_time, timedelta):
                total_seconds = int(exam_time.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes = remainder // 60
                item['exam_time'] = f"{hours:02d}:{minutes:02d}:00"
            else:
                item['exam_time'] = str(exam_time)
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'times': times
        }), 200
    
    except Exception as e:
        print(f"Error fetching times: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'An error occurred while fetching times'}), 500
