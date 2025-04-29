import gradio as gr
import sqlite3
import uuid

# Initialize Database
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

# Save Messages to Database
def save_message(session_id, role, content):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
    conn.commit()
    conn.close()

# Get Conversation History
def get_conversation_history(session_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT role, content FROM conversations WHERE session_id = ?", (session_id,))
    history = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in history]

# Get Conversation Count
def get_conversation_count():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT session_id) FROM conversations")
    count = c.fetchone()[0]
    conn.close()
    return count

# Initialize Session Data
session_data = {
    "session_id": str(uuid.uuid4()),
    "messages": []
}

# Function to Start New Chat
def start_new_chat():
    session_data["session_id"] = str(uuid.uuid4())
    session_data["messages"] = []
    return [], "New chat started!"

# Function to Handle Chat Interaction
def chat(user_input):
    if not user_input:
        return session_data["messages"], "Please enter a message."

    session_data["messages"].append({"role": "user", "content": user_input})
    save_message(session_data["session_id"], "user", user_input)

    # Placeholder response (Replace with actual model inference)
    response = "<Here will be the response from trained model>"
    session_data["messages"].append({"role": "bot", "content": response})
    save_message(session_data["session_id"], "bot", response)

    return [(msg["role"], msg["content"]) for msg in session_data["messages"]], ""

# Fetch Available Conversations for Sidebar
def get_conversations():
    initialize_database()  # Ensure the database and table exist before querying
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT session_id FROM conversations")
    sessions = c.fetchall()
    conn.close()
    return [f"Conversation {i+1}" for i in range(len(sessions))]


# Function to Load a Selected Conversation
def load_conversation(conversation_name):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT session_id FROM conversations")
    sessions = c.fetchall()
    conn.close()

    if sessions:
        index = int(conversation_name.split(" ")[-1]) - 1
        session_id = sessions[index][0]
        session_data["session_id"] = session_id
        session_data["messages"] = get_conversation_history(session_id)
    
    return [(msg["role"], msg["content"]) for msg in session_data["messages"]]

# Gradio Interface
with gr.Blocks() as demo:
    gr.Markdown("## COT-Reasoning GPT")

    # Sidebar for Conversation History
    with gr.Row():
        conversation_selector = gr.Dropdown(
            choices=get_conversations(),
            label="Conversation History",
            interactive=True
        )
        load_button = gr.Button("Load Conversation")

    # Chat Interface
    chatbot = gr.Chatbot(label="Chat with AI")
    user_input = gr.Textbox(label="Ask a question:")
    send_button = gr.Button("Send")
    new_chat_button = gr.Button("Start New Chat")

    # Actions
    send_button.click(chat, user_input, [chatbot, user_input])
    new_chat_button.click(start_new_chat, [], [chatbot])
    load_button.click(load_conversation, conversation_selector, chatbot)

# Launch Gradio App
if __name__ == "__main__":
    initialize_database()
    demo.launch()
