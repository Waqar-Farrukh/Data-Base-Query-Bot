"""
app.py — Streamlit Chat UI for the Text-to-SQL Bot
====================================================
Premium WhatsApp-style chat interface featuring:
  • Modern glassmorphism design
  • Chat input with full message history
  • Inline data tables for query results
  • Sidebar with database overview, schema, query history
  • No API key field — loads securely from .env

Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv

from db_setup import main as setup_database, DB_PATH
from db_utils import get_schema_dict, get_schema, execute_query
from llm_engine import process_question

# ── Load environment variables ──────────────────────────────────────
load_dotenv()


# ═══════════════════════════════════════════════════════════════════
#  PAGE CONFIG & PREMIUM CSS
# ═══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="DB Query Bot — AI Database Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Reset & Global ── */
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 0;
        max-width: 950px;
    }

    /* ── Sidebar Premium Dark Theme ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(175deg, #0f0c29 0%, #1a1a3e 35%, #24243e 70%, #0f0c29 100%);
        border-right: 1px solid rgba(139, 92, 246, 0.15);
    }
    section[data-testid="stSidebar"] * {
        color: #c4b5fd !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e0d4ff !important;
        letter-spacing: -0.3px;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(139, 92, 246, 0.15) !important;
        margin: 0.8rem 0;
    }

    /* ── Sidebar Brand Header ── */
    .sidebar-brand {
        text-align: center;
        padding: 1.2rem 0.5rem 0.8rem;
    }
    .sidebar-brand-icon {
        font-size: 2.4rem;
        display: block;
        margin-bottom: 0.3rem;
    }
    .sidebar-brand-title {
        font-size: 1.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a78bfa, #818cf8, #6366f1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    .sidebar-brand-sub {
        font-size: 0.72rem;
        color: #7c72a0 !important;
        font-weight: 400;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 2px;
    }

    /* ── Stat Cards Row ── */
    .stat-row {
        display: flex;
        gap: 8px;
        margin: 0.5rem 0 0.3rem;
    }
    .stat-card {
        flex: 1;
        background: rgba(139, 92, 246, 0.08);
        border: 1px solid rgba(139, 92, 246, 0.15);
        border-radius: 10px;
        padding: 10px 8px;
        text-align: center;
        transition: all 0.25s ease;
    }
    .stat-card:hover {
        background: rgba(139, 92, 246, 0.14);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
    }
    .stat-num {
        font-size: 1.3rem;
        font-weight: 700;
        color: #a78bfa !important;
        line-height: 1.2;
    }
    .stat-label {
        font-size: 0.65rem;
        color: #7c72a0 !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 500;
    }

    /* ── Schema Section ── */
    .schema-section-title {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #7c72a0 !important;
        margin: 0.6rem 0 0.5rem;
        padding-left: 2px;
    }
    .schema-card {
        background: rgba(139, 92, 246, 0.06);
        border: 1px solid rgba(139, 92, 246, 0.12);
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 6px;
        transition: all 0.2s ease;
    }
    .schema-card:hover {
        background: rgba(139, 92, 246, 0.12);
        border-color: rgba(139, 92, 246, 0.25);
    }
    .schema-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
    }
    .schema-card-name {
        font-weight: 600;
        font-size: 0.88rem;
        color: #c4b5fd !important;
    }
    .schema-card-badge {
        font-size: 0.65rem;
        background: rgba(139, 92, 246, 0.2);
        color: #a78bfa !important;
        padding: 2px 8px;
        border-radius: 20px;
        font-weight: 500;
    }
    .schema-cols {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
    }
    .schema-col-chip {
        font-size: 0.72rem;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(139, 92, 246, 0.1);
        color: #8b8ba0 !important;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 400;
    }
    .schema-col-chip.pk {
        color: #fbbf24 !important;
        border-color: rgba(251, 191, 36, 0.25);
        background: rgba(251, 191, 36, 0.08);
    }
    .schema-col-chip.fk {
        color: #34d399 !important;
        border-color: rgba(52, 211, 153, 0.2);
        background: rgba(52, 211, 153, 0.06);
    }

    /* ── Query History ── */
    .history-item {
        background: rgba(139, 92, 246, 0.05);
        border: 1px solid rgba(139, 92, 246, 0.1);
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 5px;
        cursor: default;
        transition: all 0.2s ease;
    }
    .history-item:hover {
        background: rgba(139, 92, 246, 0.1);
    }
    .history-question {
        font-size: 0.78rem;
        color: #c4b5fd !important;
        font-weight: 500;
        line-height: 1.3;
    }
    .history-time {
        font-size: 0.63rem;
        color: #5b5580 !important;
        margin-top: 3px;
    }

    /* ── Main Header ── */
    .main-header {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 40%, #a855f7 100%);
        padding: 1.8rem 2.5rem;
        border-radius: 20px;
        margin-bottom: 1.2rem;
        text-align: center;
        box-shadow: 0 12px 40px rgba(99, 102, 241, 0.25);
        position: relative;
        overflow: hidden;
    }
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.08) 0%, transparent 50%);
        pointer-events: none;
    }
    .main-header h1 {
        color: white !important;
        font-size: 1.9rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        padding: 0 !important;
        letter-spacing: -0.5px;
        position: relative;
    }
    .main-header p {
        color: rgba(255,255,255,0.8) !important;
        font-size: 0.9rem !important;
        margin: 0.4rem 0 0 0 !important;
        font-weight: 400;
        position: relative;
    }

    /* ── Welcome Card ── */
    .welcome-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.05) 0%, rgba(139,92,246,0.08) 100%);
        border: 1px solid rgba(139, 92, 246, 0.12);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .welcome-card h3 {
        color: #6366f1 !important;
        font-size: 1.1rem !important;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .welcome-card p {
        color: #64748b !important;
        font-size: 0.88rem;
        line-height: 1.5;
        margin: 0;
    }
    .welcome-suggestions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        justify-content: center;
        margin-top: 1rem;
    }
    .welcome-chip {
        background: rgba(99, 102, 241, 0.08);
        border: 1px solid rgba(99, 102, 241, 0.15);
        color: #6366f1 !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        cursor: default;
    }

    /* ── Chat Messages ── */
    .stChatMessage {
        border-radius: 16px !important;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    }

    /* ── SQL Expander ── */
    .sql-block {
        background: rgba(15, 12, 41, 0.03);
        border: 1px solid rgba(139, 92, 246, 0.1);
        border-radius: 10px;
        padding: 10px 14px;
        font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
        font-size: 0.82rem;
        color: #6366f1 !important;
        white-space: pre-wrap;
        word-wrap: break-word;
        line-height: 1.5;
    }

    /* ── Hide Streamlit defaults ── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }

    /* ── Dataframe ── */
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    /* ── Sidebar buttons ── */
    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(139, 92, 246, 0.1) !important;
        border: 1px solid rgba(139, 92, 246, 0.2) !important;
        color: #c4b5fd !important;
        font-size: 0.78rem !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        transition: all 0.2s ease !important;
        text-align: left !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(139, 92, 246, 0.2) !important;
        border-color: rgba(139, 92, 246, 0.4) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Connection indicator ── */
    .conn-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(52, 211, 153, 0.1);
        border: 1px solid rgba(52, 211, 153, 0.25);
        color: #34d399 !important;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 500;
    }
    .conn-dot {
        width: 6px;
        height: 6px;
        background: #34d399;
        border-radius: 50%;
        display: inline-block;
        animation: pulse-dot 2s ease-in-out infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  INITIALIZATION
# ═══════════════════════════════════════════════════════════════════

def initialize_database():
    """Ensure the database exists; create it if not."""
    if not os.path.exists(DB_PATH):
        setup_database()


def initialize_session_state():
    """Set up Streamlit session state variables."""
    # Always try to reload from env to catch updates
    load_dotenv(override=True)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_sql" not in st.session_state:
        st.session_state.last_sql = None
    if "query_history" not in st.session_state:
        st.session_state.query_history = []  # list of {question, sql, timestamp}
        
    st.session_state.api_key = os.getenv("GOOGLE_API_KEY", "")
    st.session_state.groq_api_key = os.getenv("GROQ_API_KEY", "")


initialize_database()
initialize_session_state()


# ═══════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════

with st.sidebar:
    # ── Brand Header ──
    st.markdown("""
        <div class="sidebar-brand">
            <span class="sidebar-brand-icon">🤖</span>
            <div class="sidebar-brand-title">DB Query Bot</div>
            <div class="sidebar-brand-sub">AI Database Assistant</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Connection Status ──
    st.markdown("""
        <div style="text-align: center; margin-bottom: 0.3rem;">
            <span class="conn-badge">
                <span class="conn-dot"></span>
                Connected to company.db
            </span>
        </div>
    """, unsafe_allow_html=True)

    # ── Database Stats ──
    try:
        schema_dict = get_schema_dict()
        total_tables = len(schema_dict)
        total_rows = sum(t["row_count"] for t in schema_dict.values())
        total_cols = sum(len(t["columns"]) for t in schema_dict.values())

        st.markdown(f"""
            <div class="stat-row">
                <div class="stat-card">
                    <div class="stat-num">{total_tables}</div>
                    <div class="stat-label">Tables</div>
                </div>
                <div class="stat-card">
                    <div class="stat-num">{total_rows}</div>
                    <div class="stat-label">Records</div>
                </div>
                <div class="stat-card">
                    <div class="stat-num">{total_cols}</div>
                    <div class="stat-label">Columns</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    except Exception:
        schema_dict = {}

    st.markdown("---")

    # ── Database Schema (columns only, no types) ──
    st.markdown('<div class="schema-section-title">📊 Database Schema</div>', unsafe_allow_html=True)

    for table_name, table_info in schema_dict.items():
        columns = table_info["columns"]
        row_count = table_info["row_count"]

        # Build column chips — just names, colored by PK/FK
        chips_html = ""
        for col in columns:
            extra_class = ""
            if col["pk"]:
                extra_class = " pk"
            elif col["fk"]:
                extra_class = " fk"
            chips_html += f'<span class="schema-col-chip{extra_class}">{col["name"]}</span>'

        st.markdown(f"""
            <div class="schema-card">
                <div class="schema-card-header">
                    <span class="schema-card-name">{table_name}</span>
                    <span class="schema-card-badge">{row_count} rows</span>
                </div>
                <div class="schema-cols">{chips_html}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Query History ──
    st.markdown('<div class="schema-section-title">🕒 Query History</div>', unsafe_allow_html=True)

    if st.session_state.query_history:
        # Show most recent first, max 10
        for entry in reversed(st.session_state.query_history[-10:]):
            st.markdown(f"""
                <div class="history-item">
                    <div class="history-question">💬 {entry['question']}</div>
                    <div class="history-time">{entry['timestamp']}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="text-align:center; font-size:0.78rem; color:#5b5580 !important; padding:12px 0;">'
            'No queries yet. Ask a question to get started!</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Last Executed SQL ──
    with st.expander("🔍 Last Executed SQL", expanded=False):
        if st.session_state.last_sql:
            st.code(st.session_state.last_sql, language="sql")
        else:
            st.caption("No query executed yet.")

    st.markdown("---")

    # ── Sample Questions ──
    st.markdown('<div class="schema-section-title">💡 Try Asking</div>', unsafe_allow_html=True)

    sample_questions = [
        "Show me all employees in Engineering",
        "What is the total budget for all projects?",
        "Who earns the highest salary?",
        "How many tasks are in progress?",
        "Show salary history for Ahmed Khan",
        "Which department has the most projects?",
        "List all completed projects with their leads",
        "What are the critical priority tasks?",
    ]
    for q in sample_questions:
        if st.button(f"💬 {q}", key=f"sample_{q}", use_container_width=True):
            st.session_state.sample_question = q
            st.rerun()

    st.markdown("---")

    # ── Clear Chat ──
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_sql = None
        st.session_state.query_history = []
        st.rerun()


# ═══════════════════════════════════════════════════════════════════
#  MAIN CHAT AREA
# ═══════════════════════════════════════════════════════════════════

# ── Header ──
st.markdown("""
    <div class="main-header">
        <h1>🤖 DB Query Bot</h1>
        <p>Ask questions about your company database in plain English</p>
    </div>
""", unsafe_allow_html=True)

# ── Welcome card when no messages ──
if not st.session_state.messages:
    st.markdown("""
        <div class="welcome-card">
            <h3>👋 Welcome! I'm your AI Database Assistant</h3>
            <p>
                I can translate your plain English questions into SQL queries,
                run them against the company database, and explain the results.
                Try one of these to get started:
            </p>
            <div class="welcome-suggestions">
                <span class="welcome-chip">📋 All employees</span>
                <span class="welcome-chip">💰 Highest salary</span>
                <span class="welcome-chip">📊 Project budgets</span>
                <span class="welcome-chip">📈 Task status</span>
                <span class="welcome-chip">🏢 Department info</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ── Display chat history ──
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])

        # If this message has associated data, show it as a table
        if "dataframe" in message and message["dataframe"] is not None:
            st.dataframe(message["dataframe"], use_container_width=True, hide_index=True)

        # Show the SQL query in an expander within the chat
        if "sql" in message and message["sql"]:
            with st.expander("📝 View SQL Query", expanded=False):
                st.code(message["sql"], language="sql")


# ── Handle sample question injection ──
sample_q = st.session_state.pop("sample_question", None)

# ── Chat input ──
user_input = st.chat_input("Ask anything about your database...", key="chat_input")

# Use sample question if one was clicked
prompt = sample_q or user_input

if prompt:
    # ── Validate API key ──
    if not st.session_state.api_key and not st.session_state.groq_api_key:
        st.error("⚠️ No API key found. Please set either GOOGLE_API_KEY or GROQ_API_KEY in your .env file.")
        st.stop()

    # ── Add user message to history ──
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    # ── Process the question with the LLM ──
    with st.chat_message("assistant", avatar="🤖"):
        status_placeholder = st.empty()

        def update_status(text):
            status_placeholder.markdown(f"*{text}*")

        with st.spinner("🔍 Analyzing your question..."):
            result = process_question(
                api_key=st.session_state.api_key,
                question=prompt,
                db_path=DB_PATH,
                status_callback=update_status,
                groq_api_key=st.session_state.groq_api_key,
            )

        # Clear the status placeholder
        status_placeholder.empty()

        # Update last SQL in sidebar
        if result.get("sql_query"):
            st.session_state.last_sql = result["sql_query"]

        # Add to query history
        st.session_state.query_history.append({
            "question": prompt,
            "sql": result.get("sql_query", "N/A"),
            "timestamp": datetime.now().strftime("%I:%M %p"),
        })

        # Display the natural language response
        st.markdown(result["response"])

        # Prepare message data for history
        message_data = {
            "role": "assistant",
            "content": result["response"],
            "sql": result.get("sql_query"),
            "dataframe": None,
        }

        # If we have tabular results, show them as a dataframe
        if (
            result.get("results")
            and result["results"].get("success")
            and result["results"]["rows"]
        ):
            df = pd.DataFrame(
                result["results"]["rows"],
                columns=result["results"]["columns"],
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            message_data["dataframe"] = df

            st.caption(f"📊 {result['results']['row_count']} row(s) returned")

        # Show SQL in expander
        if result.get("sql_query"):
            with st.expander("📝 View SQL Query", expanded=False):
                st.code(result["sql_query"], language="sql")

        # Save to history
        st.session_state.messages.append(message_data)
