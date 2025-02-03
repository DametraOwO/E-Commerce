from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secret123'

PRODUCTS_FILE = 'data/products.json'
TRANSACTIONS_FILE = 'data/transactions.json'
USERS_FILE = 'data/users.json'

# Fungsi Baca & Tulis JSON
def load_json(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print(f"Data yang dibaca dari {file_path}: {data}")  # Debugging output
        return data
    except FileNotFoundError:
        print(f"File {file_path} tidak ditemukan.")
        return []
    except json.JSONDecodeError as e:
        print(f"Terjadi kesalahan dalam memparsing JSON: {e}")
        return []

def save_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

# Halaman Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Cek kredensial pengguna
        users = load_json(USERS_FILE)
        for user in users:
            if user['email'] == email and check_password_hash(user['password'], password):
                session['user_id'] = user['id']  # Menyimpan ID pengguna dalam session
                return redirect(url_for('index'))  # Arahkan ke halaman utama setelah login

        return render_template('login.html', error="Email atau password salah")

    return render_template('login.html')

# Halaman Utama (Harus login terlebih dahulu)
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Jika belum login, redirect ke halaman login

    products = load_json(PRODUCTS_FILE)
    return render_template('index.html', products=products)

# Manajemen Produk (CRUD)
@app.route('/admin/products')
def admin_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Jika belum login, redirect ke halaman login

    products = load_json(PRODUCTS_FILE)
    return render_template('product.html', products=products)

@app.route('/admin/products/add', methods=['POST'])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Jika belum login, redirect ke halaman login

    products = load_json(PRODUCTS_FILE)
    new_product = {
        "id": len(products) + 1,
        "name": request.form['name'],
        "price": float(request.form['price']),
        "stock": int(request.form['stock'])
    }
    products.append(new_product)
    save_json(PRODUCTS_FILE, products)
    return redirect(url_for('admin_products'))

# Keranjang Belanja
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Jika belum login, redirect ke halaman login

    cart_items = session.get('cart', [])
    return render_template('cart.html', cart=cart_items)

@app.route('/cart/add/<int:product_id>')
def add_to_cart(product_id):
    # Ambil data produk dari file JSON
    products = load_json(PRODUCTS_FILE)
    # Cari produk berdasarkan ID
    product = next((p for p in products if p["id"] == product_id), None)

    if product:
        # Ambil data keranjang yang ada di session
        cart = session.get('cart', [])

        # Cek apakah produk sudah ada di keranjang
        for item in cart:
            if item['id'] == product['id']:
                # Jika produk sudah ada di keranjang, tambah quantity-nya
                item['quantity'] += 1
                break
        else:
            # Jika produk belum ada, tambahkan dengan quantity 1
            product_with_quantity = product.copy()  # Buat salinan produk
            product_with_quantity['quantity'] = 1  # Tambahkan key 'quantity'
            cart.append(product_with_quantity)  # Tambahkan ke keranjang

        # Simpan data keranjang ke session
        session['cart'] = cart

    # Tidak perlu redirect, cukup kirim response sukses
    return jsonify({'success': True})

@app.route('/cart/delete/<int:product_id>', methods=['GET'])
def delete_from_cart(product_id):
    # Ambil data keranjang dari session
    cart = session.get('cart', [])
    
    # Cari produk yang akan dihapus berdasarkan ID
    cart = [item for item in cart if item['id'] != product_id]
    
    # Simpan kembali data keranjang yang sudah diperbarui ke session
    session['cart'] = cart
    
    # Kembalikan response sukses
    return jsonify({'success': True})


# Checkout
@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Jika belum login, redirect ke halaman login

    transactions = load_json(TRANSACTIONS_FILE)
    cart = session.get('cart', [])
    
    # Menghitung total harga berdasarkan quantity setiap item
    total_price = sum(item['price'] * item['quantity'] for item in cart)
    
    new_transaction = {
        "id": len(transactions) + 1,
        "items": cart,
        "total_price": total_price  # Total harga yang benar
    }

    transactions.append(new_transaction)
    save_json(TRANSACTIONS_FILE, transactions)

    session.pop('cart', None)
    return redirect(url_for('index'))

# Dashboard Admin
@app.route('/admin/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Jika belum login, redirect ke halaman login

    transactions = load_json(TRANSACTIONS_FILE)
    
    return render_template('dashboard.html', transactions=transactions)

# Halaman Pendaftaran Akun
@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        # Ambil data JSON dari request
        data = request.get_json()

        email = data['email']
        password = data['password']

        # Validasi email
        if not is_valid_email(email):
            return jsonify({"success": False, "error": "Email tidak valid"}), 400

        # Cek apakah email sudah terdaftar
        users = load_json(USERS_FILE)
        if any(user['email'] == email for user in users):
            return jsonify({"success": False, "error": "Email sudah terdaftar"}), 400

        # Hash password dan simpan data pengguna baru
        hashed_password = generate_password_hash(password)
        new_user = {
            "id": len(users) + 1,
            "email": email,
            "password": hashed_password
        }

        users.append(new_user)
        save_json(USERS_FILE, users)

        return jsonify({"success": True}), 200  # Kembalikan response sukses

# Validasi Email
def is_valid_email(email):
    import re
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email)

if __name__ == '__main__':
    app.run(debug=True)