from flask import jsonify

def logout():
    """Clear user session and logout"""
    # Simply return success - the client will clear its credentials
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200