from flask import Flask,request, render_template, redirect, session, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt
import csv
from flask import flash
import os

EXPENSE_FILE = 'Expenses.csv'

app =Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = 'c231296'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, name, email, mobile, username, password):
        self.name = name
        self.email = email
        self.mobile = mobile
        self.username = username
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
with app.app_context():
    db.create_all()
    
def read_expenses():
    expenses = []
    for file_name in os.listdir('.'):  # Assume CSV files are in the current directory
        if file_name.endswith('.csv') and 'Expenses' in file_name:
            with open(file_name, 'r') as file:
                reader = csv.DictReader(file)
                expenses.extend(list(reader))
    return expenses


def write_expenses(expenses):
    with open(EXPENSE_FILE, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['date', 'amount', 'category', 'description'])
        writer.writeheader()
        writer.writerows(expenses)
   
def update_expense(search_type, search_term, new_data):
    expenses = read_expenses()
    updated = False
    for expense in expenses:
        if (search_type == 'date' and expense['date'] == search_term) or \
           (search_type == 'category' and expense['category'].lower() == search_term.lower()):
            expense.update(new_data)
            updated = True
    if updated:
        write_expenses(expenses)
    return updated

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/sign_up', methods=['GET','POST'])
def sign_up():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        username = request.form['username']
        password = request.form['password']
        new_user = User(name=name, email=email, mobile=mobile, username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
        
    return render_template('sign_up.html')

@app.route('/login', methods=['GET', 'POST'])    
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['name'] = user.name
            session['email'] = user.email
            session['mobile'] = user.mobile
            session['username'] = user.username
            return redirect('/home_page')
        else:
            return render_template('login.html', error='Invalid username or password') 
    return render_template('login.html')

@app.route('/home_page')
def home_page():
    if session['username']:
        user = User.query.filter_by(username=session['username']).first()
        return render_template('home_page.html', user=user)
    else:
        return redirect('/login')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        date = request.form['date']
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']

        # Save expense to the file
        with open(EXPENSE_FILE, 'a') as file:
            file.write(f"{date},{amount},{category},{description}\n")
        
        flash("Expense added successfully!", "success")
        return redirect(url_for('home_page'))

    return render_template('add.html')


@app.route('/view', methods=['GET', 'POST'])
def view():
    expenses = []
    with open(EXPENSE_FILE, 'r') as file:
        for line in file:
            try:
                date, amount, category, description = line.strip().split(',')
                expenses.append({
                    'date': date,
                    'amount': amount,
                    'category': category,
                    'description': description
                })
                
            except ValueError:
                # If any line has an invalid format, skip it
                print(f"Skipping invalid entry: {line.strip()}")
    return render_template('view.html', expenses=expenses)


@app.route('/delete', methods=['GET', 'POST'])
def delete():
    if request.method == 'POST':
        search_type = request.form['search_type']
        search_term = request.form['search_term']
        results_found = False
        
        try:
            with open(EXPENSE_FILE, 'r') as file:
                expenses = file.readlines()
            
            with open(EXPENSE_FILE, 'w') as file:
                for expense in expenses:
                    date, amount, category, description = expense.strip().split(',')
                    if (search_type == 'date' and date == search_term) or \
                       (search_type == 'category' and category.lower() == search_term.lower()):
                        results_found = True
                        continue
                    file.write(expense)
            
            if results_found:
                flash("Expense deleted successfully!", "success")
            else:
                flash("No matching expense found to delete.", "error")
        except FileNotFoundError:
            flash("No expenses found to delete.", "error")
        return redirect(url_for('home_page'))
    return render_template('delete.html')

@app.route('/search', methods=['GET', 'POST'])
def search_expenses():
    if request.method == 'POST':
        search_type = request.form['search_type']
        search_term = request.form['search_term']
        expenses = read_expenses()
        filtered_expenses = [
            expense for expense in expenses 
            if (search_type == 'date' and expense['date'] == search_term) or
               (search_type == 'category' and expense['category'].lower() == search_term.lower())
        ]
        return render_template('search.html', expenses=filtered_expenses, searched=True)

 
    return render_template('search.html', searched=False)

@app.route('/total', methods=['GET', 'POST'])
def calculate_total():
    total = 0
    expenses = []

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        try:
            # Parse the input dates to datetime objects
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')

            # Read and calculate total from the file
            try:
                with open(EXPENSE_FILE, 'r') as file:
                    for line in file:
                        try:
                            date, amount, category, description = line.strip().split(',')
                            
                            # Parse the date from the file
                            expense_date_obj = datetime.strptime(date, '%Y-%m-%d')
                            
                            # Check if the expense falls within the date range
                            if start_date_obj <= expense_date_obj <= end_date_obj:
                                total += float(amount)  # Add amount to total
                                expenses.append({
                                    'date': date,
                                    'amount': amount,
                                    'category': category,
                                    'description': description
                                })
                        except ValueError:
                            # If any line has an invalid format, skip it
                            print(f"Skipping invalid entry: {line.strip()}")

                if not expenses:
                    flash(f"No expenses found in the specified date range.", "error")
                else:
                    flash(f"Total expenses from {start_date} to {end_date}: {total}", "success")

            except FileNotFoundError:
                flash("No expenses found. Please add expenses first.", "error")
            except ValueError as e:
                flash(f"Error in file data: {e}. Please check your file format.", "error")

        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD for start and end dates.", "error")

        return render_template('total.html', expenses=expenses, total=total)

    return render_template('total.html', expenses=expenses, total=total)

@app.route('/support', methods=['GET', 'POST'])
def support():
    return render_template('support.html')

if __name__ == '__main__':
    app.run(debug=True)
