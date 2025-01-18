from flask import Flask,request, render_template, redirect, session, url_for, Response, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from datetime import datetime
import csv
import os

EXPENSE_FILE = 'Expenses.csv'

app =Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_key_for_dev")
app.config['MYSQL_HOST'] = 'localhost' 
app.config['MY_USER'] = 'Riyazul Arfaat'
app.config['MYSQL_PASSWORD'] = 'Arfaath@dataBase.296'
app.config['MYSQL_DB'] = 'personal_finance_manager'

mysql = MySQL(app)


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/sign_up', methods=['GET','POST'])
def sign_up():
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form and 'mobile' in request.form and 'username' in request.form and 'password' in request.form:
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        username = request.form['username']
        pwd = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()
        if account:
            message ='Account already exists!'
            return render_template('sign_up.html', message=message)
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
            return render_template('sign_up.html', message=message)
        elif not re.match(r'[A-Za-z0-9]+', username):
            message = 'Username must contain only characters and numbers!'
            return render_template('sign_up.html', message=message)
        elif not name or not email or not mobile or not username or not pwd:
            message = 'Please fill out the form!'
            return render_template('sign_up.html', message=message)
        else:
            cursor.execute('INSERT INTO users VALUES (NULL, %s, %s, %s, %s, %s)', (name, username, email, mobile, pwd))
            mysql.connection.commit()
            message = 'Account created successfully!'  
        return redirect('/login')
    else:
        message = 'Please fill out the form!'
    return render_template('sign_up.html', message=message)

@app.route('/login', methods=['GET', 'POST'])    
def login():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        pwd = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s AND pwd = %s', (username, pwd, ))
        user = cursor.fetchone()
        if user:
            session['loggedin'] = True
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['mobile'] = user['mobile']
            session['username'] = user['username']
            session['password'] = user['pwd']
            return redirect('/home_page')
        else:
            return render_template('login.html', error='Invalid username or password') 
    return render_template('login.html')

@app.route('/home_page')
def home_page():
    if 'username' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM users WHERE username = %s", (session['username'],))
        user = cursor.fetchone()

        if user:
            user_id = user['user_id']  
            selected_month = request.args.get('month', None)

            if selected_month:
                try:
                    selected_month = int(selected_month)
                    if selected_month < 1 or selected_month > 12:
                        raise ValueError("Invalid month selected.")
                except ValueError:
                    selected_month = None

            if selected_month:
                # Fetch the total expenses and incomes for the selected month
                cursor.execute("""
                    SELECT IFNULL(SUM(amount), 0) AS total_expenses 
                    FROM expenses 
                    WHERE user_id = %s 
                    AND MONTH(date) = %s
                """, (user_id, selected_month))
                total_expenses = cursor.fetchone()['total_expenses']

                cursor.execute("""
                    SELECT IFNULL(SUM(amount), 0) AS total_incomes 
                    FROM incomes 
                    WHERE user_id = %s 
                    AND MONTH(date) = %s
                """, (user_id, selected_month))
                total_incomes = cursor.fetchone()['total_incomes']

                # Calculate the total balance
                total_balance = total_incomes - total_expenses
            else:
                # Default to total for all months if no month is selected
                cursor.execute("""
                    SELECT IFNULL(SUM(amount), 0) AS total_expenses 
                    FROM expenses 
                    WHERE user_id = %s
                """, (user_id,))
                total_expenses = cursor.fetchone()['total_expenses']

                cursor.execute("""
                    SELECT IFNULL(SUM(amount), 0) AS total_incomes 
                    FROM incomes 
                    WHERE user_id = %s
                """, (user_id,))
                total_incomes = cursor.fetchone()['total_incomes']

                total_balance = total_incomes - total_expenses

            # Fetch monthly balances for the logged-in user
            cursor.execute("""
                SELECT DATE_FORMAT(expenses.date, '%%Y-%%m') AS month, 
                    SUM(expenses.amount) AS total_expenses,
                    SUM(COALESCE(incomes.amount, 0)) AS total_incomes
                FROM expenses 
                LEFT JOIN incomes 
                ON expenses.user_id = incomes.user_id 
                AND DATE_FORMAT(expenses.date, '%%Y-%%m') = DATE_FORMAT(incomes.date, '%%Y-%%m')
                WHERE expenses.user_id = %s 
                GROUP BY DATE_FORMAT(expenses.date, '%%Y-%%m')
                ORDER BY month;
            """, (user_id,))

            monthly_balances = cursor.fetchall()

            return render_template(
                'home_page.html',
                user=user,
                total_expenses=total_expenses,
                total_incomes=total_incomes,
                total_balance=total_balance,
                monthly_balances=monthly_balances,
                selected_month=selected_month
            )
        else:
            return redirect('/login') 
    else:
        return redirect('/login') 


@app.route('/download_report', methods=['GET'])
def download_report():
    if 'username' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch the logged-in user's details
        cursor.execute("SELECT * FROM users WHERE username = %s", (session['username'],))
        user = cursor.fetchone()

        if user:
            user_id = user['user_id']

            # Fetch financial data for the selected month
            selected_month = request.args.get('month', None)
            if selected_month:
                cursor.execute("""
                    SELECT 
                        DATE_FORMAT(date, '%%Y-%%m-%%d') AS date,
                        category,
                        amount,
                        'expense' AS type
                    FROM expenses
                    WHERE user_id = %s AND MONTH(date) = %s
                    UNION ALL
                    SELECT 
                        DATE_FORMAT(date, '%%Y-%%m-%%d') AS date,
                        category,
                        amount,
                        'income' AS type
                    FROM incomes
                    WHERE user_id = %s AND MONTH(date) = %s
                    ORDER BY date;
                """, (user_id, selected_month, user_id, selected_month))
                report_data = cursor.fetchall()
            else:
                return redirect(url_for('home_page'))

            # Generate a CSV file
            csv_file_path = f'report_{user["username"]}_month_{selected_month}.csv'
            with open(csv_file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Date', 'Category', 'Amount', 'Type'])
                for row in report_data:
                    writer.writerow([row['date'], row['category'], row['amount'], row['type']])

            # Send the CSV file as a response
            return Response(
                open(csv_file_path, 'r'),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={csv_file_path}'
                }
            )
        else:
            return redirect('/login')
    else:
        return redirect('/login')


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect('/')

@app.route('/add', methods=['GET', 'POST'])
def add():
    return render_template('add.html')

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        date = request.form['date']
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO expenses VALUES (NULL, %s, %s, %s, %s, %s)', (date, amount, category, description, session['user_id']))
        mysql.connection.commit()
        flash("Expense is added successfully!", "success")

    return render_template('add.html')

@app.route('/add_income', methods=['GET', 'POST'])
def add_income():
    if request.method == 'POST':
        date = request.form['date']
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO incomes VALUES (NULL, %s, %s, %s, %s, %s)', (date, amount, category, description, session['user_id']))
        mysql.connection.commit()
        flash("Expense is added successfully!", "success")

    return render_template('add.html')


@app.route('/view', methods=['GET', 'POST'])
def view():
    expenses = []
    if request.method == 'POST':
        view_type = request.form['type']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if view_type == 'expense':
            cursor.execute('SELECT * FROM expenses WHERE user_id = %s', (session['user_id'],))
        else:
            cursor.execute('SELECT * FROM incomes WHERE user_id = %s', (session['user_id'],))
        expenses = cursor.fetchall()
    return render_template('view.html', expenses=expenses)

@app.route('/delete', methods=['GET', 'POST'])
def delete_expense():
    if request.method == 'POST':
        search_type = request.form['search_type']
        search_term = request.form['search_term']
        results_found = False
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM expenses WHERE user_id = %s', (session['user_id'],))
        expenses = cursor.fetchall()
        for expense in expenses:
            if (search_type == 'date' and expense['date'] == search_term) or (search_type == 'category' and expense['category'].lower() == search_term.lower()):
                cursor.execute('DELETE FROM expenses WHERE exp_id = %s', (expense['exp_id'],))
                mysql.connection.commit()
                results_found = True
        if results_found:
            message = f"Expenses with {search_type} '{search_term}' deleted successfully."
        else:
            message = f"No expenses found with {search_type} '{search_term}'."
        return render_template('delete.html', message=message)
    return render_template('delete.html')

@app.route('/update', methods=['GET', 'POST'])
def update_records():
    if 'username' in session:  # Ensure the user is logged in
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        if request.method == 'POST':
            # Handle form submission
            record_type = request.form.get('record_type')  # 'income' or 'expense'
            record_id = request.form.get('record_id')
            column_to_update = request.form.get('column')
            new_value = request.form.get('value')

            # Validate inputs
            if not (record_type and record_id and column_to_update and new_value):
                return render_template('update.html', error="All fields are required!", records=[])

            # Determine table and ID column dynamically
            table = 'incomes' if record_type == 'income' else 'expenses'
            id_column = 'inc_id' if record_type == 'income' else 'exp_id'

            try:
                # Update the record using a parameterized query
                query = f"UPDATE {table} SET {column_to_update} = %s WHERE {id_column} = %s AND user_id = %s"
                cursor.execute(query, (new_value, record_id, session['user_id']))
                mysql.connection.commit()

                success_message = f"{record_type.capitalize()} record updated successfully!"
                return render_template('update.html', success=success_message, records=fetch_all_records(cursor, session['user_id']))
            except Exception as e:
                print(f"Error updating record: {e}")
                return render_template('update.html', error="An error occurred while updating the record.", records=[])

        else:
            # Fetch all records (both incomes and expenses)
            records = fetch_all_records(cursor, session['user_id'])
            return render_template('update.html', records=records)

    else:
        return redirect('/login')  # Redirect to login if the user is not logged in


def fetch_all_records(cursor, user_id):
    """Fetch all income and expense records for the logged-in user."""
    cursor.execute("SELECT 'income' AS type, inc_id AS id, amount, description, category, date FROM incomes WHERE user_id = %s", (user_id,))
    incomes = cursor.fetchall()

    cursor.execute("SELECT 'expense' AS type, exp_id AS id, amount, description, category, date FROM expenses WHERE user_id = %s", (user_id,))
    expenses = cursor.fetchall()

    return incomes + expenses



@app.route('/support', methods=['GET', 'POST'])
def support():
    return render_template('support.html')

if __name__ == '__main__':
    app.run(debug=True)
