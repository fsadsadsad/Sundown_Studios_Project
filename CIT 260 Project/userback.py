from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import bcrypt
import os
import sys

# Import regiback from current directory
sys.path.insert(0, os.path.dirname(__file__))
import regiback

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',  # Change to your MySQL username
    'password': 'IhavenoideawhatImdoing00',  # Change to your MySQL password
    'database': 'sundown_studios'  # Change to your database name
}

def get_db_connection():
    """Establish and return a database connection"""
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_database():
    """Check if the database and table exist"""
    try:
        # Connect without specifying database first
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = connection.cursor()
        
        # Check if database exists
        cursor.execute(f"SHOW DATABASES LIKE '{db_config['database']}'")
        if not cursor.fetchone():
            print(f"ERROR: Database '{db_config['database']}' does not exist. Please create it first.")
            cursor.close()
            connection.close()
            return False
        
        # Switch to the database
        cursor.execute(f"USE {db_config['database']}")
        
        # Check if user table exists
        cursor.execute(f"SHOW TABLES LIKE 'user'")
        if not cursor.fetchone():
            print("ERROR: Table 'user' does not exist. Please run table.sql to create it.")
            cursor.close()
            connection.close()
            return False
        
        print("Database and table verified successfully")
        cursor.close()
        connection.close()
        return True
    except Error as e:
        print(f"Error checking database: {e}")
        return False

@app.route('/api/login', methods=['POST'])
def login():
    """
    Handle login requests
    Expects JSON: {"username": "user", "password": "pass"}
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'}), 400
        
        # Connect to database
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # Query for user
        query = "SELECT id, username, password_hash FROM user WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        # Check if user exists and password matches
        valid = False
        if user:
            stored = user['password_hash']
            try:
                # bcrypt hashes start with $2 (eg $2b$)
                if stored and stored.startswith("$2"):
                    valid = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
                else:
                    # legacy or incorrect value: compare plaintext
                    valid = (password == stored)
                    # optionally re-hash and update the database
                    if valid:
                        try:
                            conn2 = get_db_connection()
                            if conn2:
                                cur2 = conn2.cursor()
                                new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                cur2.execute("UPDATE user SET password_hash = %s WHERE id = %s", (new_hash, user['id']))
                                conn2.commit()
                                cur2.close()
                                conn2.close()
                        except Exception:
                            pass
            except Exception as e:
                print(f"Error checking password hash: {e}")
                valid = False

        if valid:
            session['username'] = username
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user_id': user['id'],
                'username': user['username'],
                'redirect': 'regipage.html'
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during login'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'Server is running'}), 200

@app.route('/api/current_user', methods=['GET'])
def current_user():
    """Get the current logged-in user"""
    if 'username' in session:
        return jsonify({'username': session['username']}), 200
    else:
        return jsonify({'username': None}), 401

@app.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user by creating a username and password.
    
    This function handles user registration requests. It validates the input,
    hashes the password for secure storage, and stores the user information
    in the database. Duplicate usernames are not allowed due to the UNIQUE
    constraint on the username field.
    
    Expects JSON payload:
    {
        "username": "string",  // Required, non-empty after stripping whitespace
        "password": "string"   // Required, non-empty
    }
    
    Returns:
    - 201: {"success": true, "message": "Registration successful"}
    - 400: {"success": false, "message": "Username and password are required"}
    - 409: {"success": false, "message": "Username already exists"}
    - 500: {"success": false, "message": "Database connection failed"} or
           {"success": false, "message": "An error occurred during registration"}
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Connect to database
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        try:
            # Insert new user
            query = "INSERT INTO user (username, password_hash) VALUES (%s, %s)"
            cursor.execute(query, (username, password_hash))
            connection.commit()
            
            cursor.close()
            connection.close()
            
            return jsonify({
                'success': True,
                'message': 'Registration successful'
            }), 201
        
        except mysql.connector.errors.IntegrityError:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Username already exists'}), 409
    
    except Exception as e:
        print(f"Error during registration: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during registration'}), 500

@app.route('/api/classes', methods=['GET'])
def route_get_classes():
    """Route handler for fetching classes"""
    return regiback.get_classes(get_db_connection)

@app.route('/api/exams', methods=['GET'])
def route_get_exams():
    """Route handler for fetching exams by class ID"""
    class_id = request.args.get('class_id')
    return regiback.get_exams_by_class(class_id, get_db_connection)

@app.route('/api/campuses', methods=['GET'])
def route_get_campuses():
    """Route handler for fetching campuses by class and exam"""
    class_id = request.args.get('class_id')
    exam_id = request.args.get('exam_id')
    return regiback.get_campuses_by_exam(class_id, exam_id, get_db_connection)

@app.route('/api/dates', methods=['GET'])
def route_get_dates():
    """Route handler for fetching dates by class, exam, and location"""
    class_id = request.args.get('class_id')
    exam_id = request.args.get('exam_id')
    location_id = request.args.get('location_id')
    return regiback.get_dates_by_campus(class_id, exam_id, location_id, get_db_connection)

@app.route('/api/times', methods=['GET'])
def route_get_times():
    """Route handler for fetching times by class, exam, location, and date"""
    class_id = request.args.get('class_id')
    exam_id = request.args.get('exam_id')
    location_id = request.args.get('location_id')
    schedule_id = request.args.get('schedule_id')
    return regiback.get_times_by_date(class_id, exam_id, location_id, schedule_id, get_db_connection)

@app.route('/regipage.html')
def regipage():
    """Serve the regipage.html"""
    return send_from_directory(os.path.dirname(__file__), 'regipage.html')

@app.route('/login.html')
def login_page():
    """Serve the login.html"""
    return send_from_directory(os.path.dirname(__file__), 'login.html')

@app.route('/user_registration.html')
def user_registration_page():
    """Serve the user_registration.html"""
    return send_from_directory(os.path.dirname(__file__), 'user_registration.html')

# Register regiback routes with Flask
app.add_url_rule('/api/logout', 'logout_from_regiback', regiback.logout, methods=['POST'])
app.add_url_rule('/api/schedule', 'schedule_exam', regiback.schedule_exam, methods=['POST'])
app.add_url_rule('/api/schedule', 'get_user_exams', regiback.get_user_exams, methods=['GET'])
app.add_url_rule('/api/schedule/<int:registration_id>', 'cancel_exam', regiback.cancel_exam, methods=['DELETE'])

if __name__ == '__main__':
    if init_database():
        app.run(debug=True, port=5000)
    else:
        print("Cannot start server. Database or table is missing.")
