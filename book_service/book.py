from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flasgger import Swagger
import mysql.connector
from config.db_config import DB_CONFIG

app_books = Flask(__name__)
app_books.config['JWT_SECRET_KEY'] = 'supersecret'
jwt = JWTManager(app_books)

swagger_config = {
    "swagger": "2.0",
    "info": {
        "title": "Library API - Book Service",
        "description": "API for managing books in the library system",
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
    "headers": []
}

Swagger(app_books, config=swagger_config)


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


@app_books.route('/books', methods=['POST'])
@jwt_required()
def add_book():
    """
    Add a new book (Librarian Only)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - title
            - author
            - qty
            - publish_date
          properties:
            title:
              type: string
            author:
              type: string
            qty:
              type: integer
            publish_date:
              type: string
              format: date
              example: "2024-01-15"
    responses:
      201:
        description: Book added successfully
      403:
        description: Only librarians can add books
    """
    identity = get_jwt_identity()
    if identity['role_id'] != '1':
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO books (title, author, qty, publish_date, available, is_deleted) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (data['title'], data['author'], data['qty'], data['publish_date'], True, False))

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Book added successfully'}), 201


@app_books.route('/books', methods=['GET'])
@jwt_required()
def get_all_books():
    """
    Get all books (excluding deleted books)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    responses:
      200:
        description: List of all books
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM books WHERE is_deleted = 0")
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(books)


@app_books.route('/books/<int:book_id>', methods=['PUT'])
@jwt_required()
def update_book(book_id):
    """
    Update book details (Librarian Only)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    parameters:
      - in: path
        name: book_id
        required: true
        type: integer
      - in: body
        name: body
        schema:
          type: object
          properties:
            title:
              type: string
            author:
              type: string
            qty:
              type: integer
            publish_date:
              type: string
              format: date
              example: "2024-01-15"
    responses:
      200:
        description: Book updated successfully
      403:
        description: Only librarians can update books
      404:
        description: Book not found
    """
    identity = get_jwt_identity()
    if identity['role_id'] != '1':
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books WHERE id=%s AND is_deleted=0", (book_id,))
    if not cursor.fetchone():
        return jsonify({'message': 'Book not found'}), 404

    update_fields = []
    update_values = []
    if 'title' in data:
        update_fields.append("title=%s")
        update_values.append(data['title'])
    if 'author' in data:
        update_fields.append("author=%s")
        update_values.append(data['author'])
    if 'qty' in data:
        update_fields.append("qty=%s")
        update_values.append(data['qty'])
    if 'publish_date' in data:
        update_fields.append("publish_date=%s")
        update_values.append(data['publish_date'])

    update_values.append(book_id)
    query = f"UPDATE books SET {', '.join(update_fields)} WHERE id=%s"
    cursor.execute(query, tuple(update_values))

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Book updated successfully'})



@app_books.route('/books/<int:book_id>', methods=['DELETE'])
@jwt_required()
def delete_book(book_id):
    """
    Soft delete a book (Librarian Only)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    parameters:
      - in: path
        name: book_id
        required: true
        type: integer
    responses:
      200:
        description: Book deleted successfully
      403:
        description: Only librarians can delete books
      404:
        description: Book not found
    """
    identity = get_jwt_identity()
    if identity['role_id'] != '1':
        return jsonify({'message': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id=%s AND is_deleted=0", (book_id,))
    if not cursor.fetchone():
        return jsonify({'message': 'Book not found'}), 404

    cursor.execute("UPDATE books SET is_deleted = 1 WHERE id=%s", (book_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Book deleted successfully'})

@app_books.route('/books/search', methods=['GET'])
@jwt_required()
def search_books():
    """
    Search books by title or author
    ---
    tags:
      - Books
    security:
      - Bearer: []
    parameters:
      - in: query
        name: title
        type: string
        required: false
        description: Search books by title (partial match)
      - in: query
        name: author
        type: string
        required: false
        description: Search books by author (partial match)
    responses:
      200:
        description: List of matching books
    """
    title = request.args.get('title', '')
    author = request.args.get('author', '')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT id , title , author , available FROM books WHERE is_deleted = 0"
    params = []

    if title:
        query += " AND title LIKE %s"
        params.append(f"%{title}%")
    if author:
        query += " AND author LIKE %s"
        params.append(f"%{author}%")

    cursor.execute(query, tuple(params))
    books = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(books)

if __name__ == '__main__':
    app_books.run(port=5002, debug=True)
