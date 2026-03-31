from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import numpy as np
from tensorflow.keras.models import load_model
import joblib
import schedule
import time
from threading import Thread
from twilio.rest import Client
import os

app = Flask(__name__)
app.secret_key = "secret"

# Load model + scaler
model = load_model("model/model.h5", compile=False)
scaler = joblib.load("model/scaler.pkl")


# ---------------- DB ----------------
def get_db():
    return sqlite3.connect("database.db")


# 🔥 SMS FUNCTION
def send_sms_alert(message):

    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

    client = Client(account_sid, auth_token)

    client.messages.create(
        body=message,
        from_="+15706336055",   # Twilio number
        to="+916380252837"     # Owner number
    )


# 🔥 DAILY CHECK FUNCTION
def check_and_send_alert():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    expiring = []

    for p in products:
        expiry = datetime.strptime(p[4], "%Y-%m-%d")
        days_left = (expiry - datetime.now()).days

        if 0 <= days_left <= 10:
            expiring.append(p[1])

    if expiring:
        message = f"⚠️ {len(expiring)} products expiring soon:\n" + ", ".join(expiring)
        send_sms_alert(message)

    conn.close()


# 🔥 SCHEDULER
def run_scheduler():
    schedule.every().day.at("10:00").do(check_and_send_alert)

    while True:
        schedule.run_pending()
        time.sleep(60)


# 🔥🔥 AI DISCOUNT
def calculate_ai_discount(days_left, stock, price, product):

    if days_left > 10:
        return 0, 0.0

    avg_sales = stock / 10

    discount = product[6]
    season_demand = product[7]
    supplier_delay = product[8]
    storage_temp = product[9]
    product_age = product[10]
    category = product[11]

    X = np.array([[days_left, stock, price, avg_sales,
                   discount, season_demand, supplier_delay,
                   storage_temp, product_age, category]])

    X = scaler.transform(X)
    risk = float(model.predict(X)[0][0])

    risk_factor = risk
    time_factor = max(0, (10 - days_left) / 10)
    stock_factor = min(stock / 100, 1)
    demand_factor = 1 - season_demand

    score = (
        0.4 * risk_factor +
        0.3 * time_factor +
        0.2 * stock_factor +
        0.1 * demand_factor
    )

    discount = 5 + (score * 45)

    return round(min(discount, 50), 2), round(risk, 2)


# ✅ AUTO DELETE
def remove_expired_products():
    conn = get_db()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        "DELETE FROM products WHERE DATE(expiry_date) < DATE(?)",
        (today,)
    )

    conn.commit()
    conn.close()


# ---------------- AUTH ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
        result = cursor.fetchone()
        conn.close()

        if result:
            session["user"] = user
            return redirect("/dashboard")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?,?)",
            (request.form["username"], request.form["password"])
        )
        conn.commit()
        conn.close()
        return redirect("/")

    return render_template("signup.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ---------------- INVENTORY ----------------
@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    remove_expired_products()

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        cursor.execute("""
        INSERT INTO products 
        (name, quantity, price, expiry_date, added_date, discount, season_demand, supplier_delay, storage_temp, product_age, category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["name"],
            int(request.form["quantity"]),
            float(request.form["price"]),
            request.form["expiry"],
            datetime.now(),
            10, 0.5, 2, 5, 10, 1
        ))

        conn.commit()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    updated_products = []

    for p in products:
        expiry = datetime.strptime(p[4], "%Y-%m-%d")
        days_left = (expiry - datetime.now()).days

        discount, risk = calculate_ai_discount(days_left, p[2], p[3], p)

        if days_left < 0:
            status = "Expired ❌"
            color = "gray"
        elif days_left <= 2:
            status = "Urgent 🔴"
            color = "red"
        elif days_left <= 5:
            status = "Warning 🟠"
            color = "orange"
        else:
            status = "Safe 🟢"
            color = "lightgreen"

        updated_products.append({
            "id": p[0],
            "name": p[1],
            "qty": p[2],
            "price": p[3],
            "expiry": p[4],
            "days_left": days_left,
            "risk": risk,
            "status": status,
            "color": color
        })

    return render_template("inventory.html", products=updated_products)


@app.route("/delete/<int:id>")
def delete_product(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/inventory")


# ---------------- EXPIRING ----------------
@app.route("/expiring")
def expiring():
    remove_expired_products()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    expiring_products = []

    for p in products:
        expiry = datetime.strptime(p[4], "%Y-%m-%d")
        days_left = (expiry - datetime.now()).days

        if 0 <= days_left <= 10:
            expiring_products.append({
                "id": p[0],
                "name": p[1],
                "qty": p[2],
                "days_left": days_left
            })

    return render_template("expiring.html", products=expiring_products)


# ---------------- BILLING ----------------
@app.route("/billing", methods=["GET", "POST"])
def billing():
    remove_expired_products()

    conn = get_db()
    cursor = conn.cursor()

    if "cart" not in session:
        session["cart"] = []

    if request.method == "POST":
        product_id = int(request.form["product_id"])
        qty = int(request.form["qty"])

        cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
        p = cursor.fetchone()

        if not p:
            return redirect("/billing")

        days_left = (datetime.strptime(p[4], "%Y-%m-%d") - datetime.now()).days
        discount, risk = calculate_ai_discount(days_left, p[2], p[3], p)

        final_price = round(p[3] - (p[3] * discount / 100), 2)

        session["cart"].append({
            "id": p[0],
            "name": p[1],
            "qty": qty,
            "price": p[3],
            "discount": discount,
            "total": round(final_price * qty, 2)
        })

        session.modified = True

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    return render_template("billing.html",
                           products=products,
                           cart=session["cart"],
                           now=datetime.now(),
                           bill_no=len(session["cart"]) + 1)


# ---------------- FINALIZE ----------------
@app.route("/finalize")
def finalize():
    conn = get_db()
    cursor = conn.cursor()

    for item in session.get("cart", []):
        cursor.execute(
            "UPDATE products SET quantity = quantity - ? WHERE id=?",
            (item["qty"], item["id"])
        )

    conn.commit()
    conn.close()
    return redirect("/billing")


@app.route("/complete")
def complete():
    session["cart"] = []
    session.modified = True
    return redirect("/billing")


@app.route("/remove/<int:id>")
def remove(id):
    session["cart"] = [i for i in session.get("cart", []) if i["id"] != id]
    session.modified = True
    return redirect("/billing")


@app.route("/clear")
def clear():
    session["cart"] = []
    session.modified = True
    return redirect("/billing")

@app.route("/risk/<int:id>")
def risk(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products WHERE id=?", (id,))
    p = cursor.fetchone()
    conn.close()

    if not p:
        return "❌ Product not found (Invalid ID)"

    expiry = datetime.strptime(p[4], "%Y-%m-%d")
    days_left = (expiry - datetime.now()).days

    stock = p[2]
    price = p[3]

    discount, risk = calculate_ai_discount(days_left, stock, price, p)

    selling_probability = round((1 - risk) * 100, 2)

    return f"""
    <h2>📊 Risk Analysis</h2>
    <p><b>Product:</b> {p[1]}</p>
    <p><b>Risk Score:</b> {risk:.2f}</p>
    <p><b>Probability of Selling:</b> {selling_probability}%</p>
    <p><b>Suggested Discount:</b> {discount}%</p>
    <p><b>Days Left:</b> {days_left}</p>
    """

@app.route("/test-sms")
def test_sms():
    send_sms_alert("✅ Test SMS from your Smart Retail System")
    return "SMS Sent!"

# ---------------- START ----------------
if __name__ == "__main__":
    scheduler_thread = Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    app.run(debug=True)