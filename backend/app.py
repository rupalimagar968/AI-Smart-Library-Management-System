import os
from datetime import datetime, timedelta, timezone

import jwt
import mysql.connector
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from books import books_bp
from admin import admin_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(books_bp)
app.register_blueprint(admin_bp)

JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "3"))


@app.before_request
def require_api_session():
    if not request.path.startswith("/api/") or request.method == "OPTIONS":
        return None

    public_paths = {
        "/api/login",
        "/api/register",
        "/api/forgot-password",
    }
    if request.path in public_paths:
        return None

    if current_user() is None:
        return jsonify({
            "success": False,
            "message": "Login required"
        }), 401

    return None


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

    name = str(data.get("name", data.get("username", ""))).strip()
    password = data.get("password", "")
    email = str(data.get("email", "")).strip()

    # Name and password are mandatory
    if not name or not password:
        return jsonify({
            "success": False,
            "message": "Name and password are required"
        }), 400

    if len(name) < 2:
        return jsonify({
            "success": False,
            "message": "Name must contain at least 2 characters"
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Password must be at least 6 characters"
        }), 400

    # Email is optional, but validate it when provided
    if email and ("@" not in email or "." not in email.split("@")[-1]):
        return jsonify({
            "success": False,
            "message": "Please enter a valid email address"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM users WHERE LOWER(name) = LOWER(%s) OR LOWER(username) = LOWER(%s)",
            (name, name)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({
                "success": False,
                "message": "An account with this name already exists"
            }), 409

        if email:
            cursor.execute(
                "SELECT id FROM users WHERE LOWER(email) = LOWER(%s)",
                (email,)
            )

            existing_email = cursor.fetchone()

            if existing_email:
                return jsonify({
                    "success": False,
                    "message": "This email is already registered"
                }), 409

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (username, name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (name, name, email if email else None, password_hash)
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
            "message": "Database error"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", data.get("username", ""))
    ).strip()

    password = data.get("password", "")

    if not name or not password:
        return jsonify({
            "success": False,
            "message": "Name and password are required"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username, name, email, password_hash
            FROM users
            WHERE LOWER(name) = LOWER(%s)
               OR LOWER(username) = LOWER(%s)
            LIMIT 1
            """,
            (name, name)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "Invalid name or password"
            }), 401

        if not check_password_hash(
            user["password_hash"],
            password
        ):
            return jsonify({
                "success": False,
                "message": "Invalid name or password"
            }), 401

        admin_username = os.getenv(
            "ADMIN_USERNAME",
            "admin"
        )

        is_admin = (
            user["username"].lower()
            == admin_username.lower()
        )

        payload = {
            "user_id": user["id"],
            "name": user["name"] or user["username"],
            "username": user["username"],
            "is_admin": is_admin,
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
            "name": user["name"] or user["username"],
            "username": user["username"],
            "email": user["email"],
            "is_admin": is_admin
        })

    except mysql.connector.Error:
        return jsonify({
            "success": False,
            "message": "Database error"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", data.get("username", ""))).strip()
    email = str(data.get("email", "")).strip()
    new_password = data.get("new_password", "")

    if not name or not email or not new_password:
        return jsonify({
            "success": False,
            "message": "Name, email and new password are required"
        }), 400

    if len(new_password) < 6:
        return jsonify({
            "success": False,
            "message": "New password must be at least 6 characters"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(name) = LOWER(%s)
              AND LOWER(email) = LOWER(%s)
            LIMIT 1
            """,
            (name, email)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "Name and email do not match our records"
            }), 404

        password_hash = generate_password_hash(new_password)

        cursor.execute(
            """
            UPDATE users
            SET password_hash = %s
            WHERE id = %s
            """,
            (password_hash, user["id"])
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Password reset successfully. You can now login."
        })

    except mysql.connector.Error:
        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "Database error"
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
    if current_user() is None:
        return jsonify({
            "success": False,
            "message": "Login required"
        }), 401

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
            search_terms = [term for term in search.split() if term]
            for term in search_terms:
                query += """
                    AND (
                        title LIKE %s
                        OR author LIKE %s
                        OR category LIKE %s
                        OR language LIKE %s
                        OR isbn LIKE %s
                    )
                """
                search_value = f"%{term}%"
                params.extend([search_value] * 5)

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


# ============================================================
# BORROWING API
# ============================================================

def current_user():
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    try:
        return jwt.decode(authorization.split(" ", 1)[1].strip(),
                          JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None


def ensure_loans_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            book_id INT NOT NULL,
            borrowed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            due_date DATE NOT NULL,
            duration_days INT NOT NULL,
            returned_at DATETIME NULL,
            INDEX idx_loans_user_active (user_id, returned_at),
            INDEX idx_loans_book_active (book_id, returned_at)
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


def ensure_payments_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fine_payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            loan_id INT NOT NULL,
            amount INT NOT NULL,
            reference VARCHAR(120) NOT NULL,
            payment_method VARCHAR(20) NOT NULL DEFAULT 'UPI',
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        SELECT COUNT(*) AS column_exists
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'fine_payments'
          AND column_name = 'payment_method'
    """)
    if cursor.fetchone()["column_exists"] == 0:
        cursor.execute(
            "ALTER TABLE fine_payments ADD COLUMN payment_method VARCHAR(20) NOT NULL DEFAULT 'UPI'"
        )


def loan_payload(row):
    overdue_days = max((datetime.now().date() - row["due_date"]).days, 0)
    # Fines start only after the ten-day maximum loan period.
    elapsed_overdue = max((datetime.now().date() -
                           row["borrowed_at"].date()).days - 10, 0)
    return {
        "id": row["id"], "loan_id": row["id"], "book_id": row["book_id"],
        "title": row.get("title"), "author": row.get("author"),
        "borrowed_at": row["borrowed_at"].isoformat(),
        "due_date": row["due_date"].isoformat(),
        "duration_days": row.get("duration_days"),
        "remaining_days": max((row["due_date"] - datetime.now().date()).days, 0),
        "returned_at": row["returned_at"].isoformat() if row.get("returned_at") else None,
        "overdue_days": overdue_days,
        "fine": elapsed_overdue * 50,
        "fine_inr": elapsed_overdue * 50
    }


@app.route("/api/borrow", methods=["POST"])
@app.route("/api/loans", methods=["POST"])
@app.route("/api/books/<int:book_id>/borrow", methods=["POST"])
def borrow_book():
    user = current_user()
    if not user:
        return jsonify(success=False, message="Authentication required"), 401
    data = request.get_json(silent=True) or {}
    try:
        book_id = int(data.get("book_id", request.view_args.get("book_id")))
        days = int(data.get("duration_days", data.get("borrow_days",
                                                        data.get("days", 7))))
    except (TypeError, ValueError):
        return jsonify(success=False, message="Book ID and duration are required"), 400
    if days < 2 or days > 10:
        return jsonify(success=False, message="Borrow duration must be between 2 and 10 days"), 400

    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        ensure_loans_table(cursor)
        connection.start_transaction()
        cursor.execute("SELECT id, available_quantity FROM books WHERE id=%s FOR UPDATE", (book_id,))
        book = cursor.fetchone()
        if not book:
            return jsonify(success=False, message="Book not found"), 404
        cursor.execute("SELECT COUNT(*) AS count FROM loans WHERE user_id=%s AND returned_at IS NULL",
                       (user["user_id"],))
        if cursor.fetchone()["count"] >= 4:
            connection.rollback()
            return jsonify(success=False, error="quota_completed",
                           code="QUOTA_COMPLETED",
                           message="Borrowing quota completed (maximum 4 active books)"), 409
        if book["available_quantity"] < 1:
            connection.rollback()
            return jsonify(success=False, message="Book is currently unavailable"), 409
        cursor.execute("""
            SELECT id FROM loans WHERE user_id=%s AND book_id=%s AND returned_at IS NULL
        """, (user["user_id"], book_id))
        if cursor.fetchone():
            connection.rollback()
            return jsonify(success=False, message="You already have this book"), 409
        cursor.execute("""
            INSERT INTO loans (user_id, book_id, borrowed_at, due_date, duration_days)
            VALUES (%s, %s, NOW(), DATE_ADD(CURDATE(), INTERVAL %s DAY), %s)
        """, (user["user_id"], book_id, days, days))
        loan_id = cursor.lastrowid
        cursor.execute("UPDATE books SET available_quantity=available_quantity-1 WHERE id=%s", (book_id,))
        connection.commit()
        return jsonify(success=True, message="Book borrowed successfully",
                       loan_id=loan_id, due_date=(datetime.now().date() +
                       timedelta(days=days)).isoformat()), 201
    except mysql.connector.Error as error:
        if connection: connection.rollback()
        return jsonify(success=False, message="Database error", error=str(error)), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route("/api/loans", methods=["GET"])
@app.route("/api/my-loans", methods=["GET"])
def get_loans():
    user = current_user()
    if not user:
        return jsonify(success=False, message="Authentication required"), 401
    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        ensure_loans_table(cursor)
        cursor.execute("""
            SELECT l.*, b.title, b.author FROM loans l
            JOIN books b ON b.id=l.book_id
            WHERE l.user_id=%s AND l.returned_at IS NULL ORDER BY l.due_date
        """, (user["user_id"],))
        rows = cursor.fetchall()
        cursor.execute(
            "SELECT loan_id FROM fine_payments WHERE user_id=%s AND status='PAID'",
            (user["user_id"],)
        )
        paid_loans = {row["loan_id"] for row in cursor.fetchall()}
        loans = []
        for row in rows:
            payload = loan_payload(row)
            if row["id"] in paid_loans:
                payload["fine"] = 0
                payload["fine_inr"] = 0
                payload["payment_cleared"] = True
            loans.append(payload)
        return jsonify(success=True, loans=loans,
                       active_count=len(rows), quota=4)
    except mysql.connector.Error as error:
        return jsonify(success=False, message="Database error", error=str(error)), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route("/api/return", methods=["POST"])
@app.route("/api/loans/<int:loan_id>/return", methods=["POST"])
def return_book(loan_id=None):
    user = current_user()
    if not user:
        return jsonify(success=False, message="Authentication required"), 401
    data = request.get_json(silent=True) or {}
    if loan_id is None:
        loan_id = data.get("loan_id")
    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        ensure_loans_table(cursor)
        connection.start_transaction()
        if loan_id:
            cursor.execute("SELECT * FROM loans WHERE id=%s AND user_id=%s AND returned_at IS NULL FOR UPDATE",
                           (int(loan_id), user["user_id"]))
        else:
            cursor.execute("SELECT * FROM loans WHERE book_id=%s AND user_id=%s AND returned_at IS NULL FOR UPDATE",
                           (int(data.get("book_id")), user["user_id"]))
        loan = cursor.fetchone()
        if not loan:
            connection.rollback()
            return jsonify(success=False, message="Active loan not found"), 404
        overdue_days = max((datetime.now().date() - loan["borrowed_at"].date()).days - 10, 0)
        fine = overdue_days * 50
        cursor.execute("UPDATE loans SET returned_at=NOW() WHERE id=%s", (loan["id"],))
        cursor.execute("UPDATE books SET available_quantity=available_quantity+1 WHERE id=%s", (loan["book_id"],))
        connection.commit()
        return jsonify(success=True, message="Book returned successfully",
                       fine=fine, fine_inr=fine, overdue_days=overdue_days)
    except (ValueError, TypeError, mysql.connector.Error) as error:
        if connection: connection.rollback()
        return jsonify(success=False, message="Database error", error=str(error)), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route("/api/fine-payments", methods=["POST"])
def submit_fine_payment():
    user = current_user()
    if not user:
        return jsonify(success=False, message="Authentication required"), 401
    data = request.get_json(silent=True) or {}
    try:
        loan_id = int(data.get("loan_id"))
        amount = int(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify(success=False, message="Loan and payment amount are required"), 400
    reference = str(data.get("reference", "")).strip()
    payment_method = str(data.get("payment_method", "UPI")).upper().strip()
    if payment_method not in ("UPI", "CASH"):
        return jsonify(success=False, message="Invalid payment method"), 400
    if payment_method == "CASH" and not reference:
        reference = "CASH"
    if not reference:
        reference = "ONLINE" if payment_method == "UPI" else "CASH"
    if amount < 1:
        return jsonify(success=False, message="Payment amount is required"), 400

    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        ensure_loans_table(cursor)
        ensure_payments_table(cursor)
        cursor.execute("""
            SELECT l.id, GREATEST(DATEDIFF(CURDATE(), l.borrowed_at) - 10, 0) * 50 AS fine
            FROM loans l
            WHERE l.id=%s AND l.user_id=%s AND l.returned_at IS NULL
        """, (loan_id, user["user_id"]))
        loan = cursor.fetchone()
        if not loan:
            return jsonify(success=False, message="Active loan not found"), 404
        if amount != loan["fine"] or amount < 1:
            return jsonify(success=False, message=f"Payment amount must be ₹{loan['fine']}"), 400
        cursor.execute("""
            SELECT id FROM fine_payments
            WHERE user_id=%s AND loan_id=%s AND status='PAID'
        """, (user["user_id"], loan_id))
        if cursor.fetchone():
            return jsonify(success=False, message="This fine is already cleared"), 409
        cursor.execute("""
            INSERT INTO fine_payments
                (user_id, loan_id, amount, reference, payment_method, status)
            VALUES (%s, %s, %s, %s, %s, 'PAID')
        """, (user["user_id"], loan_id, amount, reference, payment_method))
        payment_id = cursor.lastrowid
        cursor.execute(
            "UPDATE loans SET returned_at=NOW() WHERE id=%s AND returned_at IS NULL",
            (loan_id,)
        )
        cursor.execute(
            """
            UPDATE books b
            JOIN loans l ON l.book_id=b.id
            SET b.available_quantity=LEAST(b.quantity, b.available_quantity+1)
            WHERE l.id=%s
            """,
            (loan_id,)
        )
        connection.commit()
        return jsonify(success=True, message="Payment completed",
                       receipt_id=payment_id, status="PAID")
    except mysql.connector.Error as error:
        if connection:
            connection.rollback()
        return jsonify(success=False, message="Database error", error=str(error)), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route("/api/fine-payments/<int:payment_id>/receipt", methods=["GET"])
def download_payment_receipt(payment_id):
    user = current_user()
    if not user:
        return jsonify(success=False, message="Authentication required"), 401
    connection = cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id, p.amount, p.payment_method, p.status, p.created_at,
                   l.due_date, b.title, u.name
            FROM fine_payments p
            JOIN loans l ON l.id=p.loan_id
            JOIN books b ON b.id=l.book_id
            JOIN users u ON u.id=p.user_id
            WHERE p.id=%s AND p.user_id=%s AND p.status='PAID'
        """, (payment_id, user["user_id"]))
        receipt = cursor.fetchone()
        if not receipt:
            return jsonify(success=False, message="Receipt not found"), 404
        lines = [
            "SMART DIGITAL LIBRARY",
            "PAYMENT RECEIPT",
            "",
            f"Receipt No: {receipt['id']}",
            f"Member: {receipt['name']}",
            f"Book: {receipt['title']}",
            f"Amount Paid: INR {receipt['amount']}",
            f"Payment Mode: {receipt['payment_method']}",
            f"Payment Date: {receipt['created_at']}",
            f"Due Date: {receipt['due_date']}",
            "Status: PAID / FINE CLEARED",
        ]
        pdf_lines = []
        y = 760
        for line in lines:
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            pdf_lines.append(f"BT /F1 12 Tf 72 {y} Td ({safe}) Tj ET")
            y -= 28
        stream = "\n".join(pdf_lines).encode("latin-1", "replace")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        pdf = b"%PDF-1.4\n"
        offsets = [0]
        for index, obj in enumerate(objects, 1):
            offsets.append(len(pdf))
            pdf += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
        xref = len(pdf)
        pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
        pdf += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
        pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
        from flask import Response
        return Response(pdf, mimetype="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=library-receipt-{payment_id}.pdf"
        })
    except mysql.connector.Error as error:
        return jsonify(success=False, message="Database error", error=str(error)), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
