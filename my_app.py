import streamlit as st
import sqlite3
import uuid
from datetime import datetime
import time
from gradio_client import Client
import os

# -------------------- DATABASE SETUP --------------------

def initialize_database():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            first_name TEXT,
            last_name TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversation_titles (
            session_id TEXT PRIMARY KEY,
            title TEXT
        )
    """)
    conn.commit()
    conn.close()

# -------------------- USER FUNCTIONS --------------------

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

def authenticate_user(email, password):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    conn.close()
    return user is not None

def get_user_first_name(email):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT first_name FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else ""

# -------------------- CHAT FUNCTIONS --------------------

def save_message(session_id, role, content):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
              (session_id, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_conversation_history(session_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT role, content, timestamp FROM conversations WHERE session_id = ?", (session_id,))
    history = c.fetchall()
    conn.close()
    return [{"role": r, "content": c, "timestamp": t} for r, c, t in history]

def save_conversation_title(session_id, title):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO conversation_titles (session_id, title) VALUES (?, ?)", (session_id, title))
    conn.commit()
    conn.close()

def get_conversations():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT session_id, title FROM conversation_titles")
    sessions = c.fetchall()
    conn.close()
    return sessions

# -------------------- SESSION STATE --------------------

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
    if "pending_input" not in st.session_state:
        st.session_state.pending_input = ""
    if "send_triggered" not in st.session_state:
        st.session_state.send_triggered = False
    if "model_name" not in st.session_state:
        st.session_state.model_name = "Llama-3.2-1B-DPO"

    # Persistent login check
    params = st.query_params
    if not st.session_state.logged_in and "user_email" in params:
        email = params["user_email"]
        st.session_state.logged_in = True
        st.session_state.user_email = email
        st.session_state.user_first_name = get_user_first_name(email)

# -------------------- UI COMPONENTS --------------------

def login_page():
    st.title("🔐 Login or Signup")
    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if authenticate_user(email, password):
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.user_first_name = get_user_first_name(email)
                st.query_params.update({"user_email": email})
                st.rerun()
            else:
                st.error("Invalid email or password")

    with tab2:
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        new_email = st.text_input("Email")
        new_password = st.text_input("Password", type="password")
        if st.button("Signup"):
            if save_user(new_email, new_password, first_name, last_name):
                st.success("Signup successful! Please log in.")
            else:
                st.error("User already exists.")

def chat_interface():
    MODEL_OPTIONS = [
        "Llama-3.2-1B-DPO",
        "gemma-3-1b-it-DPO",
        "phi-2-DPO",
        "Llama-3.2-1B-DPO-DPO-GRPO"
    ]

    with st.sidebar:
        st.title(f"👋 Welcome, {st.session_state.user_first_name}!")
        st.selectbox("Select Model", MODEL_OPTIONS,
                     index=MODEL_OPTIONS.index(st.session_state.model_name),
                     key="model_name")

        show_timestamps = st.checkbox("🕒 Show timestamps", value=False)

        conversations = get_conversations()
        if conversations:
            display_options = [f"{title} ({sid[:8]}...)" for sid, title in conversations]
            selected_display = st.selectbox("Load Conversation", display_options)
            if st.button("Load Chat"):
                selected_sid = conversations[display_options.index(selected_display)][0]
                st.session_state.session_id = selected_sid
                st.session_state.messages = get_conversation_history(selected_sid)

        if st.button("➕ New Chat"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []

    st.title("COT-Reasoning GPT")
    st.markdown("<hr style='margin-top:-10px;'>", unsafe_allow_html=True)

    user_input = st.chat_input("Ask your question:")
    if user_input:
        st.session_state.pending_input = user_input
        st.session_state.send_triggered = True

    if st.session_state.send_triggered:
        user_input = st.session_state.pending_input
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_message(st.session_state.session_id, "user", user_input)

        if len(st.session_state.messages) == 1:
            title = f"Topic: {user_input.strip()}"
            if len(title) > 50:
                title = title[:47] + "..."
            save_conversation_title(st.session_state.session_id, title)

        try:
            client = Client("Eshita-ds/cot-llm-298", hf_token = os.getenv("HF_API_TOKEN"))
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
                    response = "⚠️ Invalid response format."
            else:
                response = "⚠️ Empty response."
        except Exception as e:
            response = f"❗ Error: {e}"

        st.session_state.messages.append({"role": "bot", "content": response})
        save_message(st.session_state.session_id, "bot", response)
        st.session_state.pending_input = ""
        st.session_state.send_triggered = False
        st.rerun()

    # Display messages bottom-up
    messages = st.session_state.messages
    paired = []
    i = 0
    while i < len(messages) - 1:
        if messages[i]["role"] == "user" and messages[i+1]["role"] == "bot":
            paired.append((messages[i], messages[i+1]))
            i += 2
        else:
            i += 1

    for user_msg, bot_msg in paired:
        # User message
        ts_user = f"<div style='font-size:10px; color:gray; text-align:right;'>{user_msg['timestamp']}</div>" if show_timestamps else ""
        st.markdown(
            f"""
            <div style='display: flex; justify-content: flex-end;'>
                <div style='background-color: #DCF8C6; padding: 10px 15px; border-radius: 12px;
                            max-width: 75%; margin: 4px 0; box-shadow: 1px 1px 5px rgba(0,0,0,0.05);'>
                    <b>🧑 You:</b><br>{user_msg['content']}<br>{ts_user}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Bot message with typewriter effect
        ts_bot = f"<div style='font-size:10px; color:gray; text-align:left;'>{bot_msg['timestamp']}</div>" if show_timestamps else ""
        if bot_msg == st.session_state.messages[-1]:  # last bot message
            placeholder = st.empty()
            typed = ""
            for i in range(1, len(bot_msg['content']) + 1):
                typed = bot_msg['content'][:i]
                placeholder.markdown(
                    f"""
                    <div style='display: flex; justify-content: flex-start;'>
                        <div style='background-color: #F1F0F0; padding: 10px 15px; border-radius: 12px;
                                    max-width: 75%; margin: 4px 0; box-shadow: 1px 1px 5px rgba(0,0,0,0.05);'>
                            <b>🤖 Bot:</b><br>{typed}<br>{ts_bot}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                time.sleep(0.005)
        else:
            st.markdown(
                f"""
                <div style='display: flex; justify-content: flex-start;'>
                    <div style='background-color: #F1F0F0; padding: 10px 15px; border-radius: 12px;
                                max-width: 75%; margin: 4px 0; box-shadow: 1px 1px 5px rgba(0,0,0,0.05);'>
                        <b>🤖 Bot:</b><br>{bot_msg['content']}<br>{ts_bot}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# -------------------- MAIN --------------------

def main():
    st.set_page_config(page_title="COT Chatbot", page_icon="🤖")
    initialize_database()
    initialize_session()

    if not st.session_state.logged_in:
        login_page()
    else:
        chat_interface()

if __name__ == "__main__":
    main()
