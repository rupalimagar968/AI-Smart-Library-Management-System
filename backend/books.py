import mysql.connector
from flask import Blueprint, jsonify, request

books_bp = Blueprint("books", __name__, url_prefix="/api/books")


def get_db_connection():
    import os

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "smart_library"),
        user=os.getenv("DB_USER", "library_user"),
        password=os.getenv("DB_PASSWORD", "")
    )


@books_bp.route("", methods=["POST"])
def add_book():
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    category = data.get("category", "").strip()
    isbn = data.get("isbn", "").strip() or None
    description = data.get("description", "").strip()

    quantity = data.get("quantity", 1)

    if not title or not author:
        return jsonify({
            "success": False,
            "message": "Title and author are required"
        }), 400

    try:
        quantity = int(quantity)

        if quantity < 1:
            return jsonify({
                "success": False,
                "message": "Quantity must be at least 1"
            }), 400

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Quantity must be a valid number"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            INSERT INTO books
            (title, author, category, isbn, quantity, available_quantity, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                title,
                author,
                category or None,
                isbn,
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


@books_bp.route("", methods=["GET"])
def get_books():
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
                isbn,
                quantity,
                available_quantity,
                description,
                created_at,
                updated_at
            FROM books
            ORDER BY id DESC
            """
        )

        books = cursor.fetchall()

        return jsonify({
            "success": True,
            "count": len(books),
            "books": books
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


@books_bp.route("/<int:book_id>", methods=["GET"])
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


@books_bp.route("/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    category = data.get("category", "").strip()
    isbn = data.get("isbn", "").strip() or None
    description = data.get("description", "").strip()

    quantity = data.get("quantity")

    if not title or not author:
        return jsonify({
            "success": False,
            "message": "Title and author are required"
        }), 400

    try:
        quantity = int(quantity)

        if quantity < 1:
            return jsonify({
                "success": False,
                "message": "Quantity must be at least 1"
            }), 400

    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Quantity must be a valid number"
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

        borrowed_quantity = (
            existing_book["quantity"]
            - existing_book["available_quantity"]
        )

        if quantity < borrowed_quantity:
            return jsonify({
                "success": False,
                "message": (
                    "Quantity cannot be less than the number "
                    "of currently issued books"
                )
            }), 400

        available_quantity = quantity - borrowed_quantity

        cursor.execute(
            """
            UPDATE books
            SET
                title = %s,
                author = %s,
                category = %s,
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
                isbn,
                quantity,
                available_quantity,
                description or None,
                book_id
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Book updated successfully"
        })

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


@books_bp.route("/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
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

        book = cursor.fetchone()

        if not book:
            return jsonify({
                "success": False,
                "message": "Book not found"
            }), 404

        if book["quantity"] != book["available_quantity"]:
            return jsonify({
                "success": False,
                "message": "Cannot delete a book that is currently issued"
            }), 409

        cursor.execute(
            "DELETE FROM books WHERE id = %s",
            (book_id,)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Book deleted successfully"
        })

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


@books_bp.route("/search", methods=["GET"])
def search_books():
    search = request.args.get("q", "").strip()

    if not search:
        return jsonify({
            "success": False,
            "message": "Search query is required"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        search_value = f"%{search}%"

        cursor.execute(
            """
            SELECT
                id,
                title,
                author,
                category,
                isbn,
                quantity,
                available_quantity,
                description,
                created_at,
                updated_at
            FROM books
            WHERE
                title LIKE %s
                OR author LIKE %s
                OR category LIKE %s
                OR isbn LIKE %s
            ORDER BY id DESC
            """,
            (
                search_value,
                search_value,
                search_value,
                search_value
            )
        )

        books = cursor.fetchall()

        return jsonify({
            "success": True,
            "count": len(books),
            "books": books
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

