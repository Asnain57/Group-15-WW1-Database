#import libraries
import sqlite3  # For interacting with SQLite databases
import pandas as pd  # For working with Excel files
import os  # For handling file paths and directories
from flask import Flask, request, render_template, redirect, url_for, session  # Flask web framework imports

app = Flask(__name__)  # Initialize the Flask web application
app.secret_key = 'supersecretkey'  # Secret key for session management in Flask

def init_db():
    """Initialize the SQLite database, creating necessary tables if they do not exist."""
    conn = sqlite3.connect('bradford_ww1.db')  # Connect to SQLite database
    cursor = conn.cursor()

    # Create the WW1 records tables if they do not exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS biographies (
        id INTEGER PRIMARY KEY,
        surname TEXT,
        forename TEXT,
        regiment TEXT,
        service_no TEXT,
        biography_attachment TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS townships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        surname TEXT,
        forename TEXT,
        address TEXT,
        electoral_ward TEXT,
        town TEXT,
        rank TEXT,
        regiment TEXT,
        unit TEXT,
        company TEXT,
        age INTEGER,
        service_no TEXT,
        other_regiment TEXT,
        other_unit TEXT,
        other_service_no TEXT,
        medals TEXT,
        enlistment_date TEXT,
        discharge_date TEXT,
        death_in_service_date TEXT,
        misc_info_nroh TEXT,
        cemetery_memorial TEXT,
        cemetery_memorial_ref TEXT,
        cemetery_memorial_country TEXT,
        additional_cwgc_info TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS memorials (
        id INTEGER PRIMARY KEY,
        surname TEXT,
        forename TEXT,
        regiment TEXT,
        unit TEXT,
        memorial TEXT,
        memorial_location TEXT,
        memorial_info TEXT,
        memorial_postcode TEXT,
        district TEXT,
        photo_available TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS newspapers (
        id INTEGER PRIMARY KEY,
        surname TEXT,
        forename TEXT,
        rank TEXT,
        address TEXT,
        regiment TEXT,
        unit TEXT,
        article_comment TEXT,
        newspaper_name TEXT,
        newspaper_date TEXT,
        page_col TEXT,
        photo_incl TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS burials (
        id INTEGER PRIMARY KEY,
        surname TEXT,
        forename TEXT,
        age INTEGER,
        medals TEXT,
        date_of_death TEXT,
        rank TEXT,
        service_no TEXT,
        regiment TEXT,
        unit TEXT,
        cemetery TEXT,
        grave_ref TEXT,
        misc_info TEXT
    )''')

    conn.commit()  # Save changes
    conn.close()   # Close the database connection


def load_spreadsheets():
    """Load data from Excel spreadsheets into the SQLite database."""
    folder_path = os.path.join(os.getcwd(), "data")  # Directory for data files
    conn = sqlite3.connect('bradford_ww1.db')  # Connect to SQLite database
    spreadsheets = {
        'biographies': 'Biography spreadsheet.xlsx',
        'townships': 'Bradford and surrounding townships Great War Roll of Honour 2025.xlsx',
        'memorials': 'Bradford Memorials.xlsx',
        'newspapers': 'Newspaper references 2025.xlsx',
        'burials': 'Those buried in Bradford.xlsx'
    }

    # Loop through each spreadsheet and load data into respective tables
    for table, file in spreadsheets.items():
        file_path = os.path.join(folder_path, file)
        if os.path.exists(file_path):  # Check if file exists
            df = pd.read_excel(file_path)  # Read Excel file into DataFrame

            # Ensure the dataframe columns are aligned correctly (case sensitive, etc.)
            df.to_sql(table, conn, if_exists='replace', index=False)
            print(f"Data from {file} loaded into {table} table.")
        else:
            print(f"File not found: {file_path}")

    conn.close()  # Close the database connection


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login requests."""
    if request.method == 'POST':
        username = request.form['username']  # Get the username from the form
        password = request.form['password']  # Get the password from the form
        conn = sqlite3.connect('bradford_ww1.db')  # Connect to the database
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cursor.fetchone()  # Check if user exists with the given credentials
        conn.close()

        if user:  # If user found, save the session and redirect to switchboard
            session['user'] = username  # Save user session
            return redirect(url_for('switchboard'))  # Redirect to switchboard
        return "Login Failed"
    return render_template('login.html')  # Render the login page


@app.route('/switchboard', methods=['GET', 'POST'])
def switchboard():
    """Main switchboard to select databases."""
    if request.method == 'POST':
        guest_password = request.form.get('guest-password')  # Get guest password from form
        admin_password = request.form.get('admin-password')  # Get admin password from form

        # Check the provided passwords and set the session user type
        if guest_password == "guest":
            session['user'] = 'guest'
            return redirect(url_for('switchboard'))
        elif admin_password == "admin":
            session['user'] = 'admin'
            return redirect(url_for('switchboard'))
        else:
            return "Invalid password, please try again."

    if 'user' in session:  # If user is logged in, show switchboard
        return render_template('switchboard.html')

    return redirect(url_for('login'))  # Redirect to login if user is not logged in


@app.route('/townships', methods=['GET', 'POST'])
def townships():
    """Display and search townships records with pagination."""
    conn = sqlite3.connect('bradford_ww1.db')
    cursor = conn.cursor()

    page = request.args.get('page', 1, type=int)  # Get the current page number, default is 1
    records_per_page = 10  # Number of records per page
    offset = (page - 1) * records_per_page  # Calculate offset for pagination

    # Default query to fetch all records
    query = "SELECT * FROM townships LIMIT ? OFFSET ?"
    count_query = "SELECT COUNT(*) FROM townships"
    params = (records_per_page, offset)
    
    search_query = ''
    search_type = ''

    # Handle search functionality
    if request.method == 'POST':
        search_type = request.form.get('search_type')  # e.g., 'surname', 'forename'
        search_query = request.form.get('search_query', '').strip()

        if search_query:  # If search_query is not empty
            query = f"SELECT * FROM townships WHERE {search_type} LIKE ? LIMIT ? OFFSET ?"
            count_query = f"SELECT COUNT(*) FROM townships WHERE {search_type} LIKE ?"
            params = ('%' + search_query + '%', records_per_page, offset)
        else:
            # If search_query is empty, show all records
            search_query = ''

    cursor.execute(count_query, ('%' + search_query + '%',) if search_query else ())
    total_records = cursor.fetchone()[0]  # Get total number of records

    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()

    # Determine Next and Previous pages
    next_page = page + 1 if offset + records_per_page < total_records else None
    previous_page = page - 1 if page > 1 else None

    return render_template('townships.html', records=records, page=page, 
                           next_page=next_page, previous_page=previous_page, 
                           search_query=search_query, search_type=search_type, total_results=total_records)


@app.route('/memorials', methods=['GET', 'POST'])
def memorials():
    """Display and search memorial records with pagination."""
    conn = sqlite3.connect('bradford_ww1.db')
    cursor = conn.cursor()

    page = request.args.get('page', 1, type=int)  # Get the current page number, default is 1
    records_per_page = 10  # Number of records per page
    offset = (page - 1) * records_per_page  # Calculate offset for pagination

    # Default query to fetch all records
    query = "SELECT * FROM memorials LIMIT ? OFFSET ?"
    count_query = "SELECT COUNT(*) FROM memorials"
    params = (records_per_page, offset)
    
    search_query = ''
    search_type = ''

    # Handle search functionality
    if request.method == 'POST':
        search_type = request.form.get('search_type')  # e.g., 'surname', 'forename', 'memorial_location'
        search_query = request.form.get('search_query', '').strip()

        if search_query:  # If search_query is not empty
            query = f"SELECT * FROM memorials WHERE {search_type} LIKE ? LIMIT ? OFFSET ?"
            count_query = f"SELECT COUNT(*) FROM memorials WHERE {search_type} LIKE ?"
            params = ('%' + search_query + '%', records_per_page, offset)
        else:
            # If search_query is empty, show all records
            search_query = ''

    cursor.execute(count_query, ('%' + search_query + '%',) if search_query else ())
    total_records = cursor.fetchone()[0]  # Get total number of records

    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()

    # Determine Next and Previous pages
    next_page = page + 1 if offset + records_per_page < total_records else None
    previous_page = page - 1 if page > 1 else None

    return render_template('memorials.html', records=records, page=page, 
                           next_page=next_page, previous_page=previous_page, 
                           search_query=search_query, search_type=search_type, total_results=total_records)


@app.route('/burials', methods=['GET', 'POST'])
def burials():
    """Display and search burial records with pagination."""
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    conn = sqlite3.connect('bradford_ww1.db')
    cursor = conn.cursor()

    page = request.args.get('page', 1, type=int)
    records_per_page = 10
    offset = (page - 1) * records_per_page

    query = "SELECT * FROM burials LIMIT ? OFFSET ?"
    count_query = "SELECT COUNT(*) FROM burials"
    params = (records_per_page, offset)

    search_query = ''
    search_type = ''

    # Handle search functionality
    if request.method == 'POST':
        search_type = request.form.get('search_type')  # 'surname' or 'forename'
        search_query = request.form.get('search_query', '').strip()

        if search_query:
            query = f"SELECT * FROM burials WHERE {search_type} LIKE ? LIMIT ? OFFSET ?"
            count_query = f"SELECT COUNT(*) FROM burials WHERE {search_type} LIKE ?"
            params = ('%' + search_query + '%', records_per_page, offset)

    cursor.execute(count_query, ('%' + search_query + '%',) if search_query else ())
    total_records = cursor.fetchone()[0]  # Get total number of records

    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()

    # Determine Next and Previous pages
    next_page = page + 1 if offset + records_per_page < total_records else None
    previous_page = page - 1 if page > 1 else None

    return render_template(
        'burials.html',
        records=records,
        page=page,
        next_page=next_page,
        previous_page=previous_page,
        search_query=search_query,
        search_type=search_type,
        total_results=total_records
    )


@app.route('/newspaper', methods=['GET', 'POST'])
def newspaper():
    """Display and search newspaper records with pagination."""
    conn = sqlite3.connect('bradford_ww1.db')
    cursor = conn.cursor()

    page = request.args.get('page', 1, type=int)
    records_per_page = 10
    offset = (page - 1) * records_per_page

    # Default query and params
    query = "SELECT * FROM newspapers LIMIT ? OFFSET ?"
    count_query = "SELECT COUNT(*) FROM newspapers"
    params = (records_per_page, offset)

    search_query = ''
    search_type = ''

    # Handle search functionality
    if request.method == 'POST':
        search_type = request.form.get('search_type')  # Field to search (e.g., surname, rank, etc.)
        search_query = request.form.get('search_query', '').strip()

        if search_query:
            query = f"SELECT * FROM newspapers WHERE {search_type} LIKE ? LIMIT ? OFFSET ?"
            count_query = f"SELECT COUNT(*) FROM newspapers WHERE {search_type} LIKE ?"
            params = ('%' + search_query + '%', records_per_page, offset)

    # Execute count and data query
    cursor.execute(count_query, ('%' + search_query + '%',) if search_query else ())
    total_records = cursor.fetchone()[0]  # Get total number of records

    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()

    # Pagination logic
    next_page = page + 1 if offset + records_per_page < total_records else None
    previous_page = page - 1 if page > 1 else None

    return render_template(
        'newspaper.html',
        records=records,
        page=page,
        next_page=next_page,
        previous_page=previous_page,
        search_query=search_query,
        search_type=search_type,
        total_results=total_records
    )


@app.route('/biographies', methods=['GET', 'POST'])
def biographies():
    """Display and search biography records."""
    if 'user' in session:  # Check if user is logged in
        conn = sqlite3.connect('bradford_ww1.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            search_term = request.form['search']  # Search term input from the user
            cursor.execute("SELECT * FROM biographies WHERE surname LIKE ? OR forename LIKE ?", ('%' + search_term + '%', '%' + search_term + '%'))
        else:
            cursor.execute("SELECT * FROM biographies")  # If no search term, fetch all records
        
        records = cursor.fetchall()  # Fetch biography records
        conn.close()
        return render_template('biographies.html', records=records)  # Render biographies page with results
    return redirect(url_for('login'))  # Redirect to login page if user is not logged in


if __name__ == '__main__':
    init_db()  # Initialize the database
    load_spreadsheets()  # Load data from spreadsheets into the database
    app.run(debug=True)  # Start the Flask application with debugging enabled