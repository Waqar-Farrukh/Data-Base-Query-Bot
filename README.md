# 🤖 Text-to-SQL Database Query Bot

A professional, AI-powered chat interface that lets non-technical users query a database using plain English. The app translates natural language into SQL, executes it safely, and returns results in a clean, modern UI.

## Tech Stack

| Component | Technology |
|---|---|
| **Backend** | Python 3.10+ |
| **Database** | SQLite (built-in) |
| **LLM** | Google Gemini 2.0 Flash (via LangChain) |
| **Frontend** | Streamlit |

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Your API key is already saved in the `.env` file. Alternatively, you can enter it in the app's sidebar.

### 3. Initialize the Database

```bash
python db_setup.py
```

This creates `company.db` with 5 tables and 57+ rows of realistic mock data.

### 4. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Database Schema

| Table | Rows | Description |
|---|---|---|
| **Departments** | 5 | Company departments with budgets |
| **Employees** | 15 | Staff with positions, salaries, and departments |
| **Projects** | 10 | Company projects with status tracking |
| **Tasks** | 15 | Individual tasks within projects |
| **Salary_History** | 12 | Employee salary change log |

## Example Questions

- "Show me all employees in Engineering"
- "What is the total budget for all projects?"
- "Who earns the highest salary?"
- "List employees hired after 2022"
- "How many tasks are in progress?"
- "Show salary history for Ahmed Khan"
- "Which department has the most projects?"

## Project Structure

```
DBQuery Bot/
├── app.py              # Streamlit chat UI
├── db_setup.py         # Database initialization & mock data
├── db_utils.py         # Schema extraction & safe query execution
├── llm_engine.py       # LangChain + Gemini text-to-SQL engine
├── requirements.txt    # Python dependencies
├── .env                # API key configuration
└── README.md           # This file
```

## Safety Features

- **SELECT-only enforcement**: The app blocks all data-modifying queries (DROP, DELETE, INSERT, etc.)
- **Read-only database connection**: Uses SQLite's `?mode=ro` URI flag
- **Query timeout**: 10-second timeout prevents runaway queries
- **Input validation**: Multi-layer SQL validation before execution
