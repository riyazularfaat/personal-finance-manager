from flask import Flask,request, render_template, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

app =Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Replace with your database URI
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
        
class Expenses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(100), nullable=False)

    def __init__(self, date, amount, category, description):
        self.date = date
        self.amount = amount
        self.category = category
        self.description = description
        
with app.app_context():
    db.create_all()

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
        new_expense = Expenses(date=date, amount=amount, category=category, description=description)
        db.session.add(new_expense)
        db.session.commit()
        return redirect('/home_page')
    return render_template('add.html')

@app.route('/view')
def view():
    expenses = Expenses.query.all()
    return render_template('view.html', expenses=expenses)

if __name__ == '__main__':
    app.run(debug=True)
