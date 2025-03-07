#import libraries
import sqlite3
import pandas as pd
import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def init_db():
    """Initialize the SQLite database, creating necessary tables if they do not exist."""
    conn = sqlite3.connect('bradford_ww1.db') # Connect to SQLite database
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
        if os.path.exists(file_path):
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

        if user:
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
    """Display and search townships records."""
    page = request.args.get('page', 1, type=int)  # Get the current page number
    search_term = request.form['search'] if request.method == 'POST' else ''  # Get search term if POST request

    conn = sqlite3.connect('bradford_ww1.db')  # Connect to the database
    cursor = conn.cursor()

    # Search query with pagination (limit 10 records per page)
    cursor.execute('SELECT * FROM townships WHERE surname LIKE ? OR forename LIKE ? LIMIT ? OFFSET ?',
                   ('%' + search_term + '%', '%' + search_term + '%', 10, (page - 1) * 10))
    records = cursor.fetchall()

    cursor.execute('SELECT COUNT(*) FROM townships WHERE surname LIKE ? OR forename LIKE ?',
                   ('%' + search_term + '%', '%' + search_term + '%'))
    results_count = cursor.fetchone()[0]  # Get the total number of results

    # Pagination logic
    next_record = page + 1 if page * 10 < results_count else None
    previous_record = page - 1 if page > 1 else None

    conn.close()  # Close the database connection

    return render_template('townships.html', records=records, results_count=results_count,
                           next_record=next_record, previous_record=previous_record)


@app.route('/memorials', methods=['GET', 'POST'])
def memorials():
    """Display and search memorial records."""
    conn = sqlite3.connect('bradford_ww1.db')
    cursor = conn.cursor()

    query = "SELECT * FROM memorials"  # Default query to fetch all records
    search_query = ''  # Initialize search query
    
    if request.method == 'POST':
        search_type = request.form.get('search_type')  # Get search type (e.g., surname, forename, etc.)
        search_query = request.form.get('search_query')  # Get the search query from the form

        # Modify the query based on the search type
        if search_type == 'surname':
            query = "SELECT * FROM memorials WHERE surname LIKE ?"
        elif search_type == 'forename':
            query = "SELECT * FROM memorials WHERE forename LIKE ?"
        elif search_type == 'memorial_location':
            query = "SELECT * FROM memorials WHERE memorial_location LIKE ?"

        cursor.execute(query, ('%' + search_query + '%',))  # Execute the query with the search term
    else:
        cursor.execute(query)  # If no search, fetch all records

    records = cursor.fetchall()  # Fetch all results from the query
    conn.close()

    return render_template('memorials.html', records=records)  # Render the memorials page with results


@app.route('/burials', methods=['GET', 'POST'])
def burials():
    """Display and search burial records."""
    if 'user' in session:  # Check if user is logged in
        conn = sqlite3.connect('bradford_ww1.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            search_term = request.form['search']
            cursor.execute("SELECT * FROM burials WHERE surname LIKE ? OR forename LIKE ?", ('%' + search_term + '%', '%' + search_term + '%'))
        else:
            cursor.execute("SELECT * FROM burials")
        
        records = cursor.fetchall()  # Fetch burial records
        conn.close()
        return render_template('burials.html', records=records)  # Render burials page with results
    return redirect(url_for('login'))  # Redirect to login page if user is not logged in


@app.route('/newspaper', methods=['GET', 'POST'])
def newspaper():
    """Display and search newspaper records."""
    if 'user' in session:  # Check if user is logged in
        conn = sqlite3.connect('bradford_ww1.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            search_term = request.form['search']
            cursor.execute("SELECT * FROM newspapers WHERE surname LIKE ? OR forename LIKE ?", ('%' + search_term + '%', '%' + search_term + '%'))
        else:
            cursor.execute("SELECT * FROM newspapers")
        
        records = cursor.fetchall()  # Fetch newspaper records
        conn.close()
        return render_template('newspaper.html', records=records)  # Render newspaper page with results
    return redirect(url_for('login'))  # Redirect to login page if user is not logged in


@app.route('/biographies', methods=['GET', 'POST'])
def biographies():
    """Display and search biography records."""
    if 'user' in session:  # Check if user is logged in
        conn = sqlite3.connect('bradford_ww1.db')
        cursor = conn.cursor()

        if request.method == 'POST':
            search_term = request.form['search']
            cursor.execute("SELECT * FROM biographies WHERE surname LIKE ? OR forename LIKE ?", ('%' + search_term + '%', '%' + search_term + '%'))
        else:
            cursor.execute("SELECT * FROM biographies")
        
        records = cursor.fetchall()  # Fetch biography records
        conn.close()
        return render_template('biographies.html', records=records)  # Render biographies page with results
    return redirect(url_for('login'))  # Redirect to login page if user is not logged in


if __name__ == '__main__':
    init_db()  # Initialize the database
    load_spreadsheets()  # Load data from spreadsheets into the database
    app.run(debug=True)  # Start the Flask application with debugging enabled