from flask import Flask, render_template, request, redirect, session, send_file, flash
from db_config import conn, cursor
from dotenv import load_dotenv
import os
import io
import pandas as pd
import xlsxwriter
import mysql.connector

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


@app.route('/')
def home():
    return redirect('/login')



# Download Product List


@app.route('/download_products')
def download_products():
    search_value = request.args.get('search_value', '').strip().lower()

    cursor = conn.cursor()

    if search_value:
        query = """
            SELECT name, quantity, price, total_cost, date
            FROM products
            WHERE LOWER(name) = %s OR quantity = %s OR price = %s
        """
        cursor.execute(query, (search_value, search_value, search_value))
    else:
        query = "SELECT name, quantity, price, total_cost, date FROM products"
        cursor.execute(query)

    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        return "No data to export."

    # Convert rows to DataFrame
    df = pd.DataFrame(rows, columns=['Name', 'Quantity', 'Price Per Product', 'Total Cost', 'Purchase Date'])

    # Save to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Products')

    output.seek(0)
    return send_file(
        output,
        download_name='filtered_products.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )





#  For Admin Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]  # Add this line to save role in session
            return redirect('/dashboard')
        else:
            return "Invalid username or password"
    
    return render_template('login.html')







from flask import Flask, render_template, request, session
from db_config import conn  # using your existing DB connection
# dashboard route
@app.route('/dashboard', methods=['GET'])
def dashboard():
    search_value = request.args.get('search_value', '').strip()
    cursor = conn.cursor()

    if search_value:
        query = """
            SELECT * FROM products 
            WHERE name = %s 
               OR CAST(price AS CHAR) = %s 
               OR CAST(quantity AS CHAR) = %s
        """
        cursor.execute(query, (search_value, search_value, search_value))
    else:
        cursor.execute("SELECT * FROM products")

    products = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    cursor.close()
    return render_template('dashboard.html', products=products, total_products=total_products)



    #add products 

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        date = request.form['date']

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (name, quantity, price, date)
            VALUES (%s, %s, %s, %s)
        """, (name, quantity, price, date))
        conn.commit()
        cursor.close()

        return redirect('/dashboard')
    return render_template('add_product.html')



# Edit Product Logic

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        date = request.form['date']

        cursor.execute("""
            UPDATE products
            SET name=%s, quantity=%s, price=%s, date=%s
            WHERE id=%s
        """, (name, quantity, price, date, product_id))
        conn.commit()
        cursor.close()
        return redirect('/dashboard')

    # GET request: load product details
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()

    # Format date for HTML input
    if product and product[5]:
        formatted_product = list(product)
        formatted_product[5] = product[5].strftime('%Y-%m-%d')
    else:
        formatted_product = product

    return render_template('edit_product.html', product=formatted_product)



# Delete Product
@app.route('/delete_product/<int:id>')
def delete_product(id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    return redirect('/dashboard')




# Create User



@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, 'user'))
            conn.commit()
            flash('User created successfully!', 'success')  # ✅ Flash success message
        except mysql.connector.IntegrityError:
            flash('User already exists!', 'danger')  # ✅ Flash error message
        return redirect('/create_user')  # Redirect AFTER flashing
    return render_template('create_user.html')




# Route to view all users (only for admin)


# Manage Users (Admin only)
@app.route('/manage_users')
def manage_users():
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/dashboard')

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    return render_template('manage_user.html', users=users)


# Delete User (Admin only)
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/dashboard')

    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    return redirect('/manage_users')



# for product total count


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)






