import os
from functools import wraps

import jwt
import mysql.connector
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "smart_library"),
        user=os.getenv("DB_USER", "library_user"),
        password=os.getenv("DB_PASSWORD", "")
    )


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        authorization = request.headers.get("Authorization", "")

        if not authorization.startswith("Bearer "):
            return jsonify({
                "success": False,
                "message": "Admin authentication required"
            }), 401

        token = authorization.split(" ", 1)[1].strip()

        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"]
            )

            username = payload.get("username", "")

            if username.lower() != ADMIN_USERNAME.lower():
                return jsonify({
                    "success": False,
                    "message": "Admin access required"
                }), 403

            request.admin_username = username

        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Admin session expired"
            }), 401

        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid authentication token"
            }), 401

        return function(*args, **kwargs)

    return wrapper


def log_activity(cursor, action, details):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_activity (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_username VARCHAR(100) NOT NULL,
            action VARCHAR(100) NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        INSERT INTO admin_activity
        (admin_username, action, details)
        VALUES (%s, %s, %s)
        """,
        (
            getattr(request, "admin_username", ADMIN_USERNAME),
            action,
            details
        )
    )


# ============================================================
# DASHBOARD
# ============================================================

@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total_users FROM users")
        users = cursor.fetchone()["total_users"]

        cursor.execute("SELECT COUNT(*) AS total_books FROM books")
        books = cursor.fetchone()["total_books"]

        cursor.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS total_copies FROM books"
        )
        total_copies = cursor.fetchone()["total_copies"]

        cursor.execute(
            """
            SELECT COALESCE(SUM(available_quantity), 0)
            AS available_copies
            FROM books
            """
        )
        available_copies = cursor.fetchone()["available_copies"]

        cursor.execute(
            """
            SELECT COUNT(*) AS unavailable_titles
            FROM books
            WHERE available_quantity = 0
            """
        )
        unavailable_titles = cursor.fetchone()["unavailable_titles"]

        cursor.execute(
            """
            SELECT
                id,
                username,
                name,
                email,
                created_at
            FROM users
            ORDER BY id DESC
            """
        )
        recent_users = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                id,
                title,
                author,
                category,
                quantity,
                available_quantity,
                created_at,
                updated_at
            FROM books
            ORDER BY updated_at DESC, id DESC
            """
        )
        recent_books = cursor.fetchall()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_activity (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_username VARCHAR(100) NOT NULL,
                action VARCHAR(100) NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            SELECT
                id,
                admin_username,
                action,
                details,
                created_at
            FROM admin_activity
            ORDER BY id DESC
            """
        )
        activities = cursor.fetchall()

        return jsonify({
            "success": True,
            "stats": {
                "users": users,
                "books": books,
                "total_copies": total_copies,
                "available_copies": available_copies,
                "unavailable_titles": unavailable_titles
            },
            "recent_users": recent_users,
            "recent_books": recent_books,
            "activities": activities
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
# USERS
# ============================================================

@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        search = request.args.get("q", "").strip()

        query = """
            SELECT
                id,
                username,
                name,
                email,
                created_at
            FROM users
        """

        params = []

        if search:
            query += """
                WHERE
                    username LIKE %s
                    OR name LIKE %s
                    OR email LIKE %s
            """

            value = f"%{search}%"
            params = [value, value, value]

        query += " ORDER BY id DESC"

        cursor.execute(query, tuple(params))

        users = cursor.fetchall()

        return jsonify({
            "success": True,
            "count": len(users),
            "users": users
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


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_user_password(user_id):
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not isinstance(password, str) or len(password) < 6:
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
            "SELECT id, username FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (generate_password_hash(password), user_id)
        )
        log_activity(
            cursor,
            "PASSWORD_RESET",
            f"Reset password for user: {user['username']}"
        )
        connection.commit()

        return jsonify({
            "success": True,
            "message": "Password reset successfully"
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


@admin_bp.route("/loans", methods=["GET"])
@admin_required
def get_admin_loans():
    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                book_id INT NOT NULL,
                borrowed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                due_date DATE NOT NULL,
                duration_days INT NOT NULL DEFAULT 7,
                returned_at DATETIME NULL
            )
        """)
        cursor.execute("""
            SELECT COUNT(*) AS column_exists
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'loans'
              AND column_name = 'duration_days'
        """)
        if cursor.fetchone()["column_exists"] == 0:
            cursor.execute(
                "ALTER TABLE loans ADD COLUMN duration_days INT NOT NULL DEFAULT 7"
            )
        cursor.execute("""
            SELECT l.id, l.borrowed_at, l.due_date, l.duration_days, l.returned_at,
                   u.username, u.name, b.title,
                   GREATEST(DATEDIFF(CURDATE(), l.due_date), 0) AS overdue_days,
                   GREATEST(DATEDIFF(CURDATE(), l.borrowed_at) - 10, 0) * 50 AS fine_inr,
                   GREATEST(DATEDIFF(l.due_date, CURDATE()), 0) AS remaining_days
            FROM loans l
            JOIN users u ON u.id = l.user_id
            JOIN books b ON b.id = l.book_id
            ORDER BY l.returned_at IS NULL DESC, l.due_date ASC, l.id DESC
        """)
        loans = cursor.fetchall()
        for loan in loans:
            for key in ("borrowed_at", "due_date", "returned_at"):
                if loan.get(key):
                    loan[key] = loan[key].isoformat()
        return jsonify(success=True, loans=loans, count=len(loans))
    except mysql.connector.Error as error:
        return jsonify(success=False, message="Database error", error=str(error)), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@admin_bp.route("/fine-payments", methods=["GET"])
@admin_required
def get_fine_payments():
    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id, p.loan_id, p.amount, p.reference, p.status, p.created_at,
                   u.username, b.title
            FROM fine_payments p
            JOIN users u ON u.id = p.user_id
            JOIN loans l ON l.id = p.loan_id
            JOIN books b ON b.id = l.book_id
            ORDER BY p.id DESC
        """)
        payments = cursor.fetchall()
        for payment in payments:
            payment["created_at"] = payment["created_at"].isoformat()
        return jsonify(success=True, payments=payments, count=len(payments))
    except mysql.connector.Error as error:
        return jsonify(success=False, message="Database error", error=str(error)), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username, name, email
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        if user["username"].lower() == ADMIN_USERNAME.lower():
            return jsonify({
                "success": False,
                "message": "The admin account cannot be deleted"
            }), 403

        cursor.execute(
            "DELETE FROM users WHERE id = %s",
            (user_id,)
        )

        log_activity(
            cursor,
            "USER_DELETED",
            f"Deleted user: {user['username']}"
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "User deleted successfully"
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


# ============================================================
# BOOKS
# ============================================================

@admin_bp.route("/books", methods=["GET"])
@admin_required
def get_admin_books():

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

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
        """

        params = []

        if search:
            query += """
                WHERE
                    title LIKE %s
                    OR author LIKE %s
                    OR category LIKE %s
                    OR isbn LIKE %s
            """

            value = f"%{search}%"
            params = [value, value, value, value]

        query += " ORDER BY id DESC"

        cursor.execute(query, tuple(params))

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


@admin_bp.route("/books", methods=["POST"])
@admin_required
def create_book():

    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    category = data.get("category", "").strip()
    language = data.get("language", "English").strip()
    isbn = data.get("isbn", "").strip() or None
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
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                title,
                author,
                category or None,
                language or "English",
                isbn,
                quantity,
                quantity,
                description or None
            )
        )

        log_activity(
            cursor,
            "BOOK_CREATED",
            f"Added book: {title}"
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Book added successfully",
            "book_id": cursor.lastrowid
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


@admin_bp.route("/books/<int:book_id>", methods=["PUT"])
@admin_required
def edit_book(book_id):

    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    category = data.get("category", "").strip()
    language = data.get("language", "English").strip()
    isbn = data.get("isbn", "").strip() or None
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

        existing = cursor.fetchone()

        if not existing:
            return jsonify({
                "success": False,
                "message": "Book not found"
            }), 404

        issued = (
            existing["quantity"]
            - existing["available_quantity"]
        )

        if quantity < issued:
            return jsonify({
                "success": False,
                "message": f"Quantity cannot be less than issued copies ({issued})"
            }), 400

        available = quantity - issued

        cursor.execute(
            """
            UPDATE books
            SET
                title=%s,
                author=%s,
                category=%s,
                language=%s,
                isbn=%s,
                quantity=%s,
                available_quantity=%s,
                description=%s
            WHERE id=%s
            """,
            (
                title,
                author,
                category or None,
                language or "English",
                isbn,
                quantity,
                available,
                description or None,
                book_id
            )
        )

        log_activity(
            cursor,
            "BOOK_UPDATED",
            f"Updated book #{book_id}: {title}"
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


@admin_bp.route("/books/<int:book_id>", methods=["DELETE"])
@admin_required
def remove_book(book_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT title, quantity, available_quantity
            FROM books
            WHERE id=%s
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
            "DELETE FROM books WHERE id=%s",
            (book_id,)
        )

        log_activity(
            cursor,
            "BOOK_DELETED",
            f"Deleted book #{book_id}: {book['title']}"
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
