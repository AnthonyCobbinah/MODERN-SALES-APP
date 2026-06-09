from flask import Flask, render_template, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Production Secret Key management
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# SQLite Database path optimized for Render Persistent Disks
db_path = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(os.environ.get('DISK_PATH', '.'), 'printing_shop.db'))
if db_path.startswith("postgres://"):
    db_path = db_path.replace("postgres://", "postgresql://", 1)

app.config['DATABASE_URL_OPTIONS'] = {'sslmode': 'require'} if db_path.startswith("postgresql") else {}
app.config['SQLALCHEMY_DATABASE_URI'] = db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Admin Credentials ---
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Uncleato2312')

# --- Database Models ---
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    normal_print_amount = db.Column(db.Float, nullable=False, default=0.0)
    large_format_amount = db.Column(db.Float, nullable=False, default=0.0)
    # Changed default to allow worker input dates
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total_entry_sales(self):
        return self.normal_print_amount + self.large_format_amount

# Create database tables automatically
with app.app_context():
    db.create_all()

# --- App Routes for PWA Root Access ---
@app.route('/manifest.json')
def serve_manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def serve_sw():
    response = app.send_static_file('sw.js')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.route('/', methods=['GET', 'POST'])
def worker_sales_entry():
    if request.method == 'POST':
        try:
            normal_print = float(request.form.get('normal_print', 0) or 0)
            large_format = float(request.form.get('large_format', 0) or 0)
            custom_date_str = request.form.get('sale_date')
            
            if normal_print == 0 and large_format == 0:
                flash("Please enter an amount for at least one service.", "warning")
                return redirect('/')

            # Parse custom date selected by worker or fallback to current time
            if custom_date_str:
                sale_time = datetime.strptime(custom_date_str, '%Y-%m-%d')
            else:
                sale_time = datetime.utcnow()

            new_sale = Sale(
                normal_print_amount=normal_print, 
                large_format_amount=large_format,
                timestamp=sale_time
            )
            db.session.add(new_sale)
            db.session.commit()
            flash("Sales record saved successfully!", "success")
        except ValueError:
            flash("Invalid input. Check fields and try again.", "danger")
        
        return redirect('/')

    sales = Sale.query.all()
    total_normal = sum(s.normal_print_amount for s in sales)
    total_large = sum(s.large_format_amount for s in sales)
    current_date = datetime.utcnow().strftime('%Y-%m-%d')

    return render_template('worker.html', total_normal=total_normal, total_large=total_large, current_date=current_date)


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

    # --- ADVANCED BUSINESS ANALYTICS ENGINE ---
    normal_pct = 0.0
    large_pct = 0.0
    top_service = "None"
    recommendations = []

    if grand_total > 0:
        normal_pct = (grand_normal / grand_total) * 100
        large_pct = (grand_large / grand_total) * 100
        
        if grand_normal > grand_large:
            top_service = "Normal Document Printing"
        elif grand_large > grand_normal:
            top_service = "Large Format / Banners"
        else:
            top_service = "Perfectly Balanced"

        if top_service == "Normal Document Printing":
            recommendations.append({
                "type": "growth",
                "title": "Leverage High-Volume Document Traffic",
                "text": f"Normal printing generates {normal_pct:.1f}% of your revenue. Consider introducing a customer loyalty program or a high-margin service bundle like binding/lamination at the terminal counter."
            })
        elif top_service == "Large Format / Banners":
            recommendations.append({
                "type": "growth",
                "title": "Scale Large Format Infrastructure",
                "text": f"Large format brings in {large_pct:.1f}% of your cash flow. Secure your ink and media vinyl stock lines early, and run local targeted outreach campaigns to event planners."
            })

        if normal_pct < 30 and grand_total > 100:
            recommendations.append({
                "type": "warning",
                "title": "Low Foot-Traffic Warning",
                "text": "Normal print revenue is below 30%. Consider running small promotional offers or standard student copy discounts to drive immediate volume through the storefront door."
            })
        elif large_pct < 30 and grand_total > 100:
            recommendations.append({
                "type": "warning",
                "title": "Underutilized High-Margin Asset",
                "text": "Large format printer demands are flagging. Set up clear, high-contrast sample signs or banners near your entrance to catch passing consumer attention."
            })
            
        recommendations.append({
            "type": "info",
            "title": "Routine Equipment Optimization",
            "text": "To guarantee smooth operational run-times, clean your wide-format printheads and align cartridges every weekend. Shop particulate dust is the primary cause of sudden downtime."
        })
    else:
        recommendations.append({
            "type": "info",
            "title": "Awaiting Initial Sales Data",
            "text": "Once data inputs start flowing cleanly through the worker terminal, your tailored smart analytics suggestions will formulate automatically here."
        })

    return render_template('dashboard.html', 
                           sales=all_sales, 
                           grand_normal=grand_normal, 
                           grand_large=grand_large, 
                           grand_total=grand_total,
                           normal_pct=normal_pct,
                           large_pct=large_pct,
                           top_service=top_service,
                           recommendations=recommendations)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')