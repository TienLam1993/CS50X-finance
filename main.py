import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db_url = os.environ.get('DATABASE_URL')

db = SQL(db_url)

# for sqlite version
# db.execute('CREATE TABLE IF NOT EXISTS transactions ( id INTEGER, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, share INTEGER NOT NULL, price NUMERIC NOT NULL, type TEXT NOT NULL, time TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id), PRIMARY KEY(id))')


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    data1 = db.execute(
        'SELECT SUM(share), symbol FROM transactions WHERE user_id = ? GROUP BY symbol ORDER BY symbol', session['user_id'])
    price = []
    total = []
    length = len(data1)
    for i in range(length):
        price.append(usd(float(lookup(data1[i]['symbol'])['price'])))
        total.append(usd(float(lookup(data1[i]['symbol'])['price']) * float(data1[i]['sum'])))

    cash = usd(float(db.execute('SELECT cash FROM users WHERE id = ?', session['user_id'])[0]['cash']))
    return render_template('index.html', data=data1, price=price, total=total, length=length, cash=cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == 'POST':

        symbol = request.form.get('symbol').upper()
        share = request.form.get('shares')
        
        if share.isnumeric():
            number = int(share)
        else:
            return apology('Invalid share')

        if lookup(symbol) == None:
            return apology('Invalid symbol')

        cash = db.execute('SELECT cash FROM users WHERE id = ?', session['user_id'])[0]['cash']
        price = lookup(symbol)['price']

        if cash < number * price:
            return apology('Not enough cash')
        else:
            db.execute('UPDATE users SET cash = ? WHERE id = ?', cash - number * price, session['user_id'])
            db.execute('INSERT INTO transactions (user_id, symbol, share, price, type, time) VALUES(?, ?, ?, ?, ?, ?)',
                       session['user_id'], symbol, number, price, 'buy', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

            flash('Bought!')
            return redirect('/')

    else:
        return render_template('buy.html')


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    data1 = db.execute('SELECT symbol, share, price, time FROM transactions WHERE user_id = ?', session['user_id'])

    return render_template('history.html', data=data1)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == 'POST':

        symbol = request.form.get('symbol')
    
        if lookup(symbol) == None:
            return apology('Invalid Symbol')
        else:
            name = lookup(symbol)['name']
            price = lookup(symbol)['price']
            # assign value of varible name and price in temple to variable name and price in .py
            return render_template('quoted.html', name=name, price=usd(price)) 

    else:
        return render_template('quote.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == 'POST':

        nametable = db.execute('SELECT username FROM users')
        name = request.form.get('username')
        
        namelist = []
        for i in range(len(nametable)):
            namelist.append(nametable[i]['username'])

        if not name or name in namelist:
            return apology('Invalid username or username already exists')

        password = request.form.get('password')
        confirmation = request.form.get('confirmation')
        if not password or not confirmation or password != confirmation:
            return apology('Invalid password or password not match')

        if (db.execute('INSERT INTO users (username, hash) VALUES(?, ?)', name, generate_password_hash(password))):
            flash('Successful registed! Please log in!')
            return redirect('login')

    else:
        return render_template('register.html') # method == GET


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    data1 = db.execute(
        'SELECT SUM(share), symbol FROM transactions WHERE user_id = ? GROUP BY symbol ORDER BY symbol', session['user_id'])

    symbols = []
    shares = []
    length = len(data1)
    for i in range(length):
        symbols.append(data1[i]['symbol'])
        shares.append(int(data1[i]['sum']))

    cash = float(db.execute('SELECT cash FROM users WHERE id = ?', session['user_id'])[0]['cash'])

    if request.method == 'POST':
        symbol = request.form.get('symbol')
        share = int(request.form.get('shares'))
        price = lookup(symbol)['price']

        # share avaiable
        for i in range(length):
            if symbols[i] == symbol:
                share1 = shares[i]

        if not symbol or symbol not in symbols:
            return apology('Invalid symbol')

        if share <= 0 or share > share1:
            return apology('Invalid share')

        # update database
        now = datetime.now()
        db.execute('UPDATE users SET cash = ? WHERE id = ?', cash + share * price, session['user_id'])
        db.execute('INSERT INTO transactions (user_id, symbol, share, price, type, time) VALUES(?, ?, ?, ?, ?, ?)',
                   session['user_id'], symbol, - share, price, 'sell', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

        flash('Sold!')
        return redirect('/')

    else:
        return render_template('sell.html', symbols=symbols, length=length)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
