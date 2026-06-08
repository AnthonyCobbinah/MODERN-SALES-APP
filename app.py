from flask import Flask, render_template, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__) # Fixed typo from _name_

# Production Secret Key management
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# SQLite Database path optimized for Render Persistent Disks
# Render provides a persistent directory at /data if you mount a disk.
db_path = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(os.environ.get('DISK_PATH', '.'), 'printing_shop.db'))
if db_path.startswith("postgres://"):
    db_path = db_path.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Admin Credentials (Controlled via Render Env Variables for Security) ---
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Uncleato2312')

# --- Database Models ---
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    normal_print_amount = db.Column(db.Float, nullable=False, default=0.0)
    large_format_amount = db.Column(db.Float, nullable=False, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Changed to utcnow for production standardization

    @property
    def total_entry_sales(self):
        return self.normal_print_amount + self.large_format_amount

# Create database tables automatically
with app.app_context():
    db.create_all()

# --- App Routes ---

# Routes serving Service Worker files safely from root/static definitions
@app.route('/static/manifest.json')
def serve_manifest():
    return app.send_static_file('manifest.json')

@app.route('/static/sw.js')
def serve_sw():
    response = app.send_static_file('sw.js')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/', methods=['GET', 'POST'])
def worker_sales_entry():
    if request.method == 'POST':
        try:
            normal_print = float(request.form.get('normal_print', 0) or 0)
            large_format = float(request.form.get('large_format', 0) or 0)
            
            if normal_print == 0 and large_format == 0:
                flash("Please enter an amount for at least one service.", "warning")
                return redirect('/')

            new_sale = Sale(normal_print_amount=normal_print, large_format_amount=large_format)
            db.session.add(new_sale)
            db.session.commit()
            flash("Sales record saved successfully!", "success")
        except ValueError:
            flash("Invalid input. Please enter numbers only.", "danger")
        
        return redirect('/')

    sales = Sale.query.all()
    total_normal = sum(s.normal_print_amount for s in sales)
    total_large = sum(s.large_format_amount for s in sales)

    return render_template('worker.html', total_normal=total_normal, total_large=total_large)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin/dashboard')
        else:
            flash("Invalid credentials. Access Denied.", "danger")
    return render_template('login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    
    all_sales = Sale.query.order_by(Sale.timestamp.desc()).all()
    grand_normal = sum(s.normal_print_amount for s in all_sales)
    grand_large = sum(s.large_format_amount for s in all_sales)
    grand_total = grand_normal + grand_large

    return render_template('dashboard.html', 
                           sales=all_sales, 
                           grand_normal=grand_normal, 
                           grand_large=grand_large, 
                           grand_total=grand_total)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')