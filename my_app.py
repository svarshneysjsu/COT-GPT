import streamlit as st
import sqlite3
import uuid
from gradio_client import Client

# Initialize Database
def initialize_database():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    # Conversations table
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT
        )
    """)
    # Users table with first_name and last_name
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            first_name TEXT,
            last_name TEXT
        )
    """)
    # Conversation Titles table
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversation_titles (
            session_id TEXT PRIMARY KEY,
            title TEXT
        )
    """)
    conn.commit()
    conn.close()

# Save a new user
def save_user(email, password, first_name, last_name):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password, first_name, last_name) VALUES (?, ?, ?, ?)",
                  (email, password, first_name, last_name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# Authenticate user
def authenticate_user(email, password):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    conn.close()
    return user is not None

# Get First Name for Welcome
def get_user_first_name(email):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT first_name FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return ""

# Save conversation title
def save_conversation_title(session_id, title):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO conversation_titles (session_id, title) VALUES (?, ?)", (session_id, title))
    conn.commit()
    conn.close()

# Get all conversations (session_id + title)
def get_conversations():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT session_id, title FROM conversation_titles")
    sessions = c.fetchall()
    conn.close()
    return sessions

# Save message
def save_message(session_id, role, content):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
    conn.commit()
    conn.close()

# Fetch conversation history
def get_conversation_history(session_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT role, content FROM conversations WHERE session_id = ?", (session_id,))
    history = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in history]

# Initialize Streamlit session state
def initialize_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "user_first_name" not in st.session_state:
        st.session_state.user_first_name = ""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Persistent Login Check
    params = st.query_params
    if not st.session_state.logged_in and "user_email" in params:
        email = params["user_email"]
        st.session_state.logged_in = True
        st.session_state.user_email = email
        st.session_state.user_first_name = get_user_first_name(email)

# Login or Signup Page
def login_page():
    st.title("🔐 Login or Signup")

    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if authenticate_user(email, password):
                st.success("Logged in successfully!")
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.user_first_name = get_user_first_name(email)
                st.query_params.update({"user_email": email})
                st.rerun()
            else:
                st.error("Invalid email or password!")

    with tab2:
        st.subheader("Signup")
        first_name = st.text_input("First Name", key="signup_first_name")
        last_name = st.text_input("Last Name", key="signup_last_name")
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Signup"):
            if save_user(new_email, new_password, first_name, last_name):
                st.success("Signup successful! Please log in now.")
            else:
                st.error("User already exists. Please log in.")

# Chat Interface
def chat_interface():

    # Sidebar
    with st.sidebar:
        MODEL_OPTIONS = [
        "Llama-3.2-1B-DPO",
        "gemma-3-1b-it-DPO",
        "phi-2-DPO",
        "Llama-3.2-1B-DPO-DPO-GRPO"
        ]

        # Set default model in session state
        if "model_name" not in st.session_state:
            st.session_state.model_name = "Llama-3.2-1B-DPO"

        selected_model = st.selectbox(
            "Select Model",
            MODEL_OPTIONS,
            index=MODEL_OPTIONS.index(st.session_state.model_name)
        )
        # Update state only if changed
        if selected_model != st.session_state.model_name:
            st.session_state.model_name = selected_model

        st.title(f"👋 Welcome, {st.session_state.user_first_name}!")

        conversations = get_conversations()
        if conversations:
            options = [f"{title} ({sid[:8]}...)" for sid, title in conversations]
            selected = st.selectbox("Load Conversation", options)
            if st.button("Load Chat"):
                selected_sid = conversations[options.index(selected)][0]
                st.session_state.session_id = selected_sid
                st.session_state.messages = get_conversation_history(selected_sid)

        if st.button("➕ New Chat"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []

    # Main Chat
    st.title("COT-Reasoning GPT")
    user_input = st.text_input("Ask your question:", key="user_input")

    if st.button("Send") and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message(st.session_state.session_id, "user", user_input)

        # Save title if it's the first message
        if len(st.session_state.messages) == 1:
            title = f"Topic: {user_input.strip()}"
            if len(title) > 50:
                title = title[:47] + "..."
            save_conversation_title(st.session_state.session_id, title)

        client = Client("Eshita-ds/cot-llm-298", hf_token="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")
        try:
            with st.spinner("Thinking..."):
                result = client.predict(
                    user_input=user_input,
                    history=[],
                    session_id=None,
                    model_name=st.session_state.model_name,
                    api_name="/chatbot_response",
                )
                if result and isinstance(result, (list, tuple)) and len(result) >= 1:
                    if isinstance(result[0], (list, tuple)) and len(result[0]) > 0 and isinstance(result[0][-1], (list, tuple)):
                        response = result[0][-1][1]
                    else:
                        response = "⚠️ Bot did not return a valid message."
                else:
                    response = "⚠️ Empty response from backend."
        except Exception as e:
            response = f"❗ Error communicating with model: {e}"

        st.session_state.messages.append({"role": "bot", "content": response})
        save_message(st.session_state.session_id, "bot", response)
        # st.session_state.user_input = ""
        st.rerun()

    # Display chat history
    st.write("---")
    # Group messages into (user, bot) pairs
    paired_messages = []
    messages = st.session_state.messages

    i = 0
    while i < len(messages) - 1:
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "bot":
            paired_messages.append((messages[i], messages[i + 1]))
            i += 2
        else:
            i += 1  # Skip unmatched (shouldn't happen, just in case)

    # Reverse pairs to show newest first
    for user_msg, bot_msg in reversed(paired_messages):
        st.markdown(f"**🧑 Your Question:** {user_msg['content']}")
        st.markdown(f"**🤖 Response:** {bot_msg['content']}")

# Main App
def main():
    st.set_page_config(page_title="COT-Reasoning GPT", page_icon="🤖")
    initialize_database()
    initialize_session()

    if not st.session_state.logged_in:
        login_page()
    else:
        chat_interface()

if __name__ == "__main__":
    main()
