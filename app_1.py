import streamlit as st
import mysql.connector
import os
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Custom CSS
st.markdown("""
<style>
body {
    font-family: Arial, sans-serif;
    color: #333;
}
.title {
    font-size: 36px;
    color: #4CAF50;
    text-align: center;
    margin-bottom: 20px;
}
.header {
    font-size: 28px;
    color: #333;
    margin-bottom: 10px;
}
.stTextInput input {
    border: 2px solid #4CAF50;
    border-radius: 5px;
    padding: 8px;
}
.stTextInput input:focus {
    border-color: #45a049;
    box-shadow: 0 0 5px rgba(0, 255, 0, 0.3);
}
.stButton button {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 10px 20px;
    text-align: center;
    text-decoration: none;
    display: inline-block;
    font-size: 16px;
    margin: 4px 2px;
    cursor: pointer;
    border-radius: 5px;
}
.stButton button:hover {
    background-color: #45a049;
}
.custom-card {
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    padding: 20px;
    margin: 10px;
}
.stDataFrame {
    border-collapse: collapse;
    width: 100%;
}
.stDataFrame th, .stDataFrame td {
    border: 1px solid #ddd;
    padding: 8px;
}
.stDataFrame th {
    background-color: #4CAF50;
    color: white;
}
.stDataFrame tr:nth-child(even) {
    background-color: #f2f2f2;
}
.stDataFrame tr:hover {
    background-color: #ddd;
}
</style>
""", unsafe_allow_html=True)

# MySQL connection functions
def create_connection(host, user, password):
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password
        )
        st.session_state.connection = connection
        st.success("Connection to MySQL successful")
        return connection
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
        return None

def list_databases(connection):
    cursor = connection.cursor()
    cursor.execute("SHOW DATABASES")
    databases = cursor.fetchall()
    cursor.close()
    return databases

def create_database(connection, database):
    cursor = connection.cursor()
    try:
        cursor.execute(f"CREATE DATABASE `{database}`")
        st.success(f"Database '{database}' created successfully.")
    except mysql.connector.Error as err:
        st.error(f"Error creating database: {err}")
    cursor.close()

def select_database(connection, database):
    try:
        connection.database = database
        st.success(f"Database '{database}' selected.")
    except mysql.connector.Error as err:
        st.error(f"Error selecting database: {err}")

def show_tables(connection):
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    cursor.close()
    return tables

def import_sql_file(connection, file):
    cursor = connection.cursor()
    try:
        with open(file, 'r') as f:
            sql = f.read()
        cursor.execute(sql, multi=True)
        connection.commit()
        st.success("SQL file executed successfully.")
    except mysql.connector.Error as err:
        st.error(f"Error executing SQL file: {err}")
    finally:
        cursor.close()

# Google Gemini functions
def get_gemini_response(question, prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[0], question])
    return response.text

def read_sql_query(sql, connection):
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except mysql.connector.Error as err:
        st.error(f"Error executing query: {err}")
        return []

# Define your prompt for Gemini API with correct table and column names
prompt = [
    """
    You are an expert in converting English questions to SQL query!
    The SQL database has a table named 'movie' with the following columns: 'movie_id','title', 'release_year', 
    'genre', 'rating'. 

    Example 1 - How many movies are in the database?, 
    the SQL command will be something like this SELECT COUNT(*) FROM movies;

    Example 2 - List all movies released after 2010, 
    the SQL command will be something like this SELECT * FROM movies WHERE release_year > 2010;

    also the SQL code should not have ``` in beginning or end and SQL word in output.
    """
]

# Streamlit app
def main():
    st.sidebar.title("Navigation")
    option = st.sidebar.selectbox("Choose a section", ["Connection Page", "SQL Operations", "Text-to-SQL"])

    if option == "Connection Page":
        connection_page()
    elif option == "SQL Operations":
        sql_portion_page()
    elif option == "Text-to-SQL":
        text_to_sql_page()

def connection_page():
    st.markdown('<div class="title">Connection to MySQL</div>', unsafe_allow_html=True)

    host = st.text_input("MySQL Host", value="localhost")
    user = st.text_input("MySQL Username", value="root")
    password = st.text_input("MySQL Password", type="password")

    if st.button("Connect"):
        connection = create_connection(host, user, password)
        if connection:
            st.session_state.page = "sql_portion_page"
            st.experimental_rerun()

def sql_portion_page():
    st.markdown('<div class="title">SQL Operations</div>', unsafe_allow_html=True)
    connection = st.session_state.connection

    databases = list_databases(connection)
    st.write("**Databases available:**")
    st.dataframe(pd.DataFrame(databases, columns=['Database']), use_container_width=True)

    database_name = st.text_input("Enter Database Name")

    if st.button("Check Database"):
        if database_name:
            if any(database_name == db[0] for db in databases):
                st.success(f"Database '{database_name}' exists.")
                select_database(connection, database_name)
                st.session_state.database_name = database_name
                st.session_state.page = "tables_page"
                st.experimental_rerun()
            else:
                st.error(f"Database '{database_name}' does not exist.")
                st.session_state.database_name = None
                st.session_state.page = "sql_editor_page"
                st.experimental_rerun()
        else:
            st.error("Please enter a database name.")

def tables_page():
    st.markdown('<div class="title">Tables</div>', unsafe_allow_html=True)
    connection = st.session_state.connection

    tables = show_tables(connection)
    st.write("**Tables available:**")
    st.dataframe(pd.DataFrame(tables, columns=['Table']), use_container_width=True)

def sql_editor_page():
    st.markdown('<div class="title">SQL Editor</div>', unsafe_allow_html=True)
    connection = st.session_state.connection

    database_name = st.text_input("Enter Database Name to Create")
    sql_file = st.file_uploader("Upload SQL File", type=["sql"])

    if st.button("Create Database"):
        if database_name:
            create_database(connection, database_name)
            select_database(connection, database_name)
            st.session_state.database_name = database_name
            st.session_state.page = "tables_page"
            st.experimental_rerun()
        else:
            st.error("Please enter a database name.")

    if sql_file is not None:
        temp_file_path = os.path.join("temp", sql_file.name)
        with open(temp_file_path, "wb") as f:
            f.write(sql_file.getbuffer())
        import_sql_file(connection, temp_file_path)

    if st.button("Back to SQL Operations"):
        st.session_state.page = "sql_portion_page"
        st.experimental_rerun()

def text_to_sql_page():
    st.markdown('<div class="title">Text-to-SQL</div>', unsafe_allow_html=True)
    connection = st.session_state.connection

    if "database_name" not in st.session_state or not st.session_state.database_name:
        st.error("Please select a database in the SQL Operations page first.")
        return

    st.write(f"**Using Database:** {st.session_state.database_name}")

    st.write("**Enter your question:**")
    question = st.text_input("Your Question")

    if st.button("Generate SQL"):
        if question:
            # Get the generated SQL query from the Gemini API
            response = get_gemini_response(question, prompt)
            st.write("**Generated SQL Query:**")
            st.code(response, language='sql')

            try:
                # Execute the generated SQL query
                cursor = connection.cursor()
                cursor.execute(response)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                cursor.close()

                st.write("**Query Result:**")
                df = pd.DataFrame(rows, columns=columns)
                st.dataframe(df)
            except mysql.connector.Error as err:
                st.error(f"Error executing query: {err}")
        else:
            st.error("Please enter a question.")

# Run the app
if __name__ == "__main__":
    main()
