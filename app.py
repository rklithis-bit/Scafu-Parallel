import os, sqlite3, secrets, time
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
from firebase_admin import credentials, initialize_app, auth as firebase_auth, _apps
import requests

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", str(ROOT / "instance" / "scafu.db")))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_FOLDER", str(ROOT / "static" / "uploads")))
ALLOWED = {"png", "jpg", "jpeg", "gif", "webp"}
PRIVATE_EMAILS = {"lichu@scafu.app", "ammu@scafu.app"}
MAX_UPLOAD = 10 * 1024 * 1024

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("Set FLASK_SECRET_KEY in your environment.")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
FIREBASE_WEB_API_KEY = os.environ.get("FIREBASE_WEB_API_KEY")

def init_firebase():
    if _apps:
        return
    values = {
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
    }
    if not all(values.values()):
        raise RuntimeError("Firebase Admin credentials are missing from environment variables.")
    initialize_app(credentials.Certificate({
        "type": "service_account",
        **values,
        "private_key": values["private_key"],
        "token_uri": "https://oauth2.googleapis.com/token",
    }))

def db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, email TEXT NOT NULL UNIQUE,
            created_at INTEGER NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sender_uid TEXT NOT NULL,
            recipient_uid TEXT NOT NULL, body TEXT, image_name TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(sender_uid) REFERENCES users(uid),
            FOREIGN KEY(recipient_uid) REFERENCES users(uid))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS community_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sender_uid TEXT NOT NULL,
            sender_username TEXT NOT NULL, body TEXT, image_name TEXT,
            created_at INTEGER NOT NULL)""")
init_db()

def api_login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("uid"):
            return jsonify({"error": "Please sign in again."}), 401
        return fn(*args, **kwargs)
    return wrapped


def firebase_rest(action, email, password):
    if not FIREBASE_WEB_API_KEY:
        raise RuntimeError("FIREBASE_WEB_API_KEY is not configured.")

    endpoints = {
        "signup": "accounts:signUp",
        "signin": "accounts:signInWithPassword",
    }

    response = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/"
        f"{endpoints[action]}?key={FIREBASE_WEB_API_KEY}",
        json={
            "email": email,
            "password": password,
            "returnSecureToken": True,
        },
        timeout=12,
    )

    data = response.json()

    if response.status_code != 200:
        error = data.get("error", {}).get("message", "AUTH_FAILED")

        if error == "EMAIL_EXISTS":
            raise ValueError("EMAIL_EXISTS")

        if error in ("INVALID_LOGIN_CREDENTIALS", "EMAIL_NOT_FOUND",
                     "INVALID_PASSWORD"):
            raise ValueError("Email or password is incorrect.")

        if error == "WEAK_PASSWORD":
            raise ValueError("Use a password with at least 6 characters.")

        if error == "INVALID_EMAIL":
            raise ValueError("Enter a valid email address.")

        raise ValueError("Firebase authentication failed: " + error)

    return data


@app.get("/")
def index():
    if session.get("uid"):
        return redirect(url_for("chat_page"))
    return render_template("index.html", firebase_api_key=FIREBASE_WEB_API_KEY or "")

@app.post("/api/auth/<action>")

@app.post("/api/auth/<action>")
def auth_action(action):
    if action not in {"signup", "signin"}:
        return jsonify(error="Unknown authentication action."), 404

    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    username = str(payload.get("username", "")).strip()

    if not email or not password or (action == "signup" and not username):
        return jsonify(error="Complete all required fields."), 400

    if action == "signup" and (
        len(username) < 3
        or len(username) > 24
        or not username.replace("_", "").isalnum()
    ):
        return jsonify(
            error="Username must be 3–24 letters, numbers or underscores."
        ), 400

    try:
        # If Firebase already has this email, authenticate the existing
        # account instead of trying to create it again.
        try:
            result = firebase_rest(action, email, password)
        except ValueError as exc:
            if action != "signup" or str(exc) != "EMAIL_EXISTS":
                raise
            result = firebase_rest("signin", email, password)

        init_firebase()
        decoded = firebase_auth.verify_id_token(
            result["idToken"], check_revoked=False
        )
        uid = decoded["uid"]

        with db() as conn:
            row = conn.execute(
                "SELECT username FROM users WHERE uid = ?", (uid,)
            ).fetchone()

            if row:
                username = row["username"]
            else:
                if action != "signup":
                    return jsonify(
                        error=(
                            "Your Firebase account exists, but its app profile "
                            "is missing. Choose Create Account and enter a "
                            "username to restore it."
                        )
                    ), 403

                try:
                    conn.execute(
                        """INSERT INTO users(uid, username, email, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (uid, username, email, int(time.time())),
                    )
                except sqlite3.IntegrityError:
                    return jsonify(
                        error=(
                            "That username or email is already used in the "
                            "app database. Try a different username."
                        )
                    ), 409

        session.clear()
        session["uid"] = uid
        session["username"] = username
        session["email"] = email

        return jsonify(ok=True, redirect=url_for("chat_page"))

    except ValueError as exc:
        if str(exc) == "EMAIL_EXISTS":
            return jsonify(
                error="This email already has an account. Sign in instead."
            ), 400
        return jsonify(error=str(exc)), 400

    except requests.RequestException:
        return jsonify(
            error="Could not reach Firebase. Try again shortly."
        ), 503

    except Exception:
        app.logger.exception("Authentication failed")
        return jsonify(
            error=(
                "Authentication setup error. Check Render environment "
                "variables and Firebase configuration."
            )
        ), 500


@app.get("/chat")
def chat_page():
    if not session.get("uid"):
        return redirect(url_for("index"))
    email = current_email()
    return render_template("chat.html", username=session["username"],
                           private_allowed=email in PRIVATE_EMAILS)

def current_email():
    email = str(session.get("email", "")).strip().lower()
    if email:
        return email
    uid = session.get("uid")
    if not uid:
        return ""
    with db() as conn:
        row = conn.execute("SELECT email FROM users WHERE uid=?", (uid,)).fetchone()
    email = str(row["email"] if row else "").strip().lower()
    if email:
        session["email"] = email
    return email

def private_allowed():
    return current_email() in PRIVATE_EMAILS

def private_forbidden():
    return jsonify(error="Private chat is only available to the two authorized accounts."), 403

@app.get("/api/users")
@api_login_required
def list_users():
    if not private_allowed():
        return private_forbidden()
    with db() as conn:
        rows = conn.execute("""SELECT username FROM users
            WHERE uid != ? AND lower(email) IN (?, ?) ORDER BY username""",
            (session["uid"], *sorted(PRIVATE_EMAILS))).fetchall()
    return jsonify(users=[r["username"] for r in rows])

@app.get("/api/messages")
@api_login_required
def get_messages():
    if not private_allowed():
        return private_forbidden()
    peer = request.args.get("with", "").strip()
    if not peer:
        return jsonify(messages=[])
    with db() as conn:
        other = conn.execute("SELECT uid, username, email FROM users WHERE username=?", (peer,)).fetchone()
        if not other or other["email"].strip().lower() not in PRIVATE_EMAILS or other["uid"] == session["uid"]:
            return jsonify(error="Private chat is only available between the two authorized accounts."), 403
        rows = conn.execute("""SELECT m.id, m.sender_uid, m.body, m.image_name, m.created_at, u.username AS sender
          FROM messages m JOIN users u ON u.uid=m.sender_uid
          WHERE (m.sender_uid=? AND m.recipient_uid=?) OR (m.sender_uid=? AND m.recipient_uid=?)
          ORDER BY m.id DESC LIMIT 200""",
          (session["uid"], other["uid"], other["uid"], session["uid"])).fetchall()
    items = []
    for r in reversed(rows):
        items.append({"id": r["id"], "sender": r["sender"], "mine": r["sender_uid"] == session["uid"],
                      "body": r["body"], "image": url_for("uploaded_file", filename=r["image_name"]) if r["image_name"] else None,
                      "time": time.strftime("%H:%M", time.localtime(r["created_at"]))})
    return jsonify(messages=items)

@app.post("/api/messages")
@api_login_required
def send_message():
    if not private_allowed():
        return private_forbidden()
    peer = request.form.get("to", "").strip()
    body = request.form.get("message", "").strip()
    image = request.files.get("image")
    if len(body) > 4000:
        return jsonify(error="Messages must be under 4,000 characters."), 400
    image_name = None
    if image and image.filename:
        ext = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
        if ext not in ALLOWED:
            return jsonify(error="Use PNG, JPG, GIF or WEBP images."), 400
        safe = secure_filename(image.filename) or "image"
        image_name = f"{secrets.token_hex(16)}_{safe}"
        image.save(UPLOAD_DIR / image_name)
    if not body and not image_name:
        return jsonify(error="Write a message or choose an image."), 400
    with db() as conn:
        other = conn.execute("SELECT uid, email FROM users WHERE username=?", (peer,)).fetchone()
        if not other or other["email"].strip().lower() not in PRIVATE_EMAILS or other["uid"] == session["uid"]:
            if image_name: (UPLOAD_DIR / image_name).unlink(missing_ok=True)
            return jsonify(error="Private messages can only be sent to the other authorized account."), 403
        conn.execute("INSERT INTO messages(sender_uid,recipient_uid,body,image_name,created_at) VALUES(?,?,?,?,?)",
                     (session["uid"], other["uid"], body or None, image_name, int(time.time())))
    return jsonify(ok=True)

@app.get("/api/community/messages")
@api_login_required
def get_community_messages():
    with db() as conn:
        rows = conn.execute("""SELECT id, sender_uid, sender_username, body, image_name, created_at
            FROM community_messages ORDER BY id DESC LIMIT 200""").fetchall()
    items = []
    for r in reversed(rows):
        items.append({"id": r["id"], "sender": r["sender_username"],
                      "mine": r["sender_uid"] == session["uid"], "body": r["body"],
                      "image": url_for("uploaded_file", filename=r["image_name"]) if r["image_name"] else None,
                      "time": time.strftime("%H:%M", time.localtime(r["created_at"]))})
    return jsonify(messages=items)

@app.post("/api/community/messages")
@api_login_required
def send_community_message():
    body = request.form.get("message", "").strip()
    image = request.files.get("image")
    if len(body) > 4000:
        return jsonify(error="Messages must be under 4,000 characters."), 400
    image_name = None
    if image and image.filename:
        ext = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
        if ext not in ALLOWED:
            return jsonify(error="Use PNG, JPG, GIF or WEBP images."), 400
        safe = secure_filename(image.filename) or "image"
        image_name = f"{secrets.token_hex(16)}_{safe}"
        image.save(UPLOAD_DIR / image_name)
    if not body and not image_name:
        return jsonify(error="Write a message or choose an image."), 400
    with db() as conn:
        conn.execute("""INSERT INTO community_messages(sender_uid, sender_username, body, image_name, created_at)
            VALUES(?,?,?,?,?)""",
            (session["uid"], session["username"], body or None, image_name, int(time.time())))
    return jsonify(ok=True)

@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    # Only allow image files that have a known generated filename.
    from flask import send_from_directory, abort
    if "/" in filename or "\\" in filename:
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename, max_age=3600)

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.errorhandler(413)
def too_large(_):
    return jsonify(error="Image is too large. Maximum size is 10 MB."), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
