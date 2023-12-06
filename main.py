from flask import Flask, redirect, url_for, render_template, request, session, flash
import aiohttp
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from flask_bcrypt import Bcrypt


app = Flask(__name__)
app.secret_key = "server"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(days = 5)
bcrypt = Bcrypt(app)

db = SQLAlchemy(app)

class Users(db.Model):
  id = db.Column(db.Integer, primary_key = True)
  email = db.Column(db.String(100), unique=True)
  password = db.Column(db.String(100))
  username = db.Column(db.String(15), unique=True)
  attending = db.Column(db.String)

  def __init__(self, email, password, username, attending):
    self.email = email
    self.password = password
    self.username = username
    self.attending = attending

def create_tables():
  with app.app_context():
    db.create_all()

apiUrl = "https://new-york-events-66105853a688.herokuapp.com/get-all-events"

@app.route("/")
def home():
    return render_template("home.html")

#display universal homepage
async def fetch(url):
   async with aiohttp.ClientSession() as session:
      async with session.get(url) as response:
         return await response.json()

@app.route("/apphome")
async def apphome():
    if session["logged_in"]:
       user_id = session.get("user_id")
       user = Users.query.get(user_id)
       content = await fetch(apiUrl)
       return render_template("apphome.html", userInfo=user, data=content)
    else: 
      return redirect(url_for("login"))

@app.route("/user/<username>")
async def user(username):

   if session["logged_in"]:
    eventList = await fetch(apiUrl)
    userId = session.get("user_id")
    userAttending = []
    userLoggedIn = Users.query.get(userId)
    user = Users.query.filter_by(username=username).first()
    if user:
       for event in eventList:
          if event["name"] in user.attending:
             userAttending.append(event)
       return render_template("user.html", userInfo=user, userAttending=userAttending, userLoggedIn=userLoggedIn)

    return render_template("user.html", user=user, userLoggedIn = userLoggedIn)

      
    
@app.route("/event/<name>", methods=["POST", "GET"])
async def event(name):
    if session["logged_in"]:
        url = "https://new-york-events-66105853a688.herokuapp.com/get-event/" + name
        data = await fetch(url)
        user_id = session.get("user_id")
        user = Users.query.get(user_id)
        if request.method == "POST":
            if data['name'] in user.attending:
                user.attending = user.attending.replace(data["name"], "")
                db.session.commit()          
                return redirect(url_for("event", name=name))
            else:
                user.attending += data['name']
                db.session.commit()        
                return redirect(url_for("event", name=name))
        else:
          all_attending = Users.query.filter(Users.attending.ilike(f"%{data['name']}%")).all()
          return render_template("event.html", event=data, userInfo=user, attending=all_attending) 
    else: 
      return redirect(url_for("login"))



@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
       password = request.form["password"]
       email = request.form["email"]
       user = Users.query.filter_by(email=email).first()
       if user and bcrypt.check_password_hash(user.password, password):
          session["user_id"] = user.id
          session["logged_in"] = True
          return redirect(url_for("apphome"))
       else:
          flash("Wrong password")
          redirect(url_for("login"))
    else: 
      return render_template("login.html")

@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        username = request.form["username"]
        session["user"] = username
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        attending = "None"
        createdUser = Users(email=email, password=hashed_password, username=username, attending=attending)
        db.session.add(createdUser)
        try:
            db.session.commit()
        except exc.IntegrityError as e:
            db.session.rollback()
            flash("Your username and/or email in not unique")
            return redirect(url_for("signup"))
        return redirect(url_for("login"))
    else:
        return render_template("signup.html")

@app.route("/logout")
def logout():
   return redirect(url_for("login"))

if __name__ == "__main__":
    create_tables()
    app.run(port=8000, debug=True)