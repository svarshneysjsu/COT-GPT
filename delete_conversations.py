import sqlite3

def delete_all_conversations():
    conn = sqlite3.connect("chat_history.db")  # Connect to your database
    c = conn.cursor()
    c.execute("DELETE FROM conversations")  # Delete all rows
    conn.commit()
    conn.close()
    print("All conversations deleted successfully.")

if __name__ == "__main__":
    delete_all_conversations()
