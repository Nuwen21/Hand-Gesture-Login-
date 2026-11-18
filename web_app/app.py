from flask import Flask, jsonify, request, render_template
import os

import database
import security

app = Flask(__name__)

# Initialize database on startup
database.init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/check_user", methods=["POST"])
def check_user():
    data = request.json or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username cannot be empty"}), 400

    user = database.get_user(username)
    if not user:
        return jsonify({"exists": False})

    locked = database.is_locked(user)
    lock_remaining = database.lock_remaining_seconds(user) if locked else 0

    return jsonify({
        "exists": True,
        "locked": locked,
        "lock_remaining": lock_remaining
    })


@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    gesture_sequence = data.get("gesture_sequence", "")

    if not username or not password or not gesture_sequence:
        return jsonify({"success": False, "message": "All fields are required"}), 400

    # Salt and hash password and gestures
    password_salt, password_hash = security.hash_secret(password)
    gesture_salt, gesture_hash = security.hash_secret(gesture_sequence)

    success = database.create_user(username, password_salt, password_hash, gesture_salt, gesture_hash)
    if success:
        database.log_login(username, "REGISTERED", f"gesture_length={len(gesture_sequence.split('-'))}")
        return jsonify({"success": True, "message": "User registered successfully"})
    else:
        return jsonify({"success": False, "message": "Username already exists"}), 400


@app.route("/api/login_password", methods=["POST"])
def login_password():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    user = database.get_user(username)
    if not user:
        database.log_login(username, "FAILED", "unknown username")
        return jsonify({"success": False, "message": "Incorrect username or password"}), 400

    # Check lock
    if database.is_locked(user):
        remaining = database.lock_remaining_seconds(user)
        database.log_login(username, "FAILED", "account locked")
        return jsonify({
            "success": False, 
            "message": f"Account is temporarily locked. Try again in {remaining} seconds."
        }), 403

    # Verify Password
    if not security.verify_secret(password, user["password_salt"], user["password_hash"]):
        database.record_failed_attempt(username)
        database.log_login(username, "FAILED", "wrong password")
        return jsonify({"success": False, "message": "Incorrect username or password"}), 400

    return jsonify({"success": True, "message": "Password verified successfully"})


@app.route("/api/login_gesture", methods=["POST"])
def login_gesture():
    data = request.json or {}
    username = data.get("username", "").strip()
    gesture_sequence = data.get("gesture_sequence", "")

    if not username or not gesture_sequence:
        return jsonify({"success": False, "message": "Username and gesture sequence are required"}), 400

    user = database.get_user(username)
    if not user:
        database.log_login(username, "FAILED", "unknown username (gesture stage)")
        return jsonify({"success": False, "message": "Login failed"}), 400

    # Double check lock
    if database.is_locked(user):
        remaining = database.lock_remaining_seconds(user)
        database.log_login(username, "FAILED", "account locked (gesture stage)")
        return jsonify({
            "success": False,
            "message": f"Account is locked. Try again in {remaining} seconds."
        }), 403

    # Verify gesture sequence
    if security.verify_secret(gesture_sequence, user["gesture_salt"], user["gesture_hash"]):
        database.reset_failed_attempts(username)
        database.log_login(username, "SUCCESS", "password and gesture matched")
        return jsonify({"success": True, "message": "Login successful!"})
    else:
        database.record_failed_attempt(username)
        database.log_login(username, "FAILED", "wrong gesture")
        
        # Check if the attempt triggered a lock
        updated_user = database.get_user(username)
        locked = database.is_locked(updated_user)
        remaining = database.lock_remaining_seconds(updated_user) if locked else 0

        return jsonify({
            "success": False,
            "message": "Gesture sequence did not match",
            "locked": locked,
            "lock_remaining": remaining
        }), 400


@app.route("/api/logs", methods=["GET"])
def get_logs():
    rows = database.show_logs(limit=30)
    logs = []
    for row in rows:
        logs.append({
            "created_at": row["created_at"],
            "username": row["username"],
            "status": row["status"],
            "reason": row["reason"]
        })
    return jsonify(logs)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
