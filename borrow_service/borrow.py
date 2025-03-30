from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flasgger import Swagger
import mysql.connector
from config.db_config import DB_CONFIG

app_borrow = Flask(__name__)
app_borrow.config['JWT_SECRET_KEY'] = 'supersecret'
jwt = JWTManager(app_borrow)

swagger_config = {
    "swagger": "2.0",
    "info": {
        "title": "Library API - Borrow Service",
        "description": "API for borrowing books in the library system",
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
    "security": [{"Bearer": []}],
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
    "headers": []  # ✅ Ensure this is an empty list
}

Swagger(app_borrow, config=swagger_config)

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


@app_borrow.route('/borrow/<int:book_id>/<int:user_id>', methods=['POST'])
@jwt_required()
def borrow_book(book_id,user_id):
    """
    Borrow a book
    ---
    tags:
      - Borrowing
    security:
      - Bearer: []
    parameters:
      - name: book_id
        in: path
        type: integer
        required: true
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Book borrowed successfully
      400:
        description: Book not available or already borrowed
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT qty FROM books WHERE id=%s", (book_id,))
    book = cursor.fetchone()

    if not book or book['qty'] < 1:
        return jsonify({'message': 'Book not available'}), 400

    cursor.execute(
        "SELECT status FROM borrow_history WHERE user_id=%s AND book_id=%s AND status='borrowed'",
        (user_id, book_id)
    )
    existing_borrow = cursor.fetchone()

    if existing_borrow:
        return jsonify({'message': 'You have already borrowed this book. Please return it first.'}), 400

    cursor.execute("UPDATE books SET qty = qty - 1 WHERE id=%s AND qty > 0", (book_id,))
    cursor.execute("INSERT INTO borrow_history (user_id, book_id, status) VALUES (%s, %s, 'borrowed')",
                   (user_id, book_id))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({'message': 'Book borrowed successfully'}), 200


if __name__ == '__main__':
    app_borrow.run(port=5003, debug=True)
