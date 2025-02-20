import streamlit as st
import sqlite3
import uuid

def initialize_database():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_message(session_id, role, content):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
    conn.commit()
    conn.close()

def get_conversation_history(session_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT role, content FROM conversations WHERE session_id = ?", (session_id,))
    history = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in history]  # Convert tuples to dictionaries

def get_conversation_count():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT session_id) FROM conversations")
    count = c.fetchone()[0]
    conn.close()
    return count

def initialize_session():
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())  # Generate a unique session ID
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

def display_sidebar():
    st.sidebar.title("Conversation History")
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT session_id FROM conversations")
    sessions = c.fetchall()
    conn.close()

    if "selected_conversation" not in st.session_state:
        st.session_state["selected_conversation"] = None  # Track active conversation

    if sessions:
        for i, session in enumerate(sessions, start=1):
            session_id = session[0]  # Extract session_id from tuple
            is_selected = session_id == st.session_state["selected_conversation"]

            # Highlight selected conversation with a different style
            button_style = "border: 2px solid blue; font-weight: bold;" if is_selected else ""

            if st.sidebar.button(f"Conversation {i}", key=f"conv_{i}", help="Click to view chat history"):
                st.session_state["session_id"] = session_id
                st.session_state["messages"] = get_conversation_history(session_id)
                st.session_state["selected_conversation"] = session_id  # Store selected session


def chat_interface():
    col1, col2 = st.columns([8, 2])
    with col1:
        st.title("COT-Reasoning GPT")
    with col2:
        if st.button("Start New Chat"):
            st.session_state["session_id"] = str(uuid.uuid4())  # Generate a new session ID
            st.session_state["messages"] = []
            st.session_state["user_input"] = ""  # Reset input state

    # Use a temporary key to clear input safely
    user_input = st.text_input("Ask a question:", key="temp_input", value=st.session_state.get("user_input", ""))

    if st.button("Send") and user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        save_message(st.session_state["session_id"], "user", user_input)

        # Placeholder response (Replace this with actual model inference)
        response = "<Here will be the response from trained model>"
        st.session_state["messages"].append({"role": "bot", "content": response})
        save_message(st.session_state["session_id"], "bot", response)

        # Clear input box after sending a message
        st.session_state["user_input"] = ""  # Safe way to reset input without error

        # Force rerun to refresh UI
        st.rerun()

    # Display chat history
    for message in st.session_state["messages"]:
        if isinstance(message, dict) and "role" in message and "content" in message:
            if message["role"] == "user":
                st.markdown(f"**You:** {message['content']}")
            else:
                st.markdown(f"**Response:** {message['content']}")


def main():
    initialize_database()
    initialize_session()
    display_sidebar()
    chat_interface()

if __name__ == "__main__":
    main()
