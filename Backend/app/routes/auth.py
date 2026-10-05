from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from ..extensions import bcrypt, db
from ..models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # Required fields
    if not full_name or not email or not password:
        return jsonify({
            "error": "Full name, email and password are required"
        }), 400

    # Full name validation
    if len(full_name) < 10:
        return jsonify({
            "error": "Full name must contain at least 10 characters"
        }), 400

    # Password length
    if len(password) < 8:
        return jsonify({
            "error": "Password must contain at least 8 characters"
        }), 400

    # Password number requirement
    if not any(char.isdigit() for char in password):
        return jsonify({
            "error": "Password must contain at least one number"
        }), 400

    # Basic email validation
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({
            "error": "Please enter a valid email address"
        }), 400

    # Hash password
    password_hash = bcrypt.generate_password_hash(
        password
    ).decode("utf-8")

    user = User(
        full_name=full_name,
        email=email,
        password_hash=password_hash
    )

    db.session.add(user)

    try:
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "error": "An account with this email already exists"
        }), 409

    return jsonify({
        "message": "Account created successfully",
        "user": user.to_dict()
    }), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    user = User.query.filter_by(
        email=email
    ).first()

    if not user or not bcrypt.check_password_hash(
        user.password_hash,
        password
    ):
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "message": "Login successful",
        "access_token": token,
        "user": user.to_dict()
    }), 200