"""
llm_engine.py — LangChain + Google Gemini Text-to-SQL Engine
==============================================================
Two-phase LLM pipeline:
  Phase 1: User question → SQL query  (Text-to-SQL)
  Phase 2: SQL results   → Natural language summary

Uses Google Gemini (gemini-2.0-flash) via langchain-google-genai.
Includes a seamless fallback to Groq (llama3-70b-8192) if Gemini fails 
due to rate limits, network errors, or quotas.
"""

import re
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from db_utils import get_schema, execute_query


# ── System prompt for Phase 1: Text → SQL ──────────────────────────
SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert SQL query generator for SQLite databases.
Your task is to convert a user's natural language question into a valid SQLite SELECT query.

DATABASE SCHEMA:
{schema}

RULES:
1. Generate ONLY a single valid SQLite SELECT query.
2. NEVER use DROP, DELETE, INSERT, UPDATE, ALTER, CREATE, or any data-modifying statement.
3. Use proper JOINs when the question involves data from multiple tables.
4. Use table aliases for readability (e.g., e for Employees, d for Departments).
5. If the question is ambiguous, make a reasonable assumption and write the best query.
6. Return ONLY the SQL query — no explanations, no markdown formatting, no code fences.
7. Always end the query with a semicolon.
8. Use column names exactly as shown in the schema (case-sensitive).
9. For boolean columns like is_active: 1 = active/yes, 0 = inactive/no.
10. Date columns store dates as TEXT in 'YYYY-MM-DD' format.
"""),
    ("human", "{question}"),
])


# ── System prompt for Phase 2: Results → Natural Language ──────────
RESPONSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful data analyst assistant. The user asked a question about company data,
and a SQL query was executed to find the answer. Your job is to summarize the results
in a clear, friendly, natural language response.

RULES:
1. Present the data clearly and concisely.
2. If the results contain numbers (salaries, budgets), format them nicely (e.g., $120,000).
3. If there are many rows, summarize the key findings rather than listing every row.
4. If the results are empty, say so politely and suggest the user rephrase their question.
5. Use bullet points or short paragraphs for readability.
6. Do NOT include any SQL in your response.
7. Be conversational but professional.
"""),
    ("human", """User's original question: {question}

SQL Query that was executed:
{sql_query}

Query Results (columns: {columns}):
{results}

Please provide a natural language summary of these results."""),
])


def _clean_sql(raw: str) -> str:
    """Clean the LLM output to extract just the SQL query."""
    text = raw.strip()

    # Remove markdown code fences if present
    fence_match = re.search(r"```(?:sql)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    # If there are multiple lines and the first line looks like commentary,
    # try to extract just the SELECT statement
    if not text.upper().startswith(("SELECT", "WITH")):
        select_match = re.search(r"((?:SELECT|WITH)\b.*)", text, re.DOTALL | re.IGNORECASE)
        if select_match:
            text = select_match.group(1).strip()

    # Ensure it ends with a semicolon
    if not text.endswith(";"):
        text += ";"

    return text


def create_gemini_llm(api_key: str, temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """Create a configured Gemini LLM instance."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key,
        temperature=temperature,
        max_output_tokens=2048,
    )

def create_groq_llm(api_key: str, temperature: float = 0.0) -> ChatGroq:
    """Create a configured Groq LLM instance (Fallback)."""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=api_key,
        temperature=temperature,
    )


def generate_sql(llm, question: str, schema: str) -> str:
    """Phase 1: Convert a natural language question into a SQL query."""
    chain = SQL_GENERATION_PROMPT | llm
    response = chain.invoke({"schema": schema, "question": question})
    return _clean_sql(response.content)


def generate_response(llm, question, sql_query, columns, results) -> str:
    """Phase 2: Generate a natural language summary of query results."""
    if results:
        result_str = " | ".join(columns) + "\n"
        result_str += "-" * len(result_str) + "\n"
        for row in results[:50]:
            result_str += " | ".join(str(val) for val in row) + "\n"
        if len(results) > 50:
            result_str += f"\n... and {len(results) - 50} more rows."
    else:
        result_str = "(No results returned)"

    chain = RESPONSE_PROMPT | llm
    response = chain.invoke({
        "question": question,
        "sql_query": sql_query,
        "columns": ", ".join(columns),
        "results": result_str,
    })
    return response.content


def execute_pipeline(llm, question, schema, db_path, status_callback=None):
    """Executes the core logical pipeline using a specific LLM."""
    if status_callback:
        status_callback("🧠 Generating SQL query...")
    
    sql_query = generate_sql(llm, question, schema)

    if status_callback:
        status_callback("⚡ Executing query...")

    result = execute_query(sql_query, db_path)

    if not result["success"]:
        return {
            "sql_query": sql_query,
            "results": result,
            "response": (
                f"⚠️ The generated query could not be executed.\n\n"
                f"**Error:** {result['error']}\n\n"
                f"Please try rephrasing your question."
            ),
            "error": result["error"],
        }

    if status_callback:
        status_callback("✍️ Summarizing results...")

    response = generate_response(
        llm, question, sql_query,
        result["columns"], result["rows"]
    )

    return {
        "sql_query": sql_query,
        "results": result,
        "response": response,
        "error": None,
    }


def process_question(api_key: str, question: str, db_path: str = None, status_callback=None, groq_api_key: str = None) -> dict:
    """
    Main entry point. Attempts to answer using Gemini, and if it fails (due to 
    network/DNS/quota/etc.), seamlessly falls back to Groq if the key is provided.
    """
    schema = get_schema(db_path)

    try:
        # Attempt Primary: Google Gemini
        if status_callback:
            status_callback("🔍 Initializing Gemini...")
        llm = create_gemini_llm(api_key)
        return execute_pipeline(llm, question, schema, db_path, status_callback)

    except Exception as gemini_err:
        gemini_error_str = str(gemini_err)
        
        # If Groq is missing, return the error
        if not groq_api_key:
            return {
                "sql_query": None,
                "results": None,
                "response": f"❌ Google API Error (No Groq fallback available):\n\n{gemini_error_str}",
                "error": gemini_error_str,
            }

        # Attempt Fallback: Groq
        if status_callback:
            status_callback("🔄 Gemini failed. Switching to Groq Fallback...")
            time.sleep(1) # Visual cue for the user
        
        try:
            llm = create_groq_llm(groq_api_key)
            return execute_pipeline(llm, question, schema, db_path, status_callback)
        except Exception as groq_err:
            return {
                "sql_query": None,
                "results": None,
                "response": (
                    f"❌ Both LLMs failed.\n\n"
                    f"**Gemini Error:** {gemini_error_str}\n"
                    f"**Groq Error:** {str(groq_err)}"
                ),
                "error": str(groq_err),
            }
