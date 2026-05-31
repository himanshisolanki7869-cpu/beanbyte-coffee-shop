from __future__ import annotations

import json
import os
import secrets
import sqlite3
from html import escape
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "beanbyte.db"

MENU_ITEMS = [
    {"id": "cappuccino", "name": "Cappuccino", "price": 180, "category": "Hot Coffee"},
    {"id": "mocha", "name": "Mocha", "price": 250, "category": "Signature"},
    {"id": "caramel_macchiato", "name": "Caramel Macchiato", "price": 240, "category": "Signature"},
    {"id": "frappuccino", "name": "Frappuccino", "price": 260, "category": "Cold Coffee"},
    {"id": "iced_latte", "name": "Iced Latte", "price": 169, "category": "Cold Coffee"},
]


app = Flask(__name__, static_folder=None)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-this-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        return db.execute(
            "SELECT id, username, email, is_owner FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user["is_owner"]:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Owner login required."}), 403
            return redirect("/login.html?next=/admin")
        return view(*args, **kwargs)

    return wrapped


def init_db() -> None:
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_owner INTEGER NOT NULL DEFAULT 0,
                reset_token TEXT,
                reset_expires_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );
            """
        )

        user_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()
        }
        if "email" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN email TEXT")
            db.execute(
                "UPDATE users SET email = username || '@beanbyte.local' WHERE email IS NULL"
            )
        if "reset_token" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        if "reset_expires_at" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN reset_expires_at TEXT")
        if "created_at" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
            db.execute(
                "UPDATE users SET created_at = ? WHERE created_at IS NULL",
                (utc_now().isoformat(),),
            )
        if "is_owner" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN is_owner INTEGER NOT NULL DEFAULT 0")

        order_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(orders)").fetchall()
        }
        order_migrations = {
            "customer_name": "ALTER TABLE orders ADD COLUMN customer_name TEXT",
            "customer_phone": "ALTER TABLE orders ADD COLUMN customer_phone TEXT",
            "fulfillment": "ALTER TABLE orders ADD COLUMN fulfillment TEXT DEFAULT 'pickup'",
            "status": "ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'new'",
        }
        for column, statement in order_migrations.items():
            if column not in order_columns:
                db.execute(statement)

        admin = db.execute(
            "SELECT id FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if not admin:
            db.execute(
                """
                INSERT INTO users (username, email, password_hash, is_owner, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "admin",
                    "admin@beanbyte.com",
                    generate_password_hash("coffee123"),
                    1,
                    utc_now().isoformat(),
                ),
            )
        else:
            db.execute("UPDATE users SET is_owner = 1 WHERE username = ?", ("admin",))


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    response.headers["Access-Control-Allow-Origin"] = origin or "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/login")
def login_page():
    return redirect("/login.html")


@app.route("/<path:filename>")
def static_files(filename):
    allowed_suffixes = {
        ".html",
        ".css",
        ".js",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".ico",
    }
    path = BASE_DIR / filename
    if path.is_file() and path.suffix.lower() in allowed_suffixes:
        return send_from_directory(BASE_DIR, filename)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/menu")
def api_menu():
    return jsonify(MENU_ITEMS)


@app.route("/api/contact", methods=["POST", "OPTIONS"])
def api_contact():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    message = (data.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"error": "Name, email, and message are required."}), 400

    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO contacts (name, email, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, message, utc_now().isoformat()),
        )

    return jsonify({"message": "Contact message saved.", "id": cursor.lastrowid}), 201


@app.route("/api/order", methods=["POST", "OPTIONS"])
def api_order():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    total = data.get("total")
    customer = data.get("customer") or {}
    customer_name = (customer.get("name") or "").strip()
    customer_phone = (customer.get("phone") or "").strip()
    fulfillment = (customer.get("fulfillment") or "pickup").strip().lower()

    if not isinstance(items, list) or not items:
        return jsonify({"error": "Order must include at least one item."}), 400
    if not customer_name or not customer_phone:
        return jsonify({"error": "Customer name and phone are required."}), 400
    if fulfillment not in {"pickup", "dine-in"}:
        return jsonify({"error": "Fulfillment must be pickup or dine-in."}), 400

    try:
        total_value = float(total)
    except (TypeError, ValueError):
        return jsonify({"error": "Order total must be a number."}), 400

    cleaned_items = []
    for item in items:
        product_id = str(item.get("id", "")).strip()
        try:
            qty = int(item.get("qty", 0))
        except (TypeError, ValueError):
            qty = 0
        if not product_id or qty < 1:
            return jsonify({"error": "Each item needs an id and quantity."}), 400
        cleaned_items.append((product_id, qty))

    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO orders
                (total, customer_name, customer_phone, fulfillment, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                total_value,
                customer_name,
                customer_phone,
                fulfillment,
                "new",
                utc_now().isoformat(),
            ),
        )
        order_id = cursor.lastrowid
        db.executemany(
            """
            INSERT INTO order_items (order_id, product_id, quantity)
            VALUES (?, ?, ?)
            """,
            [(order_id, product_id, qty) for product_id, qty in cleaned_items],
        )

    return jsonify({"message": "Order placed.", "order_id": order_id}), 201


@app.route("/api/orders")
@owner_required
def api_orders():
    with get_db() as db:
        rows = db.execute(
            """
            SELECT o.id, o.total, o.customer_name, o.customer_phone,
                   o.fulfillment, o.status, o.created_at,
                   json_group_array(
                       json_object('id', oi.product_id, 'qty', oi.quantity)
                   ) AS items
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            GROUP BY o.id
            ORDER BY o.id DESC
            """
        ).fetchall()

    return jsonify(
        [
            {
                "id": row["id"],
                "total": row["total"],
                "customer_name": row["customer_name"],
                "customer_phone": row["customer_phone"],
                "fulfillment": row["fulfillment"],
                "status": row["status"],
                "created_at": row["created_at"],
                "items": json.loads(row["items"] or "[]"),
            }
            for row in rows
        ]
    )


@app.route("/api/database")
@owner_required
def api_database():
    with get_db() as db:
        contacts = db.execute(
            "SELECT id, name, email, message, created_at FROM contacts ORDER BY id DESC"
        ).fetchall()
        orders = db.execute(
            """
            SELECT o.id, o.total, o.customer_name, o.customer_phone,
                   o.fulfillment, o.status, o.created_at,
                   group_concat(oi.product_id || ' x ' || oi.quantity, ', ') AS items
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            GROUP BY o.id
            ORDER BY o.id DESC
            """
        ).fetchall()
        users = db.execute(
            "SELECT id, username, email, is_owner, created_at FROM users ORDER BY id"
        ).fetchall()

    return jsonify(
        {
            "orders": [dict(row) for row in orders],
            "contacts": [dict(row) for row in contacts],
            "users": [dict(row) for row in users],
        }
    )


@app.route("/api/login", methods=["POST", "OPTIONS"])
def api_login():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    with get_db() as db:
        user = db.execute(
            """
            SELECT id, username, email, password_hash, is_owner
            FROM users
            WHERE username = ? OR email = ?
            """,
            (username, username.lower()),
        ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password."}), 401

    session.clear()
    session["user_id"] = user["id"]
    session["is_owner"] = bool(user["is_owner"])

    return jsonify(
        {
            "message": "Login successful.",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_owner": bool(user["is_owner"]),
            },
        }
    )


@app.route("/api/signup", methods=["POST", "OPTIONS"])
def api_signup():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400
    if "@" not in email or "." not in email:
        return jsonify({"error": "Enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    try:
        with get_db() as db:
            cursor = db.execute(
                """
                INSERT INTO users (username, email, password_hash, is_owner, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    email,
                    generate_password_hash(password),
                    0,
                    utc_now().isoformat(),
                ),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists."}), 409

    session.clear()
    session["user_id"] = user_id
    session["is_owner"] = False

    return jsonify(
        {
            "message": "Account created successfully.",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "is_owner": False,
            },
        }
    ), 201


@app.route("/api/me")
def api_me():
    user = current_user()
    if not user:
        return jsonify({"authenticated": False})
    return jsonify(
        {
            "authenticated": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_owner": bool(user["is_owner"]),
            },
        }
    )


@app.route("/api/logout", methods=["POST", "OPTIONS"])
def api_logout():
    if request.method == "OPTIONS":
        return ("", 204)
    session.clear()
    return jsonify({"message": "Logged out."})


@app.route("/api/forgot-password", methods=["POST", "OPTIONS"])
def api_forgot_password():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    identifier = (data.get("email") or data.get("username") or "").strip().lower()
    if not identifier:
        return jsonify({"error": "Email or username is required."}), 400

    with get_db() as db:
        user = db.execute(
            "SELECT id FROM users WHERE lower(email) = ? OR lower(username) = ?",
            (identifier, identifier),
        ).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = (utc_now() + timedelta(hours=1)).isoformat()
            db.execute(
                """
                UPDATE users
                SET reset_token = ?, reset_expires_at = ?
                WHERE id = ?
                """,
                (token, expires_at, user["id"]),
            )
        else:
            token = None

    # Demo app behavior: return the token instead of sending email.
    response = {
        "message": "If the account exists, a reset link has been created."
    }
    if token:
        response["reset_token"] = token
        response["reset_link"] = f"/login.html?reset_token={token}"
    return jsonify(response)


@app.route("/api/reset-password", methods=["POST", "OPTIONS"])
def api_reset_password():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    new_password = data.get("password") or ""

    if not token or len(new_password) < 6:
        return jsonify({"error": "Token and a 6+ character password are required."}), 400

    with get_db() as db:
        user = db.execute(
            """
            SELECT id, reset_expires_at
            FROM users
            WHERE reset_token = ?
            """,
            (token,),
        ).fetchone()

        if not user:
            return jsonify({"error": "Invalid reset token."}), 400

        expires_at = datetime.fromisoformat(user["reset_expires_at"])
        if expires_at < utc_now():
            return jsonify({"error": "Reset token has expired."}), 400

        db.execute(
            """
            UPDATE users
            SET password_hash = ?, reset_token = NULL, reset_expires_at = NULL
            WHERE id = ?
            """,
            (generate_password_hash(new_password), user["id"]),
        )

    return jsonify({"message": "Password has been reset. You can log in now."})


@app.route("/admin")
@owner_required
def admin():
    with get_db() as db:
        contacts = db.execute(
            "SELECT id, name, email, message, created_at FROM contacts ORDER BY id DESC"
        ).fetchall()
        orders = db.execute(
            """
            SELECT o.id, o.total, o.customer_name, o.customer_phone,
                   o.fulfillment, o.status, o.created_at,
                   group_concat(oi.product_id || ' x ' || oi.quantity, ', ') AS items
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            GROUP BY o.id
            ORDER BY o.id DESC
            """
        ).fetchall()

    contact_rows = "".join(
        f"<tr><td>{c['id']}</td><td>{escape(c['name'])}</td>"
        f"<td>{escape(c['email'])}</td><td>{escape(c['message'])}</td>"
        f"<td>{c['created_at']}</td></tr>"
        for c in contacts
    )
    order_rows = "".join(
        f"<tr><td>#{o['id']}</td><td>{escape(o['customer_name'] or '')}</td>"
        f"<td>{escape(o['customer_phone'] or '')}</td>"
        f"<td>{escape(o['items'] or '')}</td><td>&#8377;{o['total']}</td>"
        f"<td>{escape(o['fulfillment'] or '')}</td><td>{escape(o['status'] or '')}</td>"
        f"<td>{o['created_at']}</td></tr>"
        for o in orders
    )
    order_count = len(orders)
    contact_count = len(contacts)
    revenue = sum(float(o["total"] or 0) for o in orders)

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>BeanByte Admin</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 0; color: #2b1b14; background: #f6f0ea; }}
        header {{ background: #2c1a11; color: white; padding: 28px 40px; }}
        main {{ padding: 32px 40px; }}
        a {{ color: #8c471c; font-weight: 700; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, minmax(160px, 1fr)); gap: 16px; margin: 24px 0; }}
        .stat {{ background: white; border-radius: 8px; padding: 20px; border: 1px solid #eadfd5; }}
        .stat strong {{ display: block; font-size: 30px; margin-top: 8px; }}
        .panel {{ background: white; border: 1px solid #eadfd5; border-radius: 8px; padding: 20px; margin-bottom: 28px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; min-width: 760px; }}
        th, td {{ border-bottom: 1px solid #eee2d8; padding: 12px; text-align: left; vertical-align: top; }}
        th {{ background: #f6f0ea; font-size: 13px; text-transform: uppercase; letter-spacing: .04em; }}
        h1, h2, p {{ margin-top: 0; }}
      </style>
    </head>
    <body>
      <header>
        <h1>BeanByte Database Dashboard</h1>
        <p>Live SQLite records from orders, contacts, and users.</p>
      </header>
      <main>
        <p><a href="/">Back to shop</a> &nbsp; <a href="/api/database">View raw JSON database</a> &nbsp; <button id="logout-btn">Logout</button></p>
        <section class="stats">
          <div class="stat">Orders<strong>{order_count}</strong></div>
          <div class="stat">Messages<strong>{contact_count}</strong></div>
          <div class="stat">Revenue<strong>&#8377;{revenue:.0f}</strong></div>
        </section>
        <section class="panel">
          <h2>Orders</h2>
          <table>
            <thead><tr><th>ID</th><th>Customer</th><th>Phone</th><th>Items</th><th>Total</th><th>Type</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>{order_rows or '<tr><td colspan="8">No orders yet.</td></tr>'}</tbody>
          </table>
        </section>
        <section class="panel">
          <h2>Contact Messages</h2>
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Message</th><th>Created</th></tr></thead>
            <tbody>{contact_rows or '<tr><td colspan="5">No messages yet.</td></tr>'}</tbody>
          </table>
        </section>
      </main>
      <script>
        document.getElementById('logout-btn').addEventListener('click', async () => {{
          await fetch('/api/logout', {{ method: 'POST' }});
          window.location.href = '/login.html';
        }});
      </script>
    </body>
    </html>
    """


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
