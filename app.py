import os
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

import cloudinary
import cloudinary.uploader

# ======================================
# LOAD ENV VARIABLES
# ======================================

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "change-this-secret"
)

ADMIN_PIN = os.getenv(
    "ADMIN_PIN",
    "1234"
)

# ======================================
# MYSQL DATABASE (XAMPP)
# ======================================

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_DB = os.getenv("MYSQL_DB", "arvr5")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:"
    f"{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
)

print("DATABASE_URL =", DATABASE_URL)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}

db = SQLAlchemy(app)

# ======================================
# CLOUDINARY CONFIG
# ======================================

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# ======================================
# DATABASE MODEL
# ======================================

class Project(db.Model):

    __tablename__ = "projects"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(255),
        nullable=False
    )

    file_url = db.Column(
        db.Text,
        nullable=False
    )

    public_id = db.Column(
        db.String(255),
        nullable=False
    )

    type = db.Column(
        db.String(50),
        nullable=False
    )

# ======================================
# DATABASE INIT
# ======================================

with app.app_context():

    try:

        db.session.execute(text("SELECT 1"))

        print("DATABASE CONNECTED")

        db.create_all()

        print("TABLES CREATED")

    except Exception as e:

        print("DATABASE ERROR:", str(e))

# ======================================
# DASHBOARD
# ======================================

@app.route("/")
def dashboard():

    try:

        projects = Project.query.order_by(
            Project.id.desc()
        ).all()

        return render_template(
            "dashboard.html",
            projects=projects
        )

    except Exception as e:

        return f"""
        <h2>Database Error</h2>
        <pre>{str(e)}</pre>
        """

# ======================================
# CREATE PROJECT PAGE
# ======================================

@app.route("/create")
def create_project():

    if not session.get("create_auth"):

        return render_template(
            "pin_login.html",
            next_page="/create"
        )

    return render_template(
        "create_project.html"
    )

# ======================================
# VERIFY PIN
# ======================================

@app.route("/verify-pin", methods=["POST"])
def verify_pin():

    pin = request.form.get("pin")
    next_page = request.form.get(
        "next_page",
        "/create"
    )

    if pin == ADMIN_PIN:

        session["create_auth"] = True

        return redirect(next_page)

    return render_template(
        "pin_login.html",
        error="Wrong PIN",
        next_page=next_page
    )

# ======================================
# SAVE PROJECT
# ======================================

@app.route("/save", methods=["POST"])
def save():

    try:

        file = request.files.get("file")
        name = request.form.get("name")
        ptype = request.form.get("type")

        if not file:
            return "No file selected", 400

        if not name:
            return "Project name required", 400

        if not ptype:
            return "Project type required", 400

        public_id = str(uuid.uuid4())

        upload_result = cloudinary.uploader.upload(
            file,
            public_id=public_id,
            resource_type="auto"
        )

        project = Project(
            name=name,
            file_url=upload_result["secure_url"],
            public_id=public_id,
            type=ptype
        )

        db.session.add(project)
        db.session.commit()

        return redirect("/")

    except Exception as e:

        return f"Upload Error: {str(e)}", 500

# ======================================
# IMAGE AR
# ======================================

@app.route("/image-ar/<int:project_id>")
def image_ar(project_id):

    project = Project.query.get_or_404(
        project_id
    )

    return render_template(
        "image_ar.html",
        project=project
    )

# ======================================
# MODEL AR
# ======================================

@app.route("/model-ar/<int:project_id>")
def model_ar(project_id):

    project = Project.query.get_or_404(
        project_id
    )

    return render_template(
        "model_ar.html",
        project=project
    )

# ======================================
# WALL AR
# ======================================

@app.route("/wall-ar")
def wall_ar():

    return render_template(
        "wall_ar.html"
    )

# ======================================
# DELETE PROJECT
# ======================================

@app.route("/delete/<int:id>")
def delete_project(id):

    project = Project.query.get_or_404(id)

    try:

        cloudinary.uploader.destroy(
            project.public_id,
            resource_type="image"
        )

    except Exception:
        pass

    db.session.delete(project)
    db.session.commit()

    return redirect("/")

# ======================================
# LOGOUT
# ======================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# ======================================
# HEALTH CHECK
# ======================================

@app.route("/health")
def health():

    try:

        db.session.execute(
            text("SELECT 1")
        )

        return "Database Connected"

    except Exception as e:

        return (
            f"Database Error: {str(e)}",
            500
        )

# ======================================
# RUN SERVER
# ======================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
