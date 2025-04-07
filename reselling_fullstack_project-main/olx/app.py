import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'olx'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

mysql = MySQL(app)

# ALLOWED_EXTENSIONS for image upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to fetch vehicle by ID from the database
def get_vehicle_by_id(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (id,))
    vehicle = cur.fetchone()  # Fetch the first result (since ID is unique)
    cur.close()
    return vehicle

# Create tables if they don't exist
def create_tables():
    cur = mysql.connection.cursor()

    # Create the login table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS login (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    ''')

    # Create the products table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products(
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            name VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            image_path VARCHAR(255) NOT NULL,
            brand VARCHAR(255) NOT NULL,
            model VARCHAR(255) NOT NULL,
            year INT NOT NULL,
            mileage INT NOT NULL,
            condition1 VARCHAR(255) NOT NULL,
            img VARCHAR(255) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES login(id) ON DELETE CASCADE
        )
    ''')

    # Create the orders table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            product_id INT NOT NULL,
            offer INT NOT NULL,
            address TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES login(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')

    # Commit changes to the database
    mysql.connection.commit()
    cur.close()

# Home Route (Displays all products)
@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    cur.close()
    return render_template('home.html', products=products)

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM login WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM login WHERE email=%s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('User already exists. Please login.', 'danger')
            cur.close()
            return redirect(url_for('register'))

        cur.execute("INSERT INTO login (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')
@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session:
        flash('You must be logged in to add a product.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        brand = request.form['brand']
        model = request.form['model']
        price = request.form['price']
        year = request.form['year']
        mileage = request.form['mileage']
        condition = request.form['condition']

        # Check and save the primary image
        file = request.files.get('image')
        fl = request.files.get('img')  # For additional image

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f'/static/uploads/{filename}'  # Store relative path
        else:
            flash('Invalid or missing main image.', 'danger')
            return redirect(request.url)

        # Check and save the additional image
        if fl and allowed_file(fl.filename):
            filenam = secure_filename(fl.filename)
            fl.save(os.path.join(app.config['UPLOAD_FOLDER'], filenam))
            img_path = f'/static/uploads/{filenam}'  # Store relative path
        else:
            flash('Invalid or missing additional image.', 'danger')
            return redirect(request.url)

        # Insert product details into the database
        cur = mysql.connection.cursor()
        cur.execute('''
            INSERT INTO products (user_id, name, description, brand, model, price, year, mileage, condition1, image_path, img)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            session['user_id'], name, description, brand, model, price, year, mileage, condition, image_path, img_path
        ))

        mysql.connection.commit()
        cur.close()

        flash('Product added successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('add_product.html')



# Vehicle Detail Route (Fetch vehicle data by ID)
@app.route('/vehicle_detail/<int:id>', methods=['GET'])
def vehicle_detail(id):
    # Fetch the vehicle details from the database
    vehicle = get_vehicle_by_id(id)
    if vehicle is None:
        flash('Vehicle not found!', 'danger')
        return redirect(url_for('home'))  # Redirect to home if vehicle not found

    # Pass the vehicle data to the template
    return render_template('vehicle_detail.html', vehicle=vehicle)

# My Products Route (Authenticated)
@app.route('/my_products')
def my_products():
    if 'user_id' not in session:
        flash('You must be logged in to view your products.', 'danger')
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE user_id=%s", (session['user_id'],))
    products = cur.fetchall()
    cur.close()
    return render_template('my_products.html', products=products)

@app.route('/products/update/<int:id>', methods=['GET', 'POST'])
def update_product(id):
    if 'user_id' not in session:
        flash('You must be logged in to update a product.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s AND user_id=%s", (id, session['user_id']))
    product = cur.fetchone()

    if not product:
        flash('Product not found or you do not have permission to update it.', 'danger')
        cur.close()
        return redirect(url_for('my_products'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        brand = request.form['brand']
        model = request.form['model']
        price = request.form['price']
        year = request.form['year']
        mileage = request.form['mileage']
        condition = request.form['condition']

        # Check for the image (primary or secondary)
        if 'image' in request.files or 'img' in request.files:
            file = None
            # Check for file in 'image' first, if not found, check for 'img'
            if 'image' in request.files and request.files['image'].filename != '':
                file = request.files['image']
            elif 'img' in request.files and request.files['img'].filename != '':
                file = request.files['img']

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image_path)

                # Update image path in the database (store in 'image_path' column)
                cur.execute('''
                    UPDATE products 
                    SET name=%s, description=%s, brand=%s, model=%s, price=%s, year=%s, mileage=%s, condition1=%s, image_path=%s
                    WHERE id=%s AND user_id=%s
                ''', (
                    name, description, brand, model, price, year, mileage, condition, f'/static/uploads/{filename}', id, session['user_id']
                ))
            else:
                flash('Invalid image format.', 'danger')
                cur.close()
                return redirect(request.url)
        else:
            # If no image file is uploaded, just update other details
            cur.execute('''
                UPDATE products 
                SET name=%s, description=%s, brand=%s, model=%s, price=%s, year=%s, mileage=%s, condition1=%s 
                WHERE id=%s AND user_id=%s
            ''', (
                name, description, brand, model, price, year, mileage, condition, id, session['user_id']
            ))

        mysql.connection.commit()
        cur.close()

        flash('Product updated successfully!', 'success')
        return redirect(url_for('my_products'))

    return render_template('update_product.html', product=product)

@app.route('/products/delete/<int:id>', methods=['POST'])
def delete_product(id):
    if 'user_id' not in session:
        flash('You must be logged in to delete a product.', 'danger')
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM products WHERE id=%s AND user_id=%s", (id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('my_products'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# View Cart
@app.route('/cart')
def view_cart():
    if 'cart' not in session:
        session['cart'] = []
    cart_items = session['cart']

    cur = mysql.connection.cursor()
    product_ids = [item['product_id'] for item in cart_items]
    if product_ids:
        format_strings = ','.join(['%s'] * len(product_ids))
        cur.execute(f"SELECT id, name, description, price, image_path FROM products WHERE id IN ({format_strings})", product_ids)
        products = cur.fetchall()
    else:
        products = []

    cart_details = []
    for product in products:
        for item in cart_items:
            if product[0] == item['product_id']:
                cart_details.append({
                    'id': product[0],
                    'name': product[1],
                    'description': product[2],
                    'price': product[3],
                    'image_path': product[4],
                    'quantity': item['quantity']
                })

    total_price = sum(item['price'] * item['quantity'] for item in cart_details)
    return render_template('cart.html', items=cart_details, total_price=total_price)

# Add to Cart
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']

    for item in cart:
        if item['product_id'] == product_id:
            item['quantity'] += 1
            session.modified = True
            flash('Product quantity updated in cart!', 'success')
            return redirect(url_for('home'))

    cart.append({'product_id': product_id, 'quantity': 1})
    session.modified = True
    flash('Product added to cart!', 'success')
    return redirect(url_for('home'))

# Remove from Cart
@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'cart' not in session:
        flash('Cart is empty!', 'danger')
        return redirect(url_for('view_cart'))

    session['cart'] = [item for item in session['cart'] if item['product_id'] != product_id]
    session.modified = True
    flash('Product removed from cart!', 'success')
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('You must be logged in to proceed with checkout.', 'danger')
        return redirect(url_for('login'))

    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty. Add some items before checking out.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        address = request.form['address']
        offer = request.form['offer_price']
        user_id = session['user_id']
        cart_items = session['cart']

        cur = mysql.connection.cursor()

        # Store each cart item as a new order entry in the database
        for item in cart_items:
            product_id = item['product_id']
            cur.execute('''
                INSERT INTO orders (user_id, product_id, address,offer)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, product_id, address, offer))

        mysql.connection.commit()
        cur.close()
        session['cart']=[]
        session.modified = True

        flash('Your order has been placed successfully!', 'success')
        return redirect(url_for('home'))

    return redirect(url_for('view_cart'))


@app.route('/seller_page')
def seller_page():
    if 'user_id' not in session:
        flash('You must be logged in to view your seller page.', 'danger')
        return redirect(url_for('login'))

    seller_id = session['user_id']
    cur = mysql.connection.cursor()

    # Debugging: Print seller_id
    print(f'Seller ID from session: {seller_id}')

    # Fetch buyer details for the seller's products
    cur.execute('''
        SELECT 
            o.id AS order_id,
            p.name AS product_name,
            p.price AS product_price,
            o.offer AS offer,
            l.name AS buyer_name,
            l.email AS buyer_email,
            o.address AS buyer_address
        FROM 
            orders o
        JOIN 
            products p ON o.product_id = p.id
        JOIN 
            login l ON o.user_id = l.id
        WHERE 
            p.user_id = %s
    ''', (seller_id,))

    sales = cur.fetchall()

    # Debugging: Print sales data
    print(f'Sales data: {sales}')

    cur.close()

    return render_template('seller_page.html', sales=sales)

@app.route('/accept_offer/<int:order_id>', methods=['POST'])
def accept_offer(order_id):
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'danger')
        return redirect(url_for('login'))
    seller_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT product_id FROM orders WHERE id = %s", (order_id,))
    result = cur.fetchone()
    if result:
        product_id = result[0]

        # Delete orders associated with the product
        cur.execute("DELETE FROM orders WHERE product_id = %s", (product_id,))

        # Delete the product
        cur.execute("DELETE FROM products WHERE id = %s AND user_id = %s", (product_id, seller_id))

        mysql.connection.commit()
        flash('Order accepted, and associated product and address have been deleted.', 'success')
    else:
        flash('Order not found or you do not have permission to accept it.', 'danger')

    cur.close()
    return redirect(url_for('seller_page'))


@app.route('/reject_offer/<int:order_id>', methods=['POST'])
def reject_offer(order_id):
    if 'user_id' not in session:
        flash('You must be logged in to perform this action.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    # Delete the offer from the orders table
    cur.execute('DELETE FROM orders WHERE id = %s', (order_id,))
    mysql.connection.commit()
    cur.close()

    flash('Offer rejected!', 'success')
    return redirect(url_for('seller_page'))
@app.route('/search', methods=['GET'])
def search_vehicles():
    query = request.args.get('query')
    cur = mysql.connection.cursor()

    if query:
        # Filter products by name or brand using raw SQL
        sql_query = """
            SELECT * FROM products 
            WHERE name LIKE %s OR brand LIKE %s
        """
        params = (f'%{query}%', f'%{query}%')

        # Execute the query using the cursor
        cur.execute(sql_query, params)
        products = cur.fetchall()
    else:
        # If no query, show all products
        sql_query = "SELECT * FROM products"
        cur.execute(sql_query)
        products = cur.fetchall()

    cur.close()
    return render_template('home.html', products=products)



if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        create_tables()
    app.run(debug=True)