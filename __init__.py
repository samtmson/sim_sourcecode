from datetime import datetime, timedelta, date
from flask import Flask, request, url_for, redirect, render_template, session, escape, flash, jsonify
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from yahoo_fin.stock_info import get_live_price
import math
import base64
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import requests
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io
import matplotlib.ticker as ticker

app = Flask(__name__)
app.secret_key = "jkn&*DCSov?cin%&3%IBYCEZ"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/SMS.db'
app.config["SQLALCTEHMY_TRACK_MODIFICATIONS"] = False

companyname = {"aapl":"Apple","adbe":"Adobe","amzn":"Amazon","atvi":"Activision Blizzard","cmcsa":"Comcast","cost":"Costco","csco":"Cisco Systems","ebay":"Ebay","fb":"Facebook","fox":"Fox","googl":"Google","has":"Hasbro","intc":"Intel","msft":"Microsoft","nflx":"Netflix","pep":"Pepsi","pypl":"Paypal","sbux":"Starbux","tmus":"T-mobile","tsla":"Tesla",}
db = SQLAlchemy(app)

class tbl_userdata(db.Model):
    username = db.Column(db.String, primary_key = True)
    name  = db.Column(db.String)
    password = db.Column(db.String)
    question = db.Column(db.String)
    balance = db.Column(db.Float)

    def __init__(self, username, name, password, question, balance):
        self.username = username
        self.name = name
        self.password = password
        self.question = question
        self.balance = balance


def dictionary_factory(cursor, row):
    dictionary = {}
    for i, col in enumerate(cursor.description):
        dictionary[col[0]] = row[i]
    return dictionary

connection = sqlite3.connect("SMS.db")
connection.row_factory = dictionary_factory
cursor = connection.cursor()

class user:
    def __init__(self,username,date):
        self.username = username
        self.date = date

    def portfolio(self):
        connection = sqlite3.connect("SMS.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()

        username = self.username
        date = self.date

        command = "SELECT tbl_usershares.tickersymbol, tbl_companies.price, tbl_usershares.totalprice, tbl_usershares.numberofshares  FROM tbl_companies INNER JOIN tbl_usershares ON tbl_usershares.tickersymbol=tbl_companies.tickersymbol AND tbl_companies.date="
        command += "'" + date + "'"
        command += " AND tbl_usershares.username="
        command += "'" + username + "'"
        result = cursor.execute(command).fetchall()

        portfolio = []
        for row in result:
            tickersymbol = row.get("tickersymbol")
            tickersymbol = str(tickersymbol)
            name = companyname[tickersymbol]
            row["name"] = name
            row['tickersymbol'] = tickersymbol
            averageprice = row.get("totalprice")/row.get("numberofshares")
            change = ((row.get("price")-averageprice)/averageprice) * 100
            row["averageprice"] = averageprice
            row["change"] = change
            portfolio.append(row)
        return  portfolio

    def userdata(self):
        connection = sqlite3.connect("SMS.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()

        command = "SELECT name,balance,username FROM tbl_userdata WHERE username="
        command += "'" + self.username + "'"
        command = cursor.execute(command).fetchall()
        return command

class company:
    def __init__(self,tickersymbol,date):
        self.tickersymbol = tickersymbol
        self.date = date

    def getcurrentprice(self):
        connection = sqlite3.connect("SMS.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()

        command = "SELECT price FROM tbl_companies WHERE tickersymbol="
        command += "'" + self.tickersymbol + "'"
        command += " AND date="
        command += "'" + self.date + "'"
        print(command)
        print("--------------------")
        command = cursor.execute(command).fetchall()
        return command[0].get("price")

    def change(self):
        connection = sqlite3.connect("SMS.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()

        command = "SELECT price FROM tbl_companies WHERE tickersymbol="
        command += "'" + self.tickersymbol + "'"
        command += " AND date="
        command += "'" + self.date + "'"
        command = cursor.execute(command).fetchall()
        today = command[0].get("price")

        yesterdays = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
        command = "SELECT price FROM tbl_companies WHERE tickersymbol="
        command += "'" + self.tickersymbol + "'"
        command += " AND date="
        command += "'" + yesterdays + "'"
        command = cursor.execute(command).fetchall()
        yesterday = command[0].get("price")

        change = ((today - yesterday)/today) / 100
        change = round(change,5)
        change = str(change)
        if today > yesterday:
            change = "+" + change
        return change

    def deviation(self):
        connection = sqlite3.connect("SMS.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()

        numbers = []
        command = "SELECT price FROM tbl_companies WHERE tickersymbol="
        command += "'" + self.tickersymbol + "'"
        for row in cursor.execute(command):
            numbers.append(row.get("price"))
        mean = sum(numbers)/len(numbers)
        num = []
        for i in numbers:
            k = (i - mean)**2
            num.append(k)
        nummean = sum(num)/len(num)
        SD = math.sqrt(nummean)

        return SD

    def pointschange(self):
        connection = sqlite3.connect("SMS.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()

        command = "SELECT price FROM tbl_companies WHERE tickersymbol="
        command += "'" + self.tickersymbol + "'"
        command += " AND date="
        command += "'" + self.date + "'"
        command = cursor.execute(command).fetchall()
        today = command[0].get("price")

        yesterdays = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
        command = "SELECT price FROM tbl_companies WHERE tickersymbol="
        command += "'" + self.tickersymbol + "'"
        command += " AND date="
        command += "'" + yesterdays + "'"
        command = cursor.execute(command).fetchall()
        yesterday = command[0].get("price")

        points = today - yesterday
        points = str(points)
        if today > yesterday:
            points = "+" + points
        return points


def makegraph(var,flag):
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()
    fig = Figure()
    x = []
    y = []

    if flag == 0:
        xlabel = "Date"
        ylabel = "Share Price"
        results = "SELECT date, price FROM tbl_companies WHERE tickersymbol ="
        results += "'" + var + "'"
        results = cursor.execute(results).fetchall()
        var = var.upper()
        for i in results:
            a = i.get('date')
            b = i.get('price')
            x.append(a)
            y.append(b)
    else:
        xlabel = "Date"
        ylabel = "Balance"
        results = "SELECT date, balance FROM tbl_pastbalance WHERE username ="
        results += "'" + var + "'"
        results = cursor.execute(results).fetchall()
        for i in results:
            a = i.get('date')
            b = i.get('balance')
            x.append(a)
            y.append(b)
    axis = fig.add_subplot(1, 1, 1)
    axis.plot(x, y)
    axis.set_title(var)
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.xaxis.set_major_locator(ticker.MultipleLocator(30))
    axis.xaxis.set_minor_locator(ticker.MultipleLocator(30))

    pngImage = io.BytesIO()
    FigureCanvas(fig).print_png(pngImage)

    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')
    return pngImageB64String



@app.route("/")
def loginorsignup():
   return render_template("welcome.html")

@app.route('/login',methods=['GET','POST'])
def loginvariables():
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        #encryption--------------------------------------------
        password_provided = password
        password = password_provided.encode()
        salt = b'\xc6W\xf2xL\xd0.\xe0\x88\xdf\xfaj\x19\xce\xd66'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        password = base64.urlsafe_b64encode(kdf.derive(password)) #hashed password
        #encryption--------------------------------------------

        #checks if the username or the password are correct---------
        try:
            query = "SELECT username, password FROM tbl_userdata WHERE username="
            query += "'" + username + "'"
            query1 = cursor.execute(query).fetchall()
            username1 = query1[0].get("username")
            password1 = query1[0].get("password")
            if (username1 != username) or (password1 != password):
                flash(">username or password incorrect")
                return render_template("logintemp.html")


            session["username"] = username1
            return redirect(url_for("home"))
        except:
            flash(">username or password incorrect")
            return render_template("logintemp.html")
    else:
        return render_template("logintemp.html")



@app.route("/signup",methods=['GET','POST'])
def signupvariables():
    connection = sqlite3.connect("SMS.db")
    cursor = connection.cursor()

    if request.method == "POST":
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        question = request.form['question']


        #validate name-----------------------------
        if len(name) <= 0:
            flash(">you need to enter at least one character")
            return render_template("signuptemp.html")
        #validate password--------------------------
        if len(password) <= 5:
            flash(">password too short ")
            return render_template("signuptemp.html")

        if password != password2:
            flash(">passwords don't match")
            return render_template("signuptemp.html")

        #validate security question--------------------
        if len(question) <= 0:
            flash(">please enter at least one character for your mothers maiden name")
            return render_template("signuptemp.html")
        #encryption--------------------------------------------
        password_provided = password
        password = password_provided.encode()

        salt = b'\xc6W\xf2xL\xd0.\xe0\x88\xdf\xfaj\x19\xce\xd66'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        password = base64.urlsafe_b64encode(kdf.derive(password)) #hashed password


        #encryption--------------------------------------------

        #Error handlling Checks for presnce of username---------
        try:
            newuser = []
            newuser.append(username)
            newuser.append(name)
            newuser.append(password)
            newuser.append(question)
            newuser.append(25000.0)
            cursor.execute("INSERT INTO tbl_userdata VALUES (?,?,?,?,?)", newuser)
            connection.commit()

            session["username"] = username
            flash(">Welcome")
            return redirect(url_for('home'))
        except:
            flash(">Username taken")
            return render_template("signuptemp.html")

    return render_template("signuptemp.html")

@app.route("/forgotpassword",methods=['GET','POST'])
def forgotpassword():
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()


    if request.method == "POST":
        username = request.form['username']
        question = request.form['security']

        command = "SELECT username from tbl_userdata WHERE username="
        command += "'" + username + "'"
        command += " AND question="
        command += "'" + question + "'"

        command = cursor.execute(command).fetchall()
        print(command)
        if len(command) == 0:
            flash(">This username does not exist")
            return render_template("forgotpassword.html")

        session["username"] = username

        return redirect(url_for('changepassword'))
    return render_template("forgotpassword.html")



@app.route("/changepassword",methods=['GET','POST'])
def changepassword():
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()
    username = session["username"]
    if request.method == "POST":
        password= request.form['password']

        if len(password) <= 5:
            flash(">password too short ")
            return render_template("signuptemp.html")

        #encryption--------------------------------------------
        password_provided = password
        password = password_provided.encode()

        salt = b'\xc6W\xf2xL\xd0.\xe0\x88\xdf\xfaj\x19\xce\xd66'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        password = base64.urlsafe_b64encode(kdf.derive(password)) #hashed password


        #encryption--------------------------------------------
        command = "UPDATE tbl_userdata SET password="
        command += "'" + password + "'"
        command += " WHERE username="
        command += "'" + username + "'"
        print("-------")
        print(command)
        print("-------")
        cursor.execute(command)
        connection.commit()
        flash(">password changed")
        return render_template("welcome.html")
    return render_template("changepassword.html")

@app.route("/home",methods=['GET','POST'])
def home():
    today = datetime.today().strftime('%Y-%m-%d')

    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()

    if "username" in session:
        username = session['username']

        u = user(username,today)

        data = u.userdata()
        name =data[0].get("name")
        name = str(name)
        balance = data[0].get("balance")
        graph = makegraph(username,1)
        portfolio = u.portfolio()

        return render_template("home.html", name=name, balance=balance, portfolio=portfolio, image=graph)
    else:
        return redirect(url_for('loginorsignup'))

@app.route('/searchstocks',methods=["POST","GET"])
def searchstock():
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()
    today = datetime.today().strftime('%Y-%m-%d')

    if "username" in session:
        username = session["username"]

        if request.method == "POST":
            tickersymbol = request.form["firm"]
            tickersymbol_no_quotes = tickersymbol
            session["tickersymbol"] = tickersymbol
            session["tickersymbol0"] = tickersymbol_no_quotes
            return redirect(url_for('selectedcompany'))

        getcompanies = "SELECT tickersymbol, price FROM tbl_companies WHERE date="
        getcompanies += "'" + today + "'"
        getcompanies += "ORDER BY price DESC"
        companyname = {"aapl":"Apple","adbe":"Adobe","amzn":"Amazon","atvi":"Activision Blizzard","cmcsa":"Comcast","cost":"Costco","csco":"Cisco Systems","ebay":"Ebay","fb":"Facebook","fox":"Fox","googl":"Google","has":"Hasbro","intc":"Intel","msft":"Microsoft","nflx":"Netflix","pep":"Pepsi","pypl":"Paypal","sbux":"Starbux","tmus":"T-mobile","tsla":"Tesla",}
        companies = []
        for row in cursor.execute(getcompanies):
            i = row.get("tickersymbol")
            i = str(i)
            j = row.get("price")
            k = companyname[i]

            symbol = company(i,today)
            change = symbol.change()
            """
            turns each row into a dictionary
            (this makes it easier to construct a table dynamic in the front-end)
            """
            eachrow = dict(name = k,tickersymbol = i, price = j, change = change)
            companies.append(eachrow) #array of dictionaries
        return render_template("stockstemplate.html", companies = companies)


    return redirect(url_for('loginorsignup'))

@app.route('/selectedcompany',methods=["GET","POST"])
def selectedcompany():
    if "username" in session:
        username = session["username"]
        connection = sqlite3.connect("SMS.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()


        if request.method == "POST":
            option = request.form["choice"]
            if option == "Buy":
                return redirect(url_for("buy"))
            else:
                return redirect(url_for("sell"))

        if "tickersymbol" in session:
            tickersymbol = session["tickersymbol"]
            date = today = datetime.today().strftime('%Y-%m-%d')
            companyselected = company(tickersymbol,date)

            shareprice = companyselected.getcurrentprice()

            compname = companyname[tickersymbol]
            points = companyselected.pointschange()
            points = str(points)

            change = companyselected.change()
            t=tickersymbol
            ticker = tickersymbol.upper()
            SD = companyselected.deviation()
            graph = makegraph(tickersymbol,0)
            session["SD"] = SD
            session["ticker"] = ticker
            session["shareprice"] = shareprice
            session["change"] = change
            session["points"] = points
            return render_template("company.html", company=compname, tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD, image=graph)
    else:
        redirect(url_for('loginorsignup'))


@app.route("/buy",methods=["GET","POST"])
def buy():
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()
    #get working
    date = today = datetime.today().strftime('%Y-%m-%d')
    #needed to pevent '' from database
    username0 = session["username"]
    tickersymbol0 = session["tickersymbol0"]
    SD = session["SD"]
    ticker = session["ticker"]
    shareprice = session["shareprice"]
    change = session["change"]
    points = session["points"]

    if request.method == "POST":
        num_shares = request.form["numshares"]
        num_shares = int(num_shares)

        if num_shares <= 0:
            flash(">The entered number of shares must be a non 0 quantity")
            return render_template("buy.html", tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD)
        username = session["username"]
        u = user(username,date)
        balance = u.userdata()[0].get("balance")
        total = num_shares * shareprice
        if total > balance:
            flash("> The you do not have enough money to purchase these shares")
            return render_template("buy.html", tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD)

        new_balance = balance - total
        new_balance = str(new_balance)

        sharesdata = []
        sharesdata.append(username0)
        sharesdata.append(tickersymbol0)
        sharesdata.append(total)
        sharesdata.append(num_shares)
        command = "SELECT * FROM tbl_usershares WHERE username="
        command += "'" + username + "'"
        command += " AND tickersymbol="
        command +="'" + ticker.lower()+ "'"
        stocks_present = cursor.execute(command).fetchall()

        if len(stocks_present) == 0:
            cursor.execute("INSERT INTO tbl_usershares VALUES (?,?,?,?)",sharesdata)
            connection.commit()
            command = "UPDATE tbl_userdata SET balance="
            command += new_balance
            command += " WHERE username="
            command += "'" + username + "'"
            cursor.execute(command)
            connection.commit()
            #add the new balance to the table
            balance_change = []
            balance_change.append(username0)
            balance_change.append(new_balance)
            balance_change.append(date)
            cursor.execute("INSERT INTO tbl_pastbalance VALUES (?,?,?)",balance_change)
            connection.commit()
            flash(">you just bought stock!!")
            return redirect(url_for('home'))
        else:
            #this is what occurs if the user already owes shares in that company
            command = "SELECT numberofshares FROM tbl_usershares WHERE username="
            command += "'" + username + "'"
            command += " AND tickersymbol="
            command +="'" + ticker.lower()+ "'"
            numberofshares = cursor.execute(command).fetchall()
            numberofshares = numberofshares[0].get("numberofshares")
            #add the current number of shares to the requested number of shares
            shares_to_add = numberofshares + num_shares
            shares_to_add = str(shares_to_add)

            total = str(total)
            command = "UPDATE tbl_usershares SET numberofshares="
            command += shares_to_add
            command += " , totalprice="
            command += total
            command += " WHERE username="
            command += "'" + username + "'"
            command += " AND tickersymbol="
            command +="'" + ticker.lower()+ "'"
            cursor.execute(command)
            connection.commit()

            command = "UPDATE tbl_userdata SET balance="
            command += new_balance
            command += " WHERE username="
            command += "'" + username + "'"
            cursor.execute(command)
            connection.commit()

            balance_change = []
            balance_change.append(username0)
            balance_change.append(new_balance)
            balance_change.append(date)
            cursor.execute("INSERT INTO tbl_pastbalance VALUES (?,?,?)",balance_change)
            connection.commit()

            flash(">you just bought stock!!")
            return redirect(url_for('home'))
        return render_template("buy.html", tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD)
    else:
        return render_template("buy.html", tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD)

@app.route("/sell",methods=["GET","POST"])
def sell():
    date0 = today = datetime.today().strftime('%Y-%m-%d')
    username0 = session["username"]
    tickersymbol0 = session["tickersymbol0"]
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()
    SD = session["SD"]
    ticker = session["ticker"]
    shareprice = session["shareprice"]
    change = session["change"]
    points = session["points"]
    username = "'" + username0 + "'"
    tickersymbol = "'" + tickersymbol0 + "'"
    if request.method == "POST":
        num_shares = request.form["numshares"]
        num_shares = int(num_shares)
        if num_shares <= 0:
            flash(">The entered number of shares must be greater than 0")
            return render_template("sell.html",tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD)

        command = "SELECT numberofshares FROM tbl_usershares WHERE username="
        command += "'" + username0 + "'"
        command += " AND tickersymbol="
        command += "'" + tickersymbol0 + "'"
        command = cursor.execute(command).fetchall()
        if len(command) == 0:
            flash(">You do not own shares in this company")
            return render_template("sell.html", tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD)
        owned_shares = command[0].get("numberofshares")
        if owned_shares < num_shares:
            flash(">You do not own this many shares in this company")
            return render_template("sell.html",tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD)

        command = "SELECT price FROM tbl_companies WHERE tickersymbol="
        command +=  "'" + tickersymbol0 + "'"
        command += "AND date="
        command += "'" + date0 + "'"
        current_share_price = cursor.execute(command).fetchall()
        current_share_price = current_share_price[0].get("price")

        command = "SELECT balance FROM tbl_userdata WHERE username="
        command += "'" + username0 + "'"
        command = cursor.execute(command).fetchall()
        balance = command[0].get("balance")
        added_money = num_shares * current_share_price
        total_shares = owned_shares - num_shares
        new_balance = balance + added_money
        new_balance = str(new_balance)
        #change balance
        command = "UPDATE tbl_userdata SET balance="
        command += new_balance
        command += " WHERE username="
        command +=  username
        cursor.execute(command)
        connection.commit()

        #change total shares
        if total_shares > 0:
            total_shares = str(total_shares)
            command = "UPDATE tbl_usershares SET numberofshares="
            command += total_shares
            command += " WHERE username="
            command +=  username
            command += "AND tickersymbol="
            command += tickersymbol
            cursor.execute(command)
            connection.commit()
        else:
            command ="DELETE FROM tbl_usershares WHERE username="
            command += username
            command += " AND tickersymbol="
            command += tickersymbol
            cursor.execute(command)
            connection.commit()
        balance_change = []
        balance_change.append(username0)
        balance_change.append(new_balance)
        balance_change.append(date0)
        cursor.execute("INSERT INTO tbl_pastbalance VALUES (?,?,?)",balance_change)
        connection.commit()

        flash(">Shares sold")
        return redirect(url_for('home'))
    return render_template("sell.html", tickersymbol=ticker, shareprice=shareprice, change=change, points=points, SD=SD)

@app.route("/league")
def league():
    if "username" in session:
        username = session["username"]
        connection = sqlite3.connect("SMS.db")
        connection.row_factory = dictionary_factory
        cursor = connection.cursor()
        getusers = "SELECT username, balance FROM  tbl_userdata "
        getusers += "ORDER BY balance DESC"
        league = []
        for row in cursor.execute(getusers):
            i = row.get("username")
            i = str(i)
            j = row.get("balance")
            dictrow = dict(username=i, balance=j)
            league.append(dictrow)
        return render_template("league.html",league=league)
    return redirect(url_for('loginorsignup'))

@app.route("/api",methods = ["GET","POST"])
def api():
    return render_template("API.html")

#gets all share prices from todays date for selected company
@app.route("/api/<string:symbol>",methods = ["GET","POST"])
def today(symbol):
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()

    today = datetime.today().strftime('%Y-%m-%d')
    symbol = "'" + symbol + "'"
    today = "'" + today + "'"
    query = 'SELECT * FROM tbl_companies WHERE '
    query += 'date='+today+' AND '
    query += 'tickersymbol='+symbol
    sharesinfo = cursor.execute(query).fetchall()
    return jsonify(sharesinfo)

#get all share price data
@app.route("/api/all",methods = ["GET","POST"])
def all():
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()

    query = 'SELECT * FROM tbl_companies'
    restults = cursor.execute(query).fetchall()
    return jsonify(restults)

#gets all share prices from todays date for selected company
@app.route("/api/all/<string:symbol>",methods = ["GET","POST"])
def allcompany(symbol):
    connection = sqlite3.connect("SMS.db")
    connection.row_factory = dictionary_factory
    cursor = connection.cursor()

    today = datetime.today().strftime('%Y-%m-%d')
    symbol = "'" + symbol + "'"
    query = 'SELECT * FROM tbl_companies WHERE '
    query += 'tickersymbol='+symbol
    sharesinfo = cursor.execute(query).fetchall()
    return jsonify(sharesinfo)

@app.errorhandler(404)
def error(e):
    return '<h1>404</h1><p>Could not locate recource</p>', 404



@app.route("/logout")
def logout():
   session.pop('username',None)
   return redirect(url_for('loginorsignup'))


if __name__ == '__main__':
    flag = True
    todaydate = datetime.today().strftime('%Y-%m-%d')
    adddata = []
    companies = ["aapl","adbe","amzn","atvi","cmcsa","cost","csco","ebay","fb","fox","googl","has","intc","msft","nflx","pep","pypl","sbux","tmus","tsla"]
    command = "SELECT * from tbl_companies WHERE date="
    command += "'" + todaydate + "'"
    command = cursor.execute(command).fetchall()
    if len(command) == 0:
        for company in companies:
            adddata.append(company)
            #retrives the date
            adddata.append(todaydate)
            #retrives the live price
            price = get_live_price(company)
            price = round(price, 3)
            price = float(price)
            adddata.append(price)
            #adds the data to tbl_companies table
            cursor.execute("INSERT INTO tbl_companies VALUES (?,?,?)", adddata)
            connection.commit()
            print("just added data for "+company)
            adddata = []
    else:
        print("-------------")
        print("data already added")
        print("-------------")
    db.create_all()
    app.run(debug=True)
