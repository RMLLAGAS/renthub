"""
================================================================================
 RentHub - Rental Marketplace Website
================================================================================
 "Find Boarding Houses, Apartments, Land, and Any Rentable Property."

 A COMPLETE single-file Flask rental marketplace application.
 Everything (models, templates, routes, config) lives in this ONE file so it
 can be run directly inside Pydroid 3 (or any machine with Python 3 + pip).

 HOW TO RUN
 ----------
 1. Install dependencies (only needs to be done once):
        pip install flask flask_sqlalchemy werkzeug

 2. Run the app:
        python main.py

 3. Open your browser to:
        http://127.0.0.1:5000

 On first run this file will automatically:
   - Create the "uploads" folder (and sub-folders) if missing
   - Create the SQLite database "renthub.db" if missing
   - Seed the property categories
   - Create a default admin account:
         email:    admin@renthub.com
         password: admin123
     (Please change this password after logging in for the first time!)
================================================================================
"""

import os
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session, flash,
    render_template_string, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from jinja2 import ChoiceLoader, DictLoader

from flask_sqlalchemy import SQLAlchemy

# ==============================================================================
# APP CONFIGURATION
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PROFILE_FOLDER = os.path.join(UPLOAD_FOLDER, "profiles")
PROPERTY_FOLDER = os.path.join(UPLOAD_FOLDER, "properties")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Automatically create the uploads folders if they don't exist yet
os.makedirs(PROFILE_FOLDER, exist_ok=True)
os.makedirs(PROPERTY_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = "renthub-super-secret-key-please-change-me"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "renthub.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB max upload
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

db = SQLAlchemy(app)

# List of property categories (also seeded into the Categories table)
CATEGORIES = [
    "Boarding House", "Apartment", "House", "Condo", "Room", "Bedspace",
    "Dormitory", "Commercial Space", "Office", "Warehouse", "Land", "Farm",
    "Beach Resort", "Parking", "Vehicle", "Equipment", "Storage", "Others",
]

# Bootstrap icon shown next to each category
CATEGORY_ICONS = {
    "Boarding House": "bi-house-door", "Apartment": "bi-building",
    "House": "bi-house", "Condo": "bi-buildings", "Room": "bi-door-closed",
    "Bedspace": "bi-lamp", "Dormitory": "bi-building-fill",
    "Commercial Space": "bi-shop", "Office": "bi-briefcase",
    "Warehouse": "bi-boxes", "Land": "bi-map", "Farm": "bi-tree",
    "Beach Resort": "bi-umbrella", "Parking": "bi-p-square",
    "Vehicle": "bi-car-front", "Equipment": "bi-tools",
    "Storage": "bi-archive", "Others": "bi-grid",
}


# ==============================================================================
# DATABASE MODELS
# ==============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30), default="")
    password_hash = db.Column(db.String(300), nullable=False)
    profile_pic = db.Column(db.String(300), default="")
    is_admin = db.Column(db.Boolean, default=False)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

    properties = db.relationship("Property", backref="owner", lazy=True,
                                  cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", backref="user", lazy=True,
                                 cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(50), default="Others")
    price = db.Column(db.Float, default=0)
    address = db.Column(db.String(300), default="")
    city = db.Column(db.String(100), default="")
    province = db.Column(db.String(100), default="")
    bedrooms = db.Column(db.Integer, default=0)
    bathrooms = db.Column(db.Integer, default=0)
    floor_area = db.Column(db.Float, default=0)
    lot_area = db.Column(db.Float, default=0)
    parking = db.Column(db.Boolean, default=False)
    wifi = db.Column(db.Boolean, default=False)
    aircon = db.Column(db.Boolean, default=False)
    kitchen = db.Column(db.Boolean, default=False)
    laundry = db.Column(db.Boolean, default=False)
    water = db.Column(db.Boolean, default=False)
    electricity = db.Column(db.Boolean, default=False)
    pets_allowed = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Float, default=0)
    longitude = db.Column(db.Float, default=0)
    maps_link = db.Column(db.String(500), default="")
    contact_number = db.Column(db.String(30), default="")
    facebook_link = db.Column(db.String(300), default="")
    messenger_link = db.Column(db.String(300), default="")
    contact_email = db.Column(db.String(150), default="")
    available = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    images = db.relationship("Image", backref="property", lazy=True,
                              cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", backref="property", lazy=True,
                                 cascade="all, delete-orphan")
    messages = db.relationship("Message", backref="property", lazy=True,
                                cascade="all, delete-orphan")


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_name = db.Column(db.String(150))
    sender_email = db.Column(db.String(150))
    sender_phone = db.Column(db.String(30))
    content = db.Column(db.Text)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_name = db.Column(db.String(150))
    reporter_email = db.Column(db.String(150))
    reason = db.Column(db.Text)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"))
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    icon = db.Column(db.String(50), default="bi-grid")


# ==============================================================================
# HELPER FUNCTIONS / DECORATORS
# ==============================================================================

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage, subfolder):
    """Save an uploaded file safely and return its stored filename, or None."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    safe_name = secure_filename(file_storage.filename)
    unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    folder = os.path.join(UPLOAD_FOLDER, subfolder)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, unique_name))
    return unique_name


def get_current_user():
    uid = session.get("user_id")
    if uid:
        return User.query.get(uid)
    return None


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        if not user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


# Make helpers/constants available inside every Jinja template automatically
app.jinja_env.globals["current_user"] = get_current_user
app.jinja_env.globals["all_categories"] = CATEGORIES
app.jinja_env.globals["category_icons"] = CATEGORY_ICONS


# ==============================================================================
# TEMPLATES
# ==============================================================================
# Every page is rendered with render_template_string(). Shared layout (navbar,
# footer, CSS, JS) lives in BASE_TEMPLATE and MACROS_TEMPLATE, which are
# registered into a DictLoader so individual page templates can use
# {% extends 'base.html' %} and {% import 'macros.html' as macros %}.
# ==============================================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{% block title %}RentHub{% endblock %} | RentHub</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --primary:#2563eb; --primary-dark:#1e40af; --primary-light:#60a5fa;
  --bg:#f0f5ff; --glass:rgba(255,255,255,0.65);
}
*{font-family:'Poppins',sans-serif;}
body{background:linear-gradient(160deg,#eaf1ff 0%,#f7faff 60%,#eef4ff 100%);min-height:100vh;color:#1e293b;}
a{text-decoration:none;}
.navbar{background:rgba(255,255,255,0.85)!important;backdrop-filter:blur(12px);box-shadow:0 2px 18px rgba(37,99,235,0.08);}
.navbar-brand{font-weight:700;color:var(--primary)!important;font-size:1.5rem;}
.navbar-brand i{color:var(--primary-dark);}
.nav-link{font-weight:500;color:#334155!important;}
.nav-link:hover{color:var(--primary)!important;}
.btn-primary{background:var(--primary);border:none;transition:.25s;}
.btn-primary:hover{background:var(--primary-dark);transform:translateY(-2px);}
.btn-outline-primary{border-color:var(--primary);color:var(--primary);}
.btn-outline-primary:hover{background:var(--primary);transform:translateY(-2px);}
.glass-card{background:var(--glass);backdrop-filter:blur(14px);border:1px solid rgba(255,255,255,0.5);border-radius:20px;box-shadow:0 8px 30px rgba(37,99,235,0.10);}
.hero{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-dark) 100%);border-radius:0 0 40px 40px;color:#fff;padding:80px 0 110px;position:relative;overflow:hidden;}
.hero::after{content:"";position:absolute;right:-80px;top:-80px;width:300px;height:300px;background:rgba(255,255,255,0.08);border-radius:50%;}
.hero h1{font-weight:700;font-size:2.6rem;}
.search-box{margin-top:-70px;position:relative;z-index:5;}
.property-card{border:none;border-radius:18px;overflow:hidden;transition:.3s;background:#fff;box-shadow:0 4px 18px rgba(30,64,175,0.08);}
.property-card:hover{transform:translateY(-6px);box-shadow:0 16px 34px rgba(30,64,175,0.18);}
.property-img{height:210px;object-fit:cover;width:100%;}
.badge-cat{background:var(--primary);}
.category-pill{border-radius:16px;padding:22px 10px;text-align:center;background:#fff;box-shadow:0 4px 14px rgba(37,99,235,0.08);transition:.25s;display:block;color:#1e293b;}
.category-pill:hover{transform:translateY(-5px);background:var(--primary);color:#fff;}
.category-pill i{font-size:1.8rem;color:var(--primary);}
.category-pill:hover i{color:#fff;}
footer{background:#0f172a;color:#cbd5e1;border-radius:40px 40px 0 0;margin-top:60px;padding:50px 0 20px;}
footer a{color:#93c5fd;}
.form-control,.form-select{border-radius:12px;padding:10px 14px;}
.card{border-radius:18px;}
.stat-card{border-radius:18px;padding:24px;color:#fff;background:linear-gradient(135deg,var(--primary),var(--primary-dark));}
.sidebar-link{display:block;padding:10px 16px;border-radius:12px;color:#334155;font-weight:500;}
.sidebar-link.active,.sidebar-link:hover{background:var(--primary);color:#fff;}
.animate-in{animation:fadeUp .5s ease both;}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px);}to{opacity:1;transform:translateY(0);}}
</style>
{% block extra_head %}{% endblock %}
</head>
<body>
<nav class="navbar navbar-expand-lg sticky-top">
  <div class="container">
    <a class="navbar-brand" href="{{ url_for('index') }}"><i class="bi bi-houses-fill"></i> RentHub</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navMain">
      <ul class="navbar-nav me-auto ms-lg-4">
        <li class="nav-item"><a class="nav-link" href="{{ url_for('index') }}">Home</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('search') }}">Browse</a></li>
        {% if current_user() %}
        <li class="nav-item"><a class="nav-link" href="{{ url_for('post_property') }}">Post Property</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a></li>
        {% endif %}
      </ul>
      <ul class="navbar-nav">
        {% if current_user() %}
          {% set u = current_user() %}
          <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle d-flex align-items-center gap-2" href="#" data-bs-toggle="dropdown">
              {% if u.profile_pic %}
                <img src="{{ url_for('uploaded_file', folder='profiles', filename=u.profile_pic) }}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">
              {% else %}
                <i class="bi bi-person-circle fs-5"></i>
              {% endif %}
              {{ u.full_name.split(' ')[0] }}
            </a>
            <ul class="dropdown-menu dropdown-menu-end">
              <li><a class="dropdown-item" href="{{ url_for('dashboard') }}"><i class="bi bi-speedometer2"></i> Dashboard</a></li>
              <li><a class="dropdown-item" href="{{ url_for('my_listings') }}"><i class="bi bi-list-ul"></i> My Listings</a></li>
              <li><a class="dropdown-item" href="{{ url_for('my_favorites') }}"><i class="bi bi-heart"></i> Favorites</a></li>
              <li><a class="dropdown-item" href="{{ url_for('edit_profile') }}"><i class="bi bi-gear"></i> Edit Profile</a></li>
              {% if u.is_admin %}
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item" href="{{ url_for('admin_dashboard') }}"><i class="bi bi-shield-lock"></i> Admin Panel</a></li>
              {% endif %}
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item" href="{{ url_for('logout') }}"><i class="bi bi-box-arrow-right"></i> Logout</a></li>
            </ul>
          </li>
        {% else %}
          <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Login</a></li>
          <li class="nav-item"><a class="btn btn-primary text-white px-3 ms-2" href="{{ url_for('register') }}">Sign Up</a></li>
        {% endif %}
      </ul>
    </div>
  </div>
</nav>

<div class="container mt-3">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="alert alert-{{ 'danger' if category=='danger' else category }} alert-dismissible fade show rounded-4" role="alert">
          {{ message }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      {% endfor %}
    {% endif %}
  {% endwith %}
</div>

{% block content %}{% endblock %}

<footer>
  <div class="container">
    <div class="row g-4">
      <div class="col-md-4">
        <h4><i class="bi bi-houses-fill"></i> RentHub</h4>
        <p>Find Boarding Houses, Apartments, Land, and Any Rentable Property — all in one place.</p>
      </div>
      <div class="col-md-4">
        <h6 class="text-white">Quick Links</h6>
        <p><a href="{{ url_for('index') }}">Home</a></p>
        <p><a href="{{ url_for('search') }}">Browse Listings</a></p>
        <p><a href="{{ url_for('post_property') }}">Post a Property</a></p>
      </div>
      <div class="col-md-4">
        <h6 class="text-white">Categories</h6>
        <p>Apartments &middot; Boarding Houses &middot; Land &middot; Commercial Space</p>
      </div>
    </div>
    <hr style="border-color:#334155;">
    <p class="text-center mb-0">&copy; {{ current_year }} RentHub. All rights reserved.</p>
  </div>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
{% block extra_js %}{% endblock %}
</body>
</html>
"""

MACROS_TEMPLATE = """
{% macro property_card(p) %}
<div class="col-md-4 col-sm-6 mb-4">
  <div class="card property-card h-100 animate-in">
    <div class="position-relative">
      {% if p.images and p.images|length > 0 %}
        <img src="{{ url_for('uploaded_file', folder='properties', filename=p.images[0].filename) }}" class="property-img">
      {% else %}
        <div class="property-img d-flex align-items-center justify-content-center bg-light">
          <i class="bi bi-image fs-1 text-secondary"></i>
        </div>
      {% endif %}
      <span class="badge badge-cat position-absolute top-0 start-0 m-2">{{ p.category }}</span>
      {% if p.featured %}<span class="badge bg-warning text-dark position-absolute top-0 end-0 m-2"><i class="bi bi-star-fill"></i> Featured</span>{% endif %}
      {% if not p.available %}<span class="badge bg-danger position-absolute bottom-0 end-0 m-2">Unavailable</span>{% endif %}
    </div>
    <div class="card-body d-flex flex-column">
      <h5 class="card-title mb-1">{{ p.title }}</h5>
      <p class="text-muted small mb-2"><i class="bi bi-geo-alt-fill"></i> {{ p.city }}{% if p.province %}, {{ p.province }}{% endif %}</p>
      <div class="d-flex gap-3 small text-secondary mb-2">
        {% if p.bedrooms %}<span><i class="bi bi-door-closed"></i> {{ p.bedrooms }} bd</span>{% endif %}
        {% if p.bathrooms %}<span><i class="bi bi-droplet"></i> {{ p.bathrooms }} ba</span>{% endif %}
      </div>
      <h5 class="text-primary mb-3">&#8369;{{ '{:,.0f}'.format(p.price) }} <small class="text-muted fw-normal">/mo</small></h5>
      <a href="{{ url_for('property_detail', property_id=p.id) }}" class="btn btn-outline-primary mt-auto w-100">View Details <i class="bi bi-arrow-right"></i></a>
    </div>
  </div>
</div>
{% endmacro %}

{% macro pagination_bar(page, total_pages, endpoint, args) %}
{% if total_pages > 1 %}
<nav class="mt-4">
  <ul class="pagination justify-content-center">
    {% for p in range(1, total_pages + 1) %}
      <li class="page-item {{ 'active' if p == page else '' }}">
        <a class="page-link" href="{{ url_for(endpoint, page=p, **args) }}">{{ p }}</a>
      </li>
    {% endfor %}
  </ul>
</nav>
{% endif %}
{% endmacro %}
"""

app.jinja_loader = ChoiceLoader([
    DictLoader({"base.html": BASE_TEMPLATE, "macros.html": MACROS_TEMPLATE}),
    app.jinja_loader,
])

app.jinja_env.globals["current_year"] = datetime.utcnow().year


# ---- HOME PAGE ----
HOME_TEMPLATE = """
{% extends 'base.html' %}
{% import 'macros.html' as macros %}
{% block title %}Home{% endblock %}
{% block content %}
<div class="hero">
  <div class="container text-center">
    <h1>Find Your Next <span style="color:#bfdbfe;">Place to Rent</span></h1>
    <p class="lead">Boarding Houses &bull; Apartments &bull; Land &bull; Commercial Spaces &amp; more</p>
  </div>
</div>

<div class="container search-box">
  <div class="glass-card p-4">
    <form action="{{ url_for('search') }}" method="get" class="row g-2">
      <div class="col-md-4">
        <input type="text" name="q" class="form-control" placeholder="Keyword (e.g. studio, condo...)">
      </div>
      <div class="col-md-3">
        <select name="category" class="form-select">
          <option value="">All Categories</option>
          {% for c in all_categories %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
        </select>
      </div>
      <div class="col-md-3">
        <input type="text" name="location" class="form-control" placeholder="City / Province">
      </div>
      <div class="col-md-2">
        <button class="btn btn-primary w-100 text-white" type="submit"><i class="bi bi-search"></i> Search</button>
      </div>
    </form>
  </div>
</div>

<div class="container mt-5">
  <h3 class="mb-4"><i class="bi bi-grid-3x3-gap-fill text-primary"></i> Browse by Category</h3>
  <div class="row g-3">
    {% for c in all_categories %}
    <div class="col-6 col-md-2">
      <a href="{{ url_for('search', category=c) }}" class="category-pill">
        <i class="bi {{ category_icons.get(c, 'bi-grid') }}"></i>
        <div class="small mt-2">{{ c }}</div>
      </a>
    </div>
    {% endfor %}
  </div>
</div>

{% if featured %}
<div class="container mt-5">
  <h3 class="mb-4"><i class="bi bi-star-fill text-warning"></i> Featured Listings</h3>
  <div class="row">
    {% for p in featured %}{{ macros.property_card(p) }}{% endfor %}
  </div>
</div>
{% endif %}

<div class="container mt-5">
  <h3 class="mb-4"><i class="bi bi-clock-history text-primary"></i> Newest Listings</h3>
  <div class="row">
    {% for p in newest %}{{ macros.property_card(p) }}{% endfor %}
  </div>
  {% if not newest %}<p class="text-muted">No properties posted yet. Be the first to <a href="{{ url_for('post_property') }}">post one</a>!</p>{% endif %}
</div>

{% if cities %}
<div class="container mt-5 mb-5">
  <h3 class="mb-4"><i class="bi bi-geo-alt-fill text-primary"></i> Popular Cities</h3>
  <div class="d-flex flex-wrap gap-2">
    {% for c in cities %}
    <a href="{{ url_for('search', location=c) }}" class="btn btn-outline-primary rounded-pill">{{ c }}</a>
    {% endfor %}
  </div>
</div>
{% endif %}
{% endblock %}
"""

# ---- AUTH TEMPLATES ----
LOGIN_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Login{% endblock %}
{% block content %}
<div class="container my-5" style="max-width:460px;">
  <div class="glass-card p-4 p-md-5">
    <h3 class="text-center mb-4"><i class="bi bi-box-arrow-in-right text-primary"></i> Welcome Back</h3>
    <form method="post">
      <div class="mb-3">
        <label class="form-label">Email</label>
        <input type="email" name="email" class="form-control" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Password</label>
        <input type="password" name="password" class="form-control" required>
      </div>
      <div class="form-check mb-3">
        <input class="form-check-input" type="checkbox" name="remember" id="remember">
        <label class="form-check-label" for="remember">Remember Me</label>
      </div>
      <button type="submit" class="btn btn-primary text-white w-100">Login</button>
    </form>
    <p class="text-center mt-3 mb-0">Don't have an account? <a href="{{ url_for('register') }}">Sign up</a></p>
  </div>
</div>
{% endblock %}
"""

REGISTER_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Sign Up{% endblock %}
{% block content %}
<div class="container my-5" style="max-width:520px;">
  <div class="glass-card p-4 p-md-5">
    <h3 class="text-center mb-4"><i class="bi bi-person-plus text-primary"></i> Create Your Account</h3>
    <form method="post">
      <div class="mb-3">
        <label class="form-label">Full Name</label>
        <input type="text" name="full_name" class="form-control" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Email</label>
        <input type="email" name="email" class="form-control" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Phone Number</label>
        <input type="text" name="phone" class="form-control">
      </div>
      <div class="mb-3">
        <label class="form-label">Password</label>
        <input type="password" name="password" class="form-control" required minlength="6">
      </div>
      <div class="mb-3">
        <label class="form-label">Confirm Password</label>
        <input type="password" name="confirm_password" class="form-control" required minlength="6">
      </div>
      <button type="submit" class="btn btn-primary text-white w-100">Create Account</button>
    </form>
    <p class="text-center mt-3 mb-0">Already have an account? <a href="{{ url_for('login') }}">Login</a></p>
  </div>
</div>
{% endblock %}
"""

EDIT_PROFILE_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Edit Profile{% endblock %}
{% block content %}
<div class="container my-5" style="max-width:600px;">
  <div class="glass-card p-4 p-md-5">
    <h3 class="mb-4"><i class="bi bi-gear text-primary"></i> Edit Profile</h3>
    <div class="text-center mb-4">
      {% if user.profile_pic %}
        <img src="{{ url_for('uploaded_file', folder='profiles', filename=user.profile_pic) }}" style="width:110px;height:110px;object-fit:cover;border-radius:50%;">
      {% else %}
        <i class="bi bi-person-circle" style="font-size:6rem;color:#94a3b8;"></i>
      {% endif %}
    </div>
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label class="form-label">Profile Picture</label>
        <input type="file" name="profile_pic" class="form-control" accept="image/*">
      </div>
      <div class="mb-3">
        <label class="form-label">Full Name</label>
        <input type="text" name="full_name" class="form-control" value="{{ user.full_name }}" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Email</label>
        <input type="email" class="form-control" value="{{ user.email }}" disabled>
      </div>
      <div class="mb-3">
        <label class="form-label">Phone Number</label>
        <input type="text" name="phone" class="form-control" value="{{ user.phone or '' }}">
      </div>
      <hr>
      <h6>Change Password (optional)</h6>
      <div class="mb-3">
        <label class="form-label">New Password</label>
        <input type="password" name="new_password" class="form-control" minlength="6">
      </div>
      <button type="submit" class="btn btn-primary text-white w-100">Save Changes</button>
    </form>
  </div>
</div>
{% endblock %}
"""

# ---- DASHBOARD ----
DASHBOARD_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Dashboard{% endblock %}
{% block content %}
<div class="container my-5">
  <h3 class="mb-4"><i class="bi bi-speedometer2 text-primary"></i> Welcome, {{ user.full_name }}</h3>
  <div class="row g-3 mb-4">
    <div class="col-md-3 col-6">
      <div class="stat-card"><h2>{{ listing_count }}</h2><p class="mb-0">My Listings</p></div>
    </div>
    <div class="col-md-3 col-6">
      <div class="stat-card" style="background:linear-gradient(135deg,#f59e0b,#b45309);"><h2>{{ favorite_count }}</h2><p class="mb-0">Favorites</p></div>
    </div>
    <div class="col-md-3 col-6">
      <div class="stat-card" style="background:linear-gradient(135deg,#10b981,#047857);"><h2>{{ message_count }}</h2><p class="mb-0">Messages</p></div>
    </div>
    <div class="col-md-3 col-6">
      <div class="stat-card" style="background:linear-gradient(135deg,#8b5cf6,#5b21b6);"><h2>{{ total_views }}</h2><p class="mb-0">Total Views</p></div>
    </div>
  </div>

  <div class="row g-3 mb-4">
    <div class="col-md-4">
      <a href="{{ url_for('post_property') }}" class="btn btn-primary text-white w-100 py-3"><i class="bi bi-plus-circle"></i> Post New Property</a>
    </div>
    <div class="col-md-4">
      <a href="{{ url_for('my_listings') }}" class="btn btn-outline-primary w-100 py-3"><i class="bi bi-list-ul"></i> Manage My Listings</a>
    </div>
    <div class="col-md-4">
      <a href="{{ url_for('my_favorites') }}" class="btn btn-outline-primary w-100 py-3"><i class="bi bi-heart"></i> View Favorites</a>
    </div>
  </div>

  <div class="glass-card p-4">
    <h5><i class="bi bi-envelope text-primary"></i> Recent Messages</h5>
    {% if messages %}
    <div class="table-responsive">
      <table class="table align-middle">
        <thead><tr><th>From</th><th>Property</th><th>Message</th><th>Date</th></tr></thead>
        <tbody>
        {% for m in messages %}
        <tr>
          <td>{{ m.sender_name }}<br><small class="text-muted">{{ m.sender_email }}</small></td>
          <td><a href="{{ url_for('property_detail', property_id=m.property_id) }}">{{ m.property.title }}</a></td>
          <td>{{ m.content[:80] }}</td>
          <td>{{ m.date_sent.strftime('%b %d, %Y') }}</td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
      <p class="text-muted mb-0">No messages yet.</p>
    {% endif %}
  </div>
</div>
{% endblock %}
"""

MY_LISTINGS_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}My Listings{% endblock %}
{% block content %}
<div class="container my-5">
  <div class="d-flex justify-content-between align-items-center mb-4">
    <h3 class="mb-0"><i class="bi bi-list-ul text-primary"></i> My Listings</h3>
    <a href="{{ url_for('post_property') }}" class="btn btn-primary text-white"><i class="bi bi-plus-circle"></i> Post Property</a>
  </div>
  {% if properties %}
  <div class="table-responsive glass-card p-3">
    <table class="table align-middle mb-0">
      <thead><tr><th>Title</th><th>Category</th><th>Price</th><th>Status</th><th>Views</th><th>Actions</th></tr></thead>
      <tbody>
      {% for p in properties %}
      <tr>
        <td>{{ p.title }}</td>
        <td>{{ p.category }}</td>
        <td>&#8369;{{ '{:,.0f}'.format(p.price) }}</td>
        <td>{% if p.available %}<span class="badge bg-success">Available</span>{% else %}<span class="badge bg-secondary">Unavailable</span>{% endif %}</td>
        <td>{{ p.views }}</td>
        <td class="d-flex gap-1">
          <a href="{{ url_for('property_detail', property_id=p.id) }}" class="btn btn-sm btn-outline-primary"><i class="bi bi-eye"></i></a>
          <a href="{{ url_for('edit_property', property_id=p.id) }}" class="btn btn-sm btn-outline-secondary"><i class="bi bi-pencil"></i></a>
          <form method="post" action="{{ url_for('delete_property', property_id=p.id) }}" onsubmit="return confirm('Delete this property?');">
            <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
          </form>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
  {% else %}
    <p class="text-muted">You have not posted any properties yet.</p>
  {% endif %}
</div>
{% endblock %}
"""

MY_FAVORITES_TEMPLATE = """
{% extends 'base.html' %}
{% import 'macros.html' as macros %}
{% block title %}My Favorites{% endblock %}
{% block content %}
<div class="container my-5">
  <h3 class="mb-4"><i class="bi bi-heart-fill text-danger"></i> My Favorite Properties</h3>
  <div class="row">
    {% for p in properties %}{{ macros.property_card(p) }}{% endfor %}
  </div>
  {% if not properties %}<p class="text-muted">You haven't favorited any properties yet.</p>{% endif %}
</div>
{% endblock %}
"""

# ---- POST / EDIT PROPERTY ----
PROPERTY_FORM_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}{{ 'Edit' if property else 'Post' }} Property{% endblock %}
{% block content %}
<div class="container my-5">
  <div class="glass-card p-4 p-md-5">
    <h3 class="mb-4"><i class="bi bi-{{ 'pencil' if property else 'plus-circle' }} text-primary"></i> {{ 'Edit' if property else 'Post New' }} Property</h3>
    <form method="post" enctype="multipart/form-data">
      <div class="row g-3">
        <div class="col-md-8">
          <label class="form-label">Title</label>
          <input type="text" name="title" class="form-control" required value="{{ property.title if property else '' }}">
        </div>
        <div class="col-md-4">
          <label class="form-label">Category</label>
          <select name="category" class="form-select">
            {% for c in all_categories %}
            <option value="{{ c }}" {{ 'selected' if property and property.category == c else '' }}>{{ c }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-12">
          <label class="form-label">Description</label>
          <textarea name="description" class="form-control" rows="4">{{ property.description if property else '' }}</textarea>
        </div>
        <div class="col-md-4">
          <label class="form-label">Price (per month)</label>
          <input type="number" step="0.01" name="price" class="form-control" required value="{{ property.price if property else '' }}">
        </div>
        <div class="col-md-4">
          <label class="form-label">City</label>
          <input type="text" name="city" class="form-control" required value="{{ property.city if property else '' }}">
        </div>
        <div class="col-md-4">
          <label class="form-label">Province</label>
          <input type="text" name="province" class="form-control" value="{{ property.province if property else '' }}">
        </div>
        <div class="col-12">
          <label class="form-label">Full Address</label>
          <input type="text" name="address" class="form-control" value="{{ property.address if property else '' }}">
        </div>

        <div class="col-md-3 col-6">
          <label class="form-label">Bedrooms</label>
          <input type="number" name="bedrooms" class="form-control" value="{{ property.bedrooms if property else 0 }}">
        </div>
        <div class="col-md-3 col-6">
          <label class="form-label">Bathrooms</label>
          <input type="number" name="bathrooms" class="form-control" value="{{ property.bathrooms if property else 0 }}">
        </div>
        <div class="col-md-3 col-6">
          <label class="form-label">Floor Area (sqm)</label>
          <input type="number" step="0.01" name="floor_area" class="form-control" value="{{ property.floor_area if property else 0 }}">
        </div>
        <div class="col-md-3 col-6">
          <label class="form-label">Lot Area (sqm)</label>
          <input type="number" step="0.01" name="lot_area" class="form-control" value="{{ property.lot_area if property else 0 }}">
        </div>

        <div class="col-12"><hr><h6>Amenities</h6></div>
        {% set amenities = [('parking','Parking'),('wifi','WiFi'),('aircon','Aircon'),('kitchen','Kitchen'),('laundry','Laundry'),('water','Water Supply'),('electricity','Electricity'),('pets_allowed','Pets Allowed')] %}
        {% for key, label in amenities %}
        <div class="col-md-3 col-6">
          <div class="form-check">
            <input class="form-check-input" type="checkbox" name="{{ key }}" id="{{ key }}" {{ 'checked' if property and property[key] else '' }}>
            <label class="form-check-label" for="{{ key }}">{{ label }}</label>
          </div>
        </div>
        {% endfor %}

        <div class="col-12"><hr><h6>Location &amp; Contact</h6></div>
        <div class="col-md-4">
          <label class="form-label">Latitude</label>
          <input type="text" name="latitude" class="form-control" value="{{ property.latitude if property else '' }}">
        </div>
        <div class="col-md-4">
          <label class="form-label">Longitude</label>
          <input type="text" name="longitude" class="form-control" value="{{ property.longitude if property else '' }}">
        </div>
        <div class="col-md-4">
          <label class="form-label">Google Maps Link</label>
          <input type="text" name="maps_link" class="form-control" value="{{ property.maps_link if property else '' }}">
        </div>
        <div class="col-md-3 col-6">
          <label class="form-label">Contact Number</label>
          <input type="text" name="contact_number" class="form-control" value="{{ property.contact_number if property else '' }}">
        </div>
        <div class="col-md-3 col-6">
          <label class="form-label">Contact Email</label>
          <input type="email" name="contact_email" class="form-control" value="{{ property.contact_email if property else '' }}">
        </div>
        <div class="col-md-3 col-6">
          <label class="form-label">Facebook Link</label>
          <input type="text" name="facebook_link" class="form-control" value="{{ property.facebook_link if property else '' }}">
        </div>
        <div class="col-md-3 col-6">
          <label class="form-label">Messenger Link</label>
          <input type="text" name="messenger_link" class="form-control" value="{{ property.messenger_link if property else '' }}">
        </div>

        <div class="col-12"><hr><h6>Images</h6></div>
        <div class="col-12">
          <label class="form-label">Upload Images (you can select multiple)</label>
          <input type="file" name="images" class="form-control" accept="image/*" multiple>
        </div>
        {% if property and property.images %}
        <div class="col-12 d-flex flex-wrap gap-2">
          {% for img in property.images %}
          <div class="position-relative">
            <img src="{{ url_for('uploaded_file', folder='properties', filename=img.filename) }}" style="width:100px;height:80px;object-fit:cover;border-radius:10px;">
            <a href="{{ url_for('delete_property_image', image_id=img.id) }}" class="btn btn-sm btn-danger position-absolute top-0 end-0" onclick="return confirm('Remove this image?');" style="padding:0 6px;border-radius:50%;">&times;</a>
          </div>
          {% endfor %}
        </div>
        {% endif %}

        <div class="col-12">
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" name="available" id="available" {{ 'checked' if (not property) or property.available else '' }}>
            <label class="form-check-label" for="available">Available for Rent</label>
          </div>
        </div>
      </div>

      <button type="submit" class="btn btn-primary text-white w-100 mt-4 py-2">
        <i class="bi bi-check-circle"></i> {{ 'Save Changes' if property else 'Publish Property' }}
      </button>
    </form>
  </div>
</div>
{% endblock %}
"""

# ---- PROPERTY DETAIL ----
PROPERTY_DETAIL_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}{{ property.title }}{% endblock %}
{% block content %}
<div class="container my-5">
  <div class="row g-4">
    <div class="col-lg-8">
      <div class="glass-card p-3 mb-4">
        {% if property.images %}
        <div id="gallery" class="carousel slide rounded-4 overflow-hidden" data-bs-ride="carousel">
          <div class="carousel-inner">
            {% for img in property.images %}
            <div class="carousel-item {{ 'active' if loop.first else '' }}">
              <img src="{{ url_for('uploaded_file', folder='properties', filename=img.filename) }}" class="d-block w-100" style="height:420px;object-fit:cover;">
            </div>
            {% endfor %}
          </div>
          {% if property.images|length > 1 %}
          <button class="carousel-control-prev" type="button" data-bs-target="#gallery" data-bs-slide="prev">
            <span class="carousel-control-prev-icon"></span>
          </button>
          <button class="carousel-control-next" type="button" data-bs-target="#gallery" data-bs-slide="next">
            <span class="carousel-control-next-icon"></span>
          </button>
          {% endif %}
        </div>
        {% else %}
        <div class="d-flex align-items-center justify-content-center bg-light rounded-4" style="height:300px;">
          <i class="bi bi-image fs-1 text-secondary"></i>
        </div>
        {% endif %}
      </div>

      <div class="glass-card p-4 mb-4">
        <div class="d-flex justify-content-between align-items-start flex-wrap">
          <div>
            <span class="badge badge-cat mb-2">{{ property.category }}</span>
            <h2>{{ property.title }}</h2>
            <p class="text-muted"><i class="bi bi-geo-alt-fill"></i> {{ property.address }}{% if property.address %}, {% endif %}{{ property.city }}, {{ property.province }}</p>
          </div>
          <h2 class="text-primary">&#8369;{{ '{:,.0f}'.format(property.price) }}<small class="text-muted fw-normal"> /mo</small></h2>
        </div>

        <div class="row text-center my-4 g-2">
          <div class="col-3"><i class="bi bi-door-closed fs-4 text-primary"></i><div>{{ property.bedrooms }} Beds</div></div>
          <div class="col-3"><i class="bi bi-droplet fs-4 text-primary"></i><div>{{ property.bathrooms }} Baths</div></div>
          <div class="col-3"><i class="bi bi-arrows-angle-expand fs-4 text-primary"></i><div>{{ property.floor_area }} sqm</div></div>
          <div class="col-3"><i class="bi bi-eye fs-4 text-primary"></i><div>{{ property.views }} views</div></div>
        </div>

        <h5>Description</h5>
        <p>{{ property.description }}</p>

        <h5>Amenities</h5>
        <div class="row g-2 mb-3">
          {% set amenities = [('parking','Parking'),('wifi','WiFi'),('aircon','Aircon'),('kitchen','Kitchen'),('laundry','Laundry'),('water','Water Supply'),('electricity','Electricity'),('pets_allowed','Pets Allowed')] %}
          {% for key, label in amenities %}
            {% if property[key] %}
            <div class="col-md-3 col-6"><i class="bi bi-check-circle-fill text-success"></i> {{ label }}</div>
            {% endif %}
          {% endfor %}
        </div>

        {% if property.maps_link %}
        <a href="{{ property.maps_link }}" target="_blank" class="btn btn-outline-primary"><i class="bi bi-map"></i> View on Google Maps</a>
        {% endif %}
      </div>
    </div>

    <div class="col-lg-4">
      <div class="glass-card p-4 mb-4">
        <h5><i class="bi bi-person-circle"></i> Listed By</h5>
        <div class="d-flex align-items-center gap-3 mb-3">
          {% if property.owner.profile_pic %}
            <img src="{{ url_for('uploaded_file', folder='profiles', filename=property.owner.profile_pic) }}" style="width:56px;height:56px;border-radius:50%;object-fit:cover;">
          {% else %}
            <i class="bi bi-person-circle fs-1 text-secondary"></i>
          {% endif %}
          <div>
            <strong>{{ property.owner.full_name }}</strong><br>
            <small class="text-muted">Member since {{ property.owner.date_joined.strftime('%Y') }}</small>
          </div>
        </div>
        {% if property.contact_number %}<p><i class="bi bi-telephone-fill text-primary"></i> {{ property.contact_number }}</p>{% endif %}
        {% if property.contact_email %}<p><i class="bi bi-envelope-fill text-primary"></i> {{ property.contact_email }}</p>{% endif %}
        <div class="d-flex gap-2">
          {% if property.facebook_link %}<a href="{{ property.facebook_link }}" target="_blank" class="btn btn-outline-primary btn-sm"><i class="bi bi-facebook"></i></a>{% endif %}
          {% if property.messenger_link %}<a href="{{ property.messenger_link }}" target="_blank" class="btn btn-outline-primary btn-sm"><i class="bi bi-messenger"></i></a>{% endif %}
        </div>
      </div>

      <div class="glass-card p-4 mb-4">
        <div class="d-flex gap-2">
          {% if current_user() %}
          <form method="post" action="{{ url_for('toggle_favorite', property_id=property.id) }}" class="flex-fill">
            <button class="btn {{ 'btn-danger' if is_favorited else 'btn-outline-danger' }} w-100">
              <i class="bi bi-heart{{ '-fill' if is_favorited else '' }}"></i> {{ 'Favorited' if is_favorited else 'Add to Favorites' }}
            </button>
          </form>
          {% endif %}
        </div>
      </div>

      <div class="glass-card p-4">
        <h5><i class="bi bi-envelope-paper"></i> Contact Owner</h5>
        <form method="post" action="{{ url_for('contact_owner', property_id=property.id) }}">
          <div class="mb-2"><input type="text" name="sender_name" class="form-control" placeholder="Your Name" required value="{{ user.full_name if user else '' }}"></div>
          <div class="mb-2"><input type="email" name="sender_email" class="form-control" placeholder="Your Email" required value="{{ user.email if user else '' }}"></div>
          <div class="mb-2"><input type="text" name="sender_phone" class="form-control" placeholder="Your Phone"></div>
          <div class="mb-2"><textarea name="content" class="form-control" rows="3" placeholder="I'm interested in this property..." required></textarea></div>
          <button class="btn btn-primary text-white w-100"><i class="bi bi-send"></i> Send Message</button>
        </form>
        <hr>
        <a href="{{ url_for('report_property', property_id=property.id) }}" class="small text-danger"><i class="bi bi-flag"></i> Report this listing</a>
      </div>
    </div>
  </div>
</div>
{% endblock %}
"""

REPORT_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Report Listing{% endblock %}
{% block content %}
<div class="container my-5" style="max-width:500px;">
  <div class="glass-card p-4">
    <h4><i class="bi bi-flag text-danger"></i> Report Listing: {{ property.title }}</h4>
    <form method="post">
      <div class="mb-3"><label class="form-label">Your Name</label><input type="text" name="reporter_name" class="form-control" required></div>
      <div class="mb-3"><label class="form-label">Your Email</label><input type="email" name="reporter_email" class="form-control" required></div>
      <div class="mb-3"><label class="form-label">Reason</label><textarea name="reason" class="form-control" rows="4" required></textarea></div>
      <button class="btn btn-danger text-white w-100">Submit Report</button>
    </form>
  </div>
</div>
{% endblock %}
"""

# ---- SEARCH ----
SEARCH_TEMPLATE = """
{% extends 'base.html' %}
{% import 'macros.html' as macros %}
{% block title %}Browse Properties{% endblock %}
{% block content %}
<div class="container my-5">
  <div class="glass-card p-4 mb-4">
    <form method="get" class="row g-2">
      <div class="col-md-3"><input type="text" name="q" class="form-control" placeholder="Keyword" value="{{ filters.q }}"></div>
      <div class="col-md-2">
        <select name="category" class="form-select">
          <option value="">All Categories</option>
          {% for c in all_categories %}<option value="{{ c }}" {{ 'selected' if filters.category==c else '' }}>{{ c }}</option>{% endfor %}
        </select>
      </div>
      <div class="col-md-2"><input type="text" name="location" class="form-control" placeholder="Location" value="{{ filters.location }}"></div>
      <div class="col-md-1"><input type="number" name="min_price" class="form-control" placeholder="Min ₱" value="{{ filters.min_price }}"></div>
      <div class="col-md-1"><input type="number" name="max_price" class="form-control" placeholder="Max ₱" value="{{ filters.max_price }}"></div>
      <div class="col-md-1"><input type="number" name="bedrooms" class="form-control" placeholder="Beds" value="{{ filters.bedrooms }}"></div>
      <div class="col-md-2">
        <select name="sort" class="form-select">
          <option value="newest" {{ 'selected' if filters.sort=='newest' else '' }}>Newest</option>
          <option value="oldest" {{ 'selected' if filters.sort=='oldest' else '' }}>Oldest</option>
          <option value="price_low" {{ 'selected' if filters.sort=='price_low' else '' }}>Lowest Price</option>
          <option value="price_high" {{ 'selected' if filters.sort=='price_high' else '' }}>Highest Price</option>
        </select>
      </div>
      <div class="col-12"><button class="btn btn-primary text-white"><i class="bi bi-funnel"></i> Apply Filters</button></div>
    </form>
  </div>

  <p class="text-muted">{{ total }} propert{{ 'y' if total == 1 else 'ies' }} found</p>
  <div class="row">
    {% for p in properties %}{{ macros.property_card(p) }}{% endfor %}
  </div>
  {% if not properties %}<p class="text-muted">No properties matched your search.</p>{% endif %}
  {{ macros.pagination_bar(page, total_pages, 'search', filters) }}
</div>
{% endblock %}
"""

# ---- ADMIN TEMPLATES ----
ADMIN_DASHBOARD_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Admin Dashboard{% endblock %}
{% block content %}
<div class="container my-5">
  <h3 class="mb-4"><i class="bi bi-shield-lock text-primary"></i> Admin Dashboard</h3>
  <div class="row g-3 mb-4">
    <div class="col-md-3 col-6"><div class="stat-card"><h2>{{ total_users }}</h2><p class="mb-0">Users</p></div></div>
    <div class="col-md-3 col-6"><div class="stat-card" style="background:linear-gradient(135deg,#10b981,#047857);"><h2>{{ total_listings }}</h2><p class="mb-0">Listings</p></div></div>
    <div class="col-md-3 col-6"><div class="stat-card" style="background:linear-gradient(135deg,#f59e0b,#b45309);"><h2>{{ total_messages }}</h2><p class="mb-0">Messages</p></div></div>
    <div class="col-md-3 col-6"><div class="stat-card" style="background:linear-gradient(135deg,#ef4444,#991b1b);"><h2>{{ pending_reports }}</h2><p class="mb-0">Pending Reports</p></div></div>
  </div>
  <div class="row g-3">
    <div class="col-md-4"><a href="{{ url_for('admin_users') }}" class="btn btn-outline-primary w-100 py-3"><i class="bi bi-people"></i> Manage Users</a></div>
    <div class="col-md-4"><a href="{{ url_for('admin_listings') }}" class="btn btn-outline-primary w-100 py-3"><i class="bi bi-list-ul"></i> Manage Listings</a></div>
    <div class="col-md-4"><a href="{{ url_for('admin_reports') }}" class="btn btn-outline-primary w-100 py-3"><i class="bi bi-flag"></i> View Reports</a></div>
  </div>
</div>
{% endblock %}
"""

ADMIN_USERS_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Manage Users{% endblock %}
{% block content %}
<div class="container my-5">
  <h3 class="mb-4"><i class="bi bi-people text-primary"></i> Manage Users</h3>
  <form method="get" class="mb-3">
    <div class="input-group" style="max-width:400px;">
      <input type="text" name="q" class="form-control" placeholder="Search by name or email" value="{{ q }}">
      <button class="btn btn-primary text-white"><i class="bi bi-search"></i></button>
    </div>
  </form>
  <div class="table-responsive glass-card p-3">
    <table class="table align-middle mb-0">
      <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Listings</th><th>Joined</th><th>Role</th><th>Actions</th></tr></thead>
      <tbody>
      {% for u in users %}
      <tr>
        <td>{{ u.full_name }}</td>
        <td>{{ u.email }}</td>
        <td>{{ u.phone }}</td>
        <td>{{ u.properties|length }}</td>
        <td>{{ u.date_joined.strftime('%b %d, %Y') }}</td>
        <td>{% if u.is_admin %}<span class="badge bg-primary">Admin</span>{% else %}<span class="badge bg-secondary">User</span>{% endif %}</td>
        <td class="d-flex gap-1">
          <form method="post" action="{{ url_for('admin_toggle_admin', user_id=u.id) }}">
            <button class="btn btn-sm btn-outline-primary">{{ 'Revoke Admin' if u.is_admin else 'Make Admin' }}</button>
          </form>
          <form method="post" action="{{ url_for('admin_delete_user', user_id=u.id) }}" onsubmit="return confirm('Delete this user and all their listings?');">
            <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
          </form>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
"""

ADMIN_LISTINGS_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Manage Listings{% endblock %}
{% block content %}
<div class="container my-5">
  <h3 class="mb-4"><i class="bi bi-list-ul text-primary"></i> Manage Listings</h3>
  <div class="table-responsive glass-card p-3">
    <table class="table align-middle mb-0">
      <thead><tr><th>Title</th><th>Owner</th><th>Category</th><th>Price</th><th>Featured</th><th>Actions</th></tr></thead>
      <tbody>
      {% for p in properties %}
      <tr>
        <td><a href="{{ url_for('property_detail', property_id=p.id) }}">{{ p.title }}</a></td>
        <td>{{ p.owner.full_name }}</td>
        <td>{{ p.category }}</td>
        <td>&#8369;{{ '{:,.0f}'.format(p.price) }}</td>
        <td>{% if p.featured %}<span class="badge bg-warning text-dark">Featured</span>{% else %}<span class="text-muted">-</span>{% endif %}</td>
        <td class="d-flex gap-1">
          <form method="post" action="{{ url_for('admin_toggle_featured', property_id=p.id) }}">
            <button class="btn btn-sm btn-outline-warning">{{ 'Unfeature' if p.featured else 'Feature' }}</button>
          </form>
          <form method="post" action="{{ url_for('delete_property', property_id=p.id) }}" onsubmit="return confirm('Delete this listing?');">
            <button class="btn btn-sm btn-outline-danger"><i class="bi bi-trash"></i></button>
          </form>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
"""

ADMIN_REPORTS_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}Reports{% endblock %}
{% block content %}
<div class="container my-5">
  <h3 class="mb-4"><i class="bi bi-flag text-danger"></i> Reported Listings</h3>
  <div class="table-responsive glass-card p-3">
    <table class="table align-middle mb-0">
      <thead><tr><th>Property</th><th>Reporter</th><th>Reason</th><th>Date</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>
      {% for r in reports %}
      <tr>
        <td>{% if r.property %}<a href="{{ url_for('property_detail', property_id=r.property.id) }}">{{ r.property.title }}</a>{% else %}(deleted){% endif %}</td>
        <td>{{ r.reporter_name }}<br><small class="text-muted">{{ r.reporter_email }}</small></td>
        <td>{{ r.reason }}</td>
        <td>{{ r.date_reported.strftime('%b %d, %Y') }}</td>
        <td>{% if r.resolved %}<span class="badge bg-success">Resolved</span>{% else %}<span class="badge bg-warning text-dark">Pending</span>{% endif %}</td>
        <td>
          {% if not r.resolved %}
          <form method="post" action="{{ url_for('admin_resolve_report', report_id=r.id) }}">
            <button class="btn btn-sm btn-outline-success">Mark Resolved</button>
          </form>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
"""


# ==============================================================================
# ROUTES - CORE PAGES
# ==============================================================================

@app.route("/")
def index():
    featured = Property.query.filter_by(featured=True, available=True) \
        .order_by(Property.date_posted.desc()).limit(6).all()
    newest = Property.query.filter_by(available=True) \
        .order_by(Property.date_posted.desc()).limit(8).all()
    cities = [row[0] for row in db.session.query(Property.city).filter(
        Property.city != "").distinct().limit(10).all()]
    return render_template_string(HOME_TEMPLATE, featured=featured, newest=newest, cities=cities)


@app.route("/uploads/<folder>/<path:filename>")
def uploaded_file(folder, filename):
    if folder not in ("profiles", "properties"):
        abort(404)
    return send_from_directory(os.path.join(UPLOAD_FOLDER, folder), filename)


# ------------------------------------------------------------------ AUTH ----

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not email or not password:
            flash("Please fill in all required fields.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
        else:
            user = User(full_name=full_name, email=email, phone=phone)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template_string(REGISTER_TEMPLATE)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session.permanent = bool(remember)
            flash(f"Welcome back, {user.full_name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template_string(LOGIN_TEMPLATE)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = get_current_user()
    if request.method == "POST":
        user.full_name = request.form.get("full_name", user.full_name).strip()
        user.phone = request.form.get("phone", user.phone).strip()

        new_password = request.form.get("new_password", "").strip()
        if new_password:
            if len(new_password) < 6:
                flash("New password must be at least 6 characters.", "danger")
                return render_template_string(EDIT_PROFILE_TEMPLATE, user=user)
            user.set_password(new_password)

        pic = request.files.get("profile_pic")
        if pic and pic.filename:
            saved = save_uploaded_file(pic, "profiles")
            if saved:
                user.profile_pic = saved

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("edit_profile"))
    return render_template_string(EDIT_PROFILE_TEMPLATE, user=user)


# -------------------------------------------------------------- DASHBOARD ----

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    listing_count = Property.query.filter_by(owner_id=user.id).count()
    favorite_count = Favorite.query.filter_by(user_id=user.id).count()
    message_count = Message.query.filter_by(owner_id=user.id).count()
    total_views = db.session.query(db.func.sum(Property.views)).filter_by(owner_id=user.id).scalar() or 0
    messages = Message.query.filter_by(owner_id=user.id).order_by(Message.date_sent.desc()).limit(10).all()
    return render_template_string(
        DASHBOARD_TEMPLATE, user=user, listing_count=listing_count,
        favorite_count=favorite_count, message_count=message_count,
        total_views=total_views, messages=messages,
    )


@app.route("/my-listings")
@login_required
def my_listings():
    user = get_current_user()
    properties = Property.query.filter_by(owner_id=user.id).order_by(Property.date_posted.desc()).all()
    return render_template_string(MY_LISTINGS_TEMPLATE, properties=properties)


@app.route("/my-favorites")
@login_required
def my_favorites():
    user = get_current_user()
    favs = Favorite.query.filter_by(user_id=user.id).all()
    properties = [f.property for f in favs if f.property]
    return render_template_string(MY_FAVORITES_TEMPLATE, properties=properties)


# ------------------------------------------------------------- PROPERTIES ----

@app.route("/property/post", methods=["GET", "POST"])
@login_required
def post_property():
    user = get_current_user()
    if request.method == "POST":
        prop = Property(
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", "").strip(),
            category=request.form.get("category", "Others"),
            price=float(request.form.get("price") or 0),
            address=request.form.get("address", "").strip(),
            city=request.form.get("city", "").strip(),
            province=request.form.get("province", "").strip(),
            bedrooms=int(request.form.get("bedrooms") or 0),
            bathrooms=int(request.form.get("bathrooms") or 0),
            floor_area=float(request.form.get("floor_area") or 0),
            lot_area=float(request.form.get("lot_area") or 0),
            parking=bool(request.form.get("parking")),
            wifi=bool(request.form.get("wifi")),
            aircon=bool(request.form.get("aircon")),
            kitchen=bool(request.form.get("kitchen")),
            laundry=bool(request.form.get("laundry")),
            water=bool(request.form.get("water")),
            electricity=bool(request.form.get("electricity")),
            pets_allowed=bool(request.form.get("pets_allowed")),
            latitude=float(request.form.get("latitude") or 0) if request.form.get("latitude") else 0,
            longitude=float(request.form.get("longitude") or 0) if request.form.get("longitude") else 0,
            maps_link=request.form.get("maps_link", "").strip(),
            contact_number=request.form.get("contact_number", "").strip(),
            contact_email=request.form.get("contact_email", "").strip(),
            facebook_link=request.form.get("facebook_link", "").strip(),
            messenger_link=request.form.get("messenger_link", "").strip(),
            available=bool(request.form.get("available")),
            owner_id=user.id,
        )
        db.session.add(prop)
        db.session.commit()

        files = request.files.getlist("images")
        for f in files:
            saved = save_uploaded_file(f, "properties")
            if saved:
                db.session.add(Image(filename=saved, property_id=prop.id))
        db.session.commit()

        flash("Property posted successfully!", "success")
        return redirect(url_for("property_detail", property_id=prop.id))
    return render_template_string(PROPERTY_FORM_TEMPLATE, property=None)


@app.route("/property/<int:property_id>/edit", methods=["GET", "POST"])
@login_required
def edit_property(property_id):
    prop = Property.query.get_or_404(property_id)
    user = get_current_user()
    if prop.owner_id != user.id and not user.is_admin:
        abort(403)

    if request.method == "POST":
        prop.title = request.form.get("title", prop.title).strip()
        prop.description = request.form.get("description", "").strip()
        prop.category = request.form.get("category", prop.category)
        prop.price = float(request.form.get("price") or 0)
        prop.address = request.form.get("address", "").strip()
        prop.city = request.form.get("city", "").strip()
        prop.province = request.form.get("province", "").strip()
        prop.bedrooms = int(request.form.get("bedrooms") or 0)
        prop.bathrooms = int(request.form.get("bathrooms") or 0)
        prop.floor_area = float(request.form.get("floor_area") or 0)
        prop.lot_area = float(request.form.get("lot_area") or 0)
        prop.parking = bool(request.form.get("parking"))
        prop.wifi = bool(request.form.get("wifi"))
        prop.aircon = bool(request.form.get("aircon"))
        prop.kitchen = bool(request.form.get("kitchen"))
        prop.laundry = bool(request.form.get("laundry"))
        prop.water = bool(request.form.get("water"))
        prop.electricity = bool(request.form.get("electricity"))
        prop.pets_allowed = bool(request.form.get("pets_allowed"))
        prop.latitude = float(request.form.get("latitude") or 0) if request.form.get("latitude") else 0
        prop.longitude = float(request.form.get("longitude") or 0) if request.form.get("longitude") else 0
        prop.maps_link = request.form.get("maps_link", "").strip()
        prop.contact_number = request.form.get("contact_number", "").strip()
        prop.contact_email = request.form.get("contact_email", "").strip()
        prop.facebook_link = request.form.get("facebook_link", "").strip()
        prop.messenger_link = request.form.get("messenger_link", "").strip()
        prop.available = bool(request.form.get("available"))

        files = request.files.getlist("images")
        for f in files:
            saved = save_uploaded_file(f, "properties")
            if saved:
                db.session.add(Image(filename=saved, property_id=prop.id))

        db.session.commit()
        flash("Property updated successfully!", "success")
        return redirect(url_for("property_detail", property_id=prop.id))

    return render_template_string(PROPERTY_FORM_TEMPLATE, property=prop)


@app.route("/property/<int:property_id>/delete", methods=["POST"])
@login_required
def delete_property(property_id):
    prop = Property.query.get_or_404(property_id)
    user = get_current_user()
    if prop.owner_id != user.id and not user.is_admin:
        abort(403)
    db.session.delete(prop)
    db.session.commit()
    flash("Property deleted.", "info")
    if user.is_admin and prop.owner_id != user.id:
        return redirect(url_for("admin_listings"))
    return redirect(url_for("my_listings"))


@app.route("/property/image/<int:image_id>/delete")
@login_required
def delete_property_image(image_id):
    img = Image.query.get_or_404(image_id)
    prop = Property.query.get(img.property_id)
    user = get_current_user()
    if prop.owner_id != user.id and not user.is_admin:
        abort(403)
    db.session.delete(img)
    db.session.commit()
    flash("Image removed.", "info")
    return redirect(url_for("edit_property", property_id=prop.id))


@app.route("/property/<int:property_id>")
def property_detail(property_id):
    prop = Property.query.get_or_404(property_id)
    prop.views = (prop.views or 0) + 1
    db.session.commit()

    user = get_current_user()
    is_favorited = False
    if user:
        is_favorited = Favorite.query.filter_by(user_id=user.id, property_id=prop.id).first() is not None

    return render_template_string(
        PROPERTY_DETAIL_TEMPLATE, property=prop, user=user, is_favorited=is_favorited
    )


@app.route("/property/<int:property_id>/contact", methods=["POST"])
def contact_owner(property_id):
    prop = Property.query.get_or_404(property_id)
    msg = Message(
        sender_name=request.form.get("sender_name", "").strip(),
        sender_email=request.form.get("sender_email", "").strip(),
        sender_phone=request.form.get("sender_phone", "").strip(),
        content=request.form.get("content", "").strip(),
        property_id=prop.id,
        owner_id=prop.owner_id,
    )
    db.session.add(msg)
    db.session.commit()
    flash("Your message has been sent to the owner!", "success")
    return redirect(url_for("property_detail", property_id=prop.id))


@app.route("/property/<int:property_id>/report", methods=["GET", "POST"])
def report_property(property_id):
    prop = Property.query.get_or_404(property_id)
    if request.method == "POST":
        report = Report(
            reporter_name=request.form.get("reporter_name", "").strip(),
            reporter_email=request.form.get("reporter_email", "").strip(),
            reason=request.form.get("reason", "").strip(),
            property_id=prop.id,
        )
        db.session.add(report)
        db.session.commit()
        flash("Thank you. Your report has been submitted to our team.", "success")
        return redirect(url_for("property_detail", property_id=prop.id))
    return render_template_string(REPORT_TEMPLATE, property=prop)


@app.route("/favorite/<int:property_id>/toggle", methods=["POST"])
@login_required
def toggle_favorite(property_id):
    user = get_current_user()
    fav = Favorite.query.filter_by(user_id=user.id, property_id=property_id).first()
    if fav:
        db.session.delete(fav)
        flash("Removed from favorites.", "info")
    else:
        db.session.add(Favorite(user_id=user.id, property_id=property_id))
        flash("Added to favorites!", "success")
    db.session.commit()
    return redirect(url_for("property_detail", property_id=property_id))


# ------------------------------------------------------------------ SEARCH ----

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    bedrooms = request.args.get("bedrooms", "").strip()
    sort = request.args.get("sort", "newest").strip()
    page = int(request.args.get("page", 1) or 1)
    per_page = 9

    query = Property.query.filter_by(available=True)

    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Property.title.ilike(like), Property.description.ilike(like)))
    if category:
        query = query.filter(Property.category == category)
    if location:
        like_loc = f"%{location}%"
        query = query.filter(db.or_(Property.city.ilike(like_loc), Property.province.ilike(like_loc)))
    if min_price:
        query = query.filter(Property.price >= float(min_price))
    if max_price:
        query = query.filter(Property.price <= float(max_price))
    if bedrooms:
        query = query.filter(Property.bedrooms >= int(bedrooms))

    if sort == "oldest":
        query = query.order_by(Property.date_posted.asc())
    elif sort == "price_low":
        query = query.order_by(Property.price.asc())
    elif sort == "price_high":
        query = query.order_by(Property.price.desc())
    else:
        query = query.order_by(Property.date_posted.desc())

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(1, page), total_pages)
    properties = query.offset((page - 1) * per_page).limit(per_page).all()

    filters = {
        "q": q, "category": category, "location": location, "min_price": min_price,
        "max_price": max_price, "bedrooms": bedrooms, "sort": sort,
    }

    return render_template_string(
        SEARCH_TEMPLATE, properties=properties, filters=filters, total=total,
        page=page, total_pages=total_pages,
    )


# ------------------------------------------------------------------- ADMIN ----

@app.route("/admin")
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_listings = Property.query.count()
    total_messages = Message.query.count()
    pending_reports = Report.query.filter_by(resolved=False).count()
    return render_template_string(
        ADMIN_DASHBOARD_TEMPLATE, total_users=total_users, total_listings=total_listings,
        total_messages=total_messages, pending_reports=pending_reports,
    )


@app.route("/admin/users")
@admin_required
def admin_users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.full_name.ilike(like), User.email.ilike(like)))
    users = query.order_by(User.date_joined.desc()).all()
    return render_template_string(ADMIN_USERS_TEMPLATE, users=users, q=q)


@app.route("/admin/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def admin_toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"Updated admin status for {user.full_name}.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == get_current_user().id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "info")
    return redirect(url_for("admin_users"))


@app.route("/admin/listings")
@admin_required
def admin_listings():
    properties = Property.query.order_by(Property.date_posted.desc()).all()
    return render_template_string(ADMIN_LISTINGS_TEMPLATE, properties=properties)


@app.route("/admin/listings/<int:property_id>/toggle-featured", methods=["POST"])
@admin_required
def admin_toggle_featured(property_id):
    prop = Property.query.get_or_404(property_id)
    prop.featured = not prop.featured
    db.session.commit()
    flash("Listing updated.", "success")
    return redirect(url_for("admin_listings"))


@app.route("/admin/reports")
@admin_required
def admin_reports():
    reports = Report.query.order_by(Report.date_reported.desc()).all()
    return render_template_string(ADMIN_REPORTS_TEMPLATE, reports=reports)


@app.route("/admin/reports/<int:report_id>/resolve", methods=["POST"])
@admin_required
def admin_resolve_report(report_id):
    report = Report.query.get_or_404(report_id)
    report.resolved = True
    db.session.commit()
    flash("Report marked as resolved.", "success")
    return redirect(url_for("admin_reports"))


# ==============================================================================
# ERROR HANDLERS
# ==============================================================================

ERROR_TEMPLATE = """
{% extends 'base.html' %}
{% block title %}{{ code }}{% endblock %}
{% block content %}
<div class="container my-5 text-center">
  <h1 class="display-1 text-primary">{{ code }}</h1>
  <p class="lead">{{ message }}</p>
  <a href="{{ url_for('index') }}" class="btn btn-primary text-white">Go Home</a>
</div>
{% endblock %}
"""


@app.errorhandler(403)
def forbidden(e):
    return render_template_string(ERROR_TEMPLATE, code=403, message="You don't have permission to access this page."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template_string(ERROR_TEMPLATE, code=404, message="Page not found."), 404


@app.errorhandler(413)
def too_large(e):
    return render_template_string(ERROR_TEMPLATE, code=413, message="Uploaded file is too large."), 413


# ==============================================================================
# DATABASE INITIALIZATION (auto-creates DB, folders, categories, admin user)
# ==============================================================================

def initialize_database():
    with app.app_context():
        db.create_all()

        # Seed categories
        for cat_name in CATEGORIES:
            if not Category.query.filter_by(name=cat_name).first():
                db.session.add(Category(name=cat_name, icon=CATEGORY_ICONS.get(cat_name, "bi-grid")))
        db.session.commit()

        # Seed default admin account
        if not User.query.filter_by(email="admin@renthub.com").first():
            admin = User(
                full_name="RentHub Admin",
                email="admin@renthub.com",
                phone="",
                is_admin=True,
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("=" * 70)
            print(" Default admin account created:")
            print("   Email:    admin@renthub.com")
            print("   Password: admin123")
            print(" Please log in and change this password right away!")
            print("=" * 70)


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    initialize_database()
    print("RentHub is starting... open http://127.0.0.1:5000 in your browser")
    app.run(host="0.0.0.0", port=5000, debug=True)
