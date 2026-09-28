import sqlite3
import os
from werkzeug.security import generate_password_hash


def init_db():
    os.makedirs("uploads/student_projects", exist_ok=True)
    os.makedirs("uploads/lecturer_projects", exist_ok=True)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Create the central projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author_name TEXT NOT NULL,
            author_type TEXT NOT NULL,
            matric_number TEXT,
            department TEXT NOT NULL,
            supervisor TEXT,
            academic_session TEXT NOT NULL,
            abstract TEXT NOT NULL,
            keywords TEXT NOT NULL,
            file_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create the users table for authentication
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Insert default test accounts if the table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("admin", generate_password_hash("admin123"), "ADMIN"),
            ("dr_adebayo", generate_password_hash("lecturer123"), "LECTURER"),
            ("2731", generate_password_hash("student123"), "STUDENT"),
        ]
        cursor.executemany(
            """
            INSERT INTO users (username, password_hash, role) 
            VALUES (?, ?, ?)
        """,
            default_users,
        )

    conn.commit()
    conn.close()
    print("Database, directories, and default users initialized successfully.")


if __name__ == "__main__":
    init_db()
