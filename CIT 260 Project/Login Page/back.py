from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import bcrypt

app = Flask(__name__)
CORS(app)

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
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user_id': user['id'],
                'username': user['username']
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

@app.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user
    Expects JSON: {"username": "user", "email": "email@example.com", "password": "pass"}
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not username or not email or not password:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Connect to database
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        try:
            # Insert new user
            query = "INSERT INTO user (username, email, password_hash) VALUES (%s, %s, %s)"
            cursor.execute(query, (username, email, password_hash))
            connection.commit()
            
            cursor.close()
            connection.close()
            
            return jsonify({
                'success': True,
                'message': 'User registered successfully'
            }), 201
        
        except mysql.connector.errors.IntegrityError:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Username or email already exists'}), 409
    
    except Exception as e:
        print(f"Error during registration: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during registration'}), 500

if __name__ == '__main__':
    if init_database():
        app.run(debug=True, port=5000)
    else:
        print("Cannot start server. Database or table is missing.")