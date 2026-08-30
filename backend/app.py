import os
from datetime import datetime, timedelta, timezone

import jwt
import mysql.connector
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from books import books_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(books_bp)

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "smart_library"),
        user=os.getenv("DB_USER", "library_user"),
        password=os.getenv("DB_PASSWORD", "")
    )


@app.route("/")
def home():
    return jsonify({
        "service": "backend",
        "status": "UP"
    })


@app.route("/health")
def health():
    return jsonify({
        "service": "backend",
        "status": "UP"
    })


@app.route("/api/health")
def api_health():
    return jsonify({
        "service": "backend",
        "status": "UP"
    })


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Username and password are required"
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Password must be at least 6 characters"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM users WHERE username = %s",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({
                "success": False,
                "message": "Username already registered"
            }), 409

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
            """,
            (username, password_hash)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Account created successfully"
        }), 201

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "Database error",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Username and password are required"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username, password_hash
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "Invalid username or password"
            }), 401

        if not check_password_hash(
            user["password_hash"],
            password
        ):
            return jsonify({
                "success": False,
                "message": "Invalid username or password"
            }), 401

        payload = {
            "user_id": user["id"],
            "username": user["username"],
            "exp": datetime.now(timezone.utc)
            + timedelta(hours=JWT_EXPIRATION_HOURS)
        }

        token = jwt.encode(
            payload,
            JWT_SECRET,
            algorithm="HS256"
        )

        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "username": user["username"]
        })

    except mysql.connector.Error as error:
        return jsonify({
            "success": False,
            "message": "Database error",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()




# ============================================================
# BOOKS API
# ============================================================

@app.route("/api/books", methods=["GET"])
def get_books():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        category = request.args.get("category", "").strip()
        language = request.args.get("language", "").strip()
        search = request.args.get("q", "").strip()

        query = """
            SELECT
                id,
                title,
                author,
                category,
                language,
                isbn,
                quantity,
                available_quantity,
                description,
                created_at,
                updated_at
            FROM books
            WHERE 1=1
        """

        params = []

        if category:
            query += " AND category = %s"
            params.append(category)

        if language:
            query += " AND language = %s"
            params.append(language)

        if search:
            query += """
                AND (
                    title LIKE %s
                    OR author LIKE %s
                    OR category LIKE %s
                    OR language LIKE %s
                    OR isbn LIKE %s
                )
            """

            search_value = f"%{search}%"

            params.extend([
                search_value,
                search_value,
                search_value,
                search_value,
                search_value
            ])

        query += " ORDER BY id DESC"

        cursor.execute(query, tuple(params))
        books = cursor.fetchall()

        return jsonify({
            "success": True,
            "count": len(books),
            "books": books
        }), 200

    except mysql.connector.Error as error:
        return jsonify({
            "success": False,
            "message": "Database error",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                title,
                author,
                category,
                language,
                isbn,
                quantity,
                available_quantity,
                description,
                created_at,
                updated_at
            FROM books
            WHERE id = %s
            """,
            (book_id,)
        )

        book = cursor.fetchone()

        if not book:
            return jsonify({
                "success": False,
                "message": "Book not found"
            }), 404

        return jsonify({
            "success": True,
            "book": book
        }), 200

    except mysql.connector.Error as error:
        return jsonify({
            "success": False,
            "message": "Database error",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/books", methods=["POST"])
def add_book():
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    category = data.get("category", "").strip()
    language = data.get("language", "English").strip()
    isbn = data.get("isbn", "").strip()
    description = data.get("description", "").strip()

    if not title or not author:
        return jsonify({
            "success": False,
            "message": "Title and author are required"
        }), 400

    try:
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Quantity must be a valid number"
        }), 400

    if quantity < 1:
        return jsonify({
            "success": False,
            "message": "Quantity must be at least 1"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO books
            (
                title,
                author,
                category,
                language,
                isbn,
                quantity,
                available_quantity,
                description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                title,
                author,
                category or None,
                language or "English",
                isbn or None,
                quantity,
                quantity,
                description or None
            )
        )

        connection.commit()

        book_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "message": "Book added successfully",
            "book_id": book_id
        }), 201

    except mysql.connector.IntegrityError:
        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "ISBN already exists"
        }), 409

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "Database error",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    category = data.get("category", "").strip()
    language = data.get("language", "English").strip()
    isbn = data.get("isbn", "").strip()
    description = data.get("description", "").strip()

    if not title or not author:
        return jsonify({
            "success": False,
            "message": "Title and author are required"
        }), 400

    try:
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Quantity must be a valid number"
        }), 400

    if quantity < 1:
        return jsonify({
            "success": False,
            "message": "Quantity must be at least 1"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT quantity, available_quantity
            FROM books
            WHERE id = %s
            """,
            (book_id,)
        )

        existing_book = cursor.fetchone()

        if not existing_book:
            return jsonify({
                "success": False,
                "message": "Book not found"
            }), 404

        issued_quantity = (
            existing_book["quantity"]
            - existing_book["available_quantity"]
        )

        if quantity < issued_quantity:
            return jsonify({
                "success": False,
                "message": (
                    f"Quantity cannot be less than issued books "
                    f"({issued_quantity})"
                )
            }), 400

        available_quantity = quantity - issued_quantity

        cursor.execute(
            """
            UPDATE books
            SET
                title = %s,
                author = %s,
                category = %s,
                language = %s,
                isbn = %s,
                quantity = %s,
                available_quantity = %s,
                description = %s
            WHERE id = %s
            """,
            (
                title,
                author,
                category or None,
                language or "English",
                isbn or None,
                quantity,
                available_quantity,
                description or None,
                book_id
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Book updated successfully",
            "book_id": book_id
        }), 200

    except mysql.connector.IntegrityError:
        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "ISBN already exists"
        }), 409

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "Database error",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, title, quantity, available_quantity
            FROM books
            WHERE id = %s
            """,
            (book_id,)
        )

        book = cursor.fetchone()

        if not book:
            return jsonify({
                "success": False,
                "message": "Book not found"
            }), 404

        if book["quantity"] != book["available_quantity"]:
            return jsonify({
                "success": False,
                "message": "Cannot delete a book while copies are issued"
            }), 409

        cursor.execute(
            "DELETE FROM books WHERE id = %s",
            (book_id,)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Book deleted successfully"
        }), 200

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "Database error",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
