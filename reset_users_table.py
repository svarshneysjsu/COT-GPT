import sqlite3

def reset_users_table():
    try:
        # Connect to existing chat_history.db
        conn = sqlite3.connect("chat_history.db")
        c = conn.cursor()

        # Drop old users table if it exists
        c.execute("DROP TABLE IF EXISTS users")
        conn.commit()

        print("✅ Old 'users' table dropped successfully.")

        # Recreate fresh users table with first_name, last_name, email, password
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password TEXT,
                first_name TEXT,
                last_name TEXT
            )
        """)
        conn.commit()

        print("✅ New 'users' table created successfully with correct structure.")

    except Exception as e:
        print(f"❗ Error resetting users table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_users_table()
