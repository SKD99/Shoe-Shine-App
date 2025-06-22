from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import sqlite3, os, json, hashlib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_key"
CORS(app, supports_credentials=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "products.db")
IMAGE_FOLDER = os.path.join(BASE_DIR, "static")
PROFILE_FOLDER = os.path.join(IMAGE_FOLDER, "profiles")
os.makedirs(PROFILE_FOLDER, exist_ok=True)

def get_db():
    return sqlite3.connect(DB_PATH)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# === INIT TABLES ===
def init_tables():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT UNIQUE, password TEXT,
            phone TEXT, address TEXT, profile_pic TEXT DEFAULT '', wallet REAL DEFAULT 0.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT, customer_address TEXT, customer_phone TEXT,
            items TEXT, total REAL, payment_method TEXT, delivery_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER, name TEXT, price REAL,
            category TEXT, image TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_tables()

# === AUTH ROUTES ===
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    phone = data.get("phone")
    address = data.get("address")

    if not all([name, email, password]):
        return jsonify({"error": "Missing required fields"}), 400

    hashed = hashlib.sha256(password.encode()).hexdigest()

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (name, email, password, phone, address)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, hashed, phone, address))
        conn.commit()
        conn.close()
        return jsonify({"message": "Signup successful"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, phone, profile_pic FROM users
        WHERE email = ? AND password = ?
    """, (email, hashed_password))
    row = cursor.fetchone()
    conn.close()

    if row:
        user = {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "photo": row[4],
        }
        return jsonify({"user": user}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out successfully"}), 200

@app.route("/api/profile", methods=["GET"])
def get_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, email, phone, address, profile_pic, wallet FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify({
            "name": row[0], "email": row[1], "phone": row[2],
            "address": row[3], "photo": row[4], "wallet": row[5]
        })
    return jsonify({"error": "User not found"}), 404

# === PRODUCTS & STATIC ===
@app.route("/api/products")
def get_products():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, category, image, link FROM products")
    rows = cursor.fetchall()
    conn.close()
    products = [{"id": r[0], "name": r[1], "price": r[2], "category": r[3], "image": r[4], "link": r[5]} for r in rows]
    return jsonify(products)

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

# === ORDER ROUTES ===
@app.route("/api/orders", methods=["POST"])
def save_order():
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (customer_name, customer_address, customer_phone, items, total, payment_method, delivery_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["customer"]["name"],
        data["customer"]["address"],
        data["customer"]["phone"],
        json.dumps(data["items"]),
        data["total"],
        data["paymentMethod"],
        data["deliveryDate"]
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "Order placed"}), 201

@app.route("/api/orders", methods=["GET"])
def get_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_name, customer_address, customer_phone, items, total, payment_method, delivery_date FROM orders")
    rows = cursor.fetchall()
    conn.close()
    orders = [{
        "customer": {"name": r[0], "address": r[1], "phone": r[2]},
        "items": json.loads(r[3]), "total": r[4],
        "paymentMethod": r[5], "deliveryDate": r[6]
    } for r in rows]
    return jsonify(orders)

# === WISHLIST ===
@app.route("/api/wishlist", methods=["POST"])
def add_wishlist():
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wishlist WHERE product_id=?", (data["id"],))
    if cursor.fetchone():
        conn.close()
        return jsonify({"message": "Already in wishlist"}), 409
    cursor.execute("INSERT INTO wishlist (product_id, name, price, category, image) VALUES (?, ?, ?, ?, ?)",
                   (data["id"], data["name"], data["price"], data["category"], data["image"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Added to wishlist"}), 200

@app.route("/api/wishlist", methods=["GET"])
def get_wishlist():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id, name, price, category, image FROM wishlist")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        "id": r[0], "name": r[1], "price": r[2], "category": r[3], "image": r[4]
    } for r in rows])

@app.route("/api/wishlist/<int:product_id>", methods=["DELETE"])
def delete_wishlist(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wishlist WHERE product_id=?", (product_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Removed from wishlist"}), 200

# === AI FEATURES ===
@app.route("/api/advice", methods=["POST"])
def get_advice():
    occasion = request.form.get("occasion", "")
    language = request.form.get("language", "English")
    color = request.form.get("color", "")
    size = request.form.get("size", "")
    suggestions = {
        "Wedding": "Go for formal black or tan leather shoes.",
        "Office": "Oxford or Loafers in brown or black.",
        "Party": "Trendy sneakers with color splash.",
        "Gym": "Lightweight breathable sports shoes."
    }
    message = suggestions.get(occasion, f"For a {occasion.lower()} event, we recommend size {size} shoes in {color} color.")
    if language == "Hindi":
        translations = {
            "Wedding": "शादी के लिए ब्लैक या टैन रंग के लेदर जूते पहनें।",
            "Office": "ऑफिस के लिए ब्राउन या ब्लैक ऑक्सफोर्ड जूते उपयुक्त हैं।",
            "Party": "पार्टी के लिए ट्रेंडी रंग-बिरंगे स्नीकर्स आज़माएँ।",
            "Gym": "जिम के लिए हल्के और आरामदायक स्पोर्ट्स शूज़ चुनें।"
        }
        message = translations.get(occasion, f"{occasion} के लिए हम {color} रंग के साइज {size} के जूते सुझाव देते हैं।")
    return jsonify({"message": message})

@app.route("/api/personality-quiz", methods=["POST"])
def personality_quiz():
    data = request.get_json()
    answers = data.get("answers", [])
    score = sum(answers)
    if score <= 5:
        result = "Sneaker Lover 🧢 – You’re casual and sporty!"
    elif score <= 8:
        result = "Loafer Vibe 👞 – You like a balance of class and comfort!"
    else:
        result = "Boots Bold 👢 – You’re all about making a statement!"
    return jsonify({"result": result})

@app.route("/api/style-match", methods=["POST"])
def style_match():
    data = request.get_json()
    outfit_type = data.get("outfit_type", "").lower()
    suggestions = {
        "casual": "Try pairing it with clean sneakers or loafers.",
        "formal": "Oxfords or polished leather shoes would elevate your outfit.",
        "sporty": "Sport shoes or trainers with good grip and ventilation are ideal.",
        "ethnic": "Go for embellished juttis or traditional mojaris.",
    }
    message = suggestions.get(outfit_type, "Choose versatile shoes that blend with your outfit!")
    return jsonify({"suggestion": message})

# === RUN ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

