from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token
from flasgger import Swagger
import mysql.connector
from config.db_config import DB_CONFIG

app_auth = Flask(__name__)
app_auth.config['JWT_SECRET_KEY'] = 'supersecret'
jwt = JWTManager(app_auth)

swagger_config = {
    "swagger": "2.0",
    "info": {
        "title": "Library API - Authentication",
        "description": "API for user authentication",
        "version": "1.0"
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer {token}'"
        }
    },
    "security": [
        {
            "Bearer": []
        }
    ],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "headers": []
}

Swagger(app_auth, config=swagger_config)

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

@app_auth.route('/login', methods=['POST'])
def login():
    """
    User Login
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        description: User login credentials
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              example: "admin"
            password:
              type: string
              example: "admin123"
    responses:
      200:
        description: Successfully authenticated
        schema:
          type: object
          properties:
            access_token:
              type: string
              example: "your_jwt_token"
      400:
        description: Bad request (Invalid JSON)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Invalid request. Expected JSON format"
      401:
        description: Invalid credentials
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Invalid credentials"
    """
    if not request.is_json:
        return jsonify({"message": "Invalid request. Expected JSON format"}), 400

    data = request.get_json()

    if "username" not in data or "password" not in data:
        return jsonify({"message": "Missing username or password"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (data['username'], data['password']))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        token = create_access_token(identity={'username': user['username'], 'role': user['role_id']})
        return jsonify(access_token=token)

    return jsonify({'message': 'Invalid credentials'}), 401

if __name__ == '__main__':
    app_auth.run(port=5001, debug=True)
