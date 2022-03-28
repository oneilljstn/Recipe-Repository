import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, url_for, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from helpers import apology, login_required
from datetime import timedelta, datetime

# Global variables
UPLOAD_FOLDER = './recipe_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///recipes.db")



@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    name = db.execute(
        "SELECT full_name FROM users WHERE id = ?",
        1)

    # Render recipe grid view
    recipes = db.execute("SELECT name, image, id FROM recipes")
    for row in recipes:
        ingredients = db.execute("SELECT name FROM ingredients WHERE recipe_id = ?", row["id"] )
        steps = db.execute("SELECT step FROM steps WHERE recipe_id = ?", row["id"] )
        tmp_list = []
        for i in ingredients:
            tmp_list.append(i["name"])
        row["ingredients"] = tmp_list
        tmp_list = []
        for s in steps:
            tmp_list.append(s["step"])
        row["steps"] = tmp_list
        print(row)
    

    return render_template("index.html", recipes=recipes, name=name[0]["full_name"])



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


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Redirect to registration page
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":

      # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password was submitted
        elif not request.form.get("fullname"):
            return apology("must provide name", 400)    

        # Ensure confirmation password was submitted
        elif not request.form.get("confirmation"):
            return apology("must confrim password", 400)

         # Ensure confirmation password match
        elif not (request.form.get("confirmation") == request.form.get("password")):
            return apology("passwords must match", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?",
            request.form.get("username"))
        if len(rows) > 0:
            return apology("Username taken")

        # Passess all check -> add user to db
        uname = request.form.get("username")
        pw_hash = generate_password_hash(request.form.get("password"))
        fullname = request.form.get("fullname")
        db.execute(
            "INSERT INTO users (username, hash, full_name) VALUES (?, ?, ?)"
            , uname, pw_hash, fullname)

        return logout()


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():

    """Add new recipe user"""
    if request.method == "GET":
        return render_template("add.html")

    # Variables from form 
    if (    not request.form.get("recipe_name") or
            not request.form.get("duration_h") or 
            not request.form.get("duration_m") or 
            not request.form.get("meal_type") or 
            # not request.form.get("carbs") or
            # not request.form.get("protein") or 
            # not request.form.get("fat") or 
            # not request.form.get("calories") or 
            not request.form.get("ingredients") or 
            not request.form.get("steps")
        ):
        return apology("Form Error, please fill out again")

    recipe_name = str(request.form.get("recipe_name"))    
    if len(db.execute("SELECT id FROM recipes WHERE name = ?", recipe_name)) > 0:
        return apology("Recipe with that name already exists")

    recipe_name = str(request.form.get("recipe_name"))
    image_url = upload_file('image')
    duration_h = int(request.form.get("duration_h"))
    duration_m = int(request.form.get("duration_m"))
    meal_type = request.form.get("meal_type")
    # Nutritional information removed - TODO readd later
    # carbs = int(request.form.get("carbs"))
    # protein = int(request.form.get("protein"))
    # fat = int(request.form.get("fat"))
    # calories = int(request.form.get("calories"))
    ingredients = request.form.get("ingredients").splitlines()
    steps = request.form.get("steps").splitlines()
    

    # TODO Scrap serving info - not important
    serving_size = 0
    servings = 0

    # Form validation
     
    # TODO Redo these usign Flask WTForm validation
    if recipe_name is None or recipe_name == "":
         return apology("Please enter a recipe name")
    if duration_h < 0:
          return apology("Duration_h must be positive")
    if duration_m < 0:
          return apology("Duration_m must be positive")

    if meal_type not in {'Breakfast', 'Lunch/Dinner', 'Dessert', 'Other'}:
        return apology("Invalid meal type")
    # if carbs < 0 or protein < 0 or fat < 0 or calories < 0:
    #     return apology("Nutritional info cannot be negative")
    
    # Insert into Recipe table
    db.execute(
        "INSERT INTO recipes (user_id, name, meal, duration, image) VALUES (?, ?, ?, ?, ?)"
        , session["user_id"], recipe_name, meal_type, convert_time(duration_h, duration_m), image_url)

    recipe_id = db.execute(
        "SELECT id FROM recipes WHERE name = ? LIMIT 1",
         recipe_name)[0]['id']
    # Insert into nutrition table
    # db.execute(
    #     "INSERT INTO nutrition (recipe_id, calories, protein, carbohydrates, fat) VALUES (?, ?, ?, ?, ?)"
    #     , recipe_id, calories, protein, carbs, fat)     
    # Insert into ingredients table
    for i in get_ingredients(ingredients, recipe_id):
        db.execute(
        "INSERT INTO ingredients (recipe_id, name) VALUES (?, ?)", 
        i['id'], i['ing']
    )
    # Insert into steps table
    for s in get_steps(steps, recipe_id):
        db.execute(
        "INSERT INTO steps (recipe_id, step) VALUES (?, ?)", 
        s['id'], s['step']
    )

    return redirect("/")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    # TODO Implement Search 
    if request.method == "GET":
        return render_template("/search.html")

    # Get search query
    if not request.form.get("query"):
        query = ''
    query = str(request.form.get("query"))
    # DB select
    recipes = db.execute("SELECT name, image, id FROM recipes WHERE name CONTAINS ?", query)
    for row in recipes:
        ingredients = db.execute("SELECT name FROM ingredients WHERE recipe_id = ?", row["id"] )
        steps = db.execute("SELECT step FROM steps WHERE recipe_id = ?", row["id"] )
        tmp_list = []
        for i in ingredients:
            tmp_list.append(i["name"])
        row["ingredients"] = tmp_list
        tmp_list = []
        for s in steps:
            tmp_list.append(s["step"])
        row["steps"] = tmp_list
        print(row)
    

    return render_template("search.html", recipes=recipes, name=name[0]["full_name"])

    # render template with variables

# route for searching recipes by name
@app.route("/filter")
def filter():
    q = request.args.get("q")
    if q:
        recipes = db.execute("SELECT id, name, image FROM recipes WHERE name LIKE ? LIMIT 50", "%" + q + "%")
    else:
        recipes = []
    return jsonify(recipes)  

# Route for searching recipes by ingredient
@app.route("/filter_ingredients")
def filter_ingredients():
    q = request.args.get("q")
    if q:
        recipes = db.execute("SELECT recipes.id, recipes.name, recipes.image FROM recipes INNER JOIN ingredients ON recipes.id = ingredients.recipe_id WHERE ingredients.name like ? GROUP BY recipes.name LIMIT 50", "%" + q + "%")
    else:
        recipes = []
    return jsonify(recipes)    


@app.route("/plan", methods=["GET", "POST"])
@login_required
def plan():
    # TODO Implement plan 
    
    return apology("COMING SOON")


# Function ensures filenames are safe to store when user uploads recipe images
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Saves images to folder '/recipe_images'
def upload_file(file_name):
    if request.method == 'POST':
        # check if the post request has the file part
        if file_name not in request.files:
            return apology("no image")
        file = request.files[file_name]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            return apology("no image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            print(file)
            print(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
            return (url_for('download_file', name=filename))

# Allows for the viewing of images uploaded to server
@app.route('/uploads/<name>')
@login_required
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)
    
# Strips empty ingredients from list before saving - work around for text field input
def get_ingredients(ingredients, recipe_id):
    new_list = []
    for ingredient in ingredients:
        if not ingredient or not ingredient.isspace():
            new_list.append({'id':recipe_id, 'ing':ingredient})
    return new_list

# Strips empty steps from list before saving - work around for text field input
def get_steps(steps, recipe_id):
    new_list = []
    for step in steps:
        if not step or not step.isspace():
            new_list.append({'id':recipe_id, 'step':step})
    return new_list