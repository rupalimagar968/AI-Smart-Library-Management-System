from werkzeug.security import generate_password_hash, check_password_hash


def create_users_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()


def create_user(conn, username, password):
    username = username.strip()

    if not username or not password:
        return False, "Username and password are required."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    password_hash = generate_password_hash(password)

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, password_hash)
        )
        conn.commit()
        cursor.close()
        return True, "Account created successfully."
    except Exception:
        conn.rollback()
        return False, "Username already exists."


def login_user(conn, username, password):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, username, password_hash FROM users WHERE username = %s",
        (username,)
    )
    user = cursor.fetchone()
    cursor.close()

    if user and check_password_hash(user["password_hash"], password):
        return True, {
            "id": user["id"],
            "username": user["username"]
        }

    return False, "Invalid username or password."
