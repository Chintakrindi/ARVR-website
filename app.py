import os
import uuid

from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

import cloudinary
import cloudinary.uploader

# ===============================
# LOAD ENV VARIABLES
# ===============================

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

# ===============================
# DATABASE CONFIG
# ===============================

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1
        )

else:
    DATABASE_URL = "sqlite:///local.db"

print("DATABASE_URL =", DATABASE_URL)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}

db = SQLAlchemy(app)


# ===============================
# DATABASE INIT
# ===============================

with app.app_context():

    try:

        db.session.execute(text("SELECT 1"))

        print("DATABASE CONNECTED")

        db.create_all()

        print("TABLES CREATED")

    except Exception as e:

        print("DATABASE ERROR:", str(e))

# ===============================
# DASHBOARD
# ===============================

@app.route("/")
def dashboard():

    try:

        projects = Project.query.order_by(
            Project.id.desc()
        ).all()

    except Exception as e:

        return f"""
        <h2>Database Error</h2>
        <pre>{str(e)}</pre>
        """

    return render_template(
        "dashboard.html",
        projects=projects
    )

# ===============================
# CREATE PROJECT PAGE
# ===============================

@app.route("/create")
def create_project():

    if not session.get("create_auth"):

        return render_template(
            "pin_login.html",
            next_page="/create"
        )

    return render_template("create_project.html")

# ===============================
# VERIFY PIN
# ===============================

@app.route("/verify-pin", methods=["POST"])
def verify_pin():

    pin = request.form.get("pin")
    next_page = request.form.get("next_page")

    if pin == ADMIN_PIN:

        session["create_auth"] = True

        return redirect(next_page)

    return render_template(
        "pin_login.html",
        error="Wrong PIN",
        next_page=next_page
    )

# ===============================
# IMAGE AR VIEW
# ===============================

@app.route("/image-ar/<int:project_id>")
def image_ar(project_id):

    project = Project.query.get_or_404(project_id)

    return render_template(
        "image_ar.html",
        project=project
    )

# ===============================
# MODEL AR VIEW
# ===============================

@app.route("/model-ar/<int:project_id>")
def model_ar(project_id):

    project = Project.query.get_or_404(project_id)

    return render_template(
        "model_ar.html",
        project=project
    )

# ===============================
# SAVE PROJECT
# ===============================

@app.route("/save", methods=["POST"])
def save():

    file = request.files.get("file")

    name = request.form.get("name")

    ptype = request.form.get("type")

    if not file:
        return "No file selected", 400

    public_id = str(uuid.uuid4())

    upload = cloudinary.uploader.upload(
        file,
        public_id=public_id,
        resource_type="auto"
    )

    project = Project(
        name=name,
        file_url=upload["secure_url"],
        public_id=public_id,
        type=ptype
    )

    db.session.add(project)
    db.session.commit()

    return redirect("/")

# ===============================
# DELETE PROJECT
# ===============================

@app.route("/delete/<int:id>")
def delete_project(id):

    project = Project.query.get_or_404(id)

    try:
        cloudinary.uploader.destroy(
            project.public_id,
            resource_type="image"
        )
    except:
        pass

    db.session.delete(project)
    db.session.commit()

    return redirect("/")

# ===============================
# LOGOUT
# ===============================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# ===============================
# WALL AR PAGE
# ===============================

@app.route("/wall-ar")
def wall_ar():

    return render_template("wall_ar.html")

# ===============================
# HEALTH CHECK
# ===============================

@app.route("/health")
def health():

    try:
        db.session.execute(text("SELECT 1"))
        return "Database Connected"

    except Exception as e:
        return f"Database Error: {str(e)}", 500

# ===============================
# RUN SERVER
# ===============================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
