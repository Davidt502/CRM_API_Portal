"""
routes/portal_routes.py — Rutas del portal web (páginas HTML)
"""
import logging
from flask import Blueprint, render_template, redirect, url_for

logger = logging.getLogger(__name__)
portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


@portal_bp.route("/")
def index():
    return redirect(url_for("portal.login"))

@portal_bp.route("/login")
def login():
    return render_template("login.html")

@portal_bp.route("/register")
def register():
    return render_template("register.html")

@portal_bp.route("/docs")
def docs():
    return render_template("swagger.html")

@portal_bp.route("/reportes")
def reportes():
    return render_template("reports.html")

@portal_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")
