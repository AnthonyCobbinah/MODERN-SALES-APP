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
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def total_entry_sales(self):
        return self.normal_print_amount + self.large_format_amount

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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
        form_type = request.form.get('form_type')
        custom_date_str = request.form.get('entry_date')
        
        # Parse logging date or fallback to current time
        if custom_date_str:
            entry_time = datetime.strptime(custom_date_str, '%Y-%m-%d')
        else:
            entry_time = datetime.utcnow()

        try:
            if form_type == 'sale':
                normal_print = float(request.form.get('normal_print', 0) or 0)
                large_format = float(request.form.get('large_format', 0) or 0)
                
                if normal_print == 0 and large_format == 0:
                    flash("Please enter an amount for at least one service.", "warning")
                    return redirect('/')

                new_sale = Sale(
                    normal_print_amount=normal_print, 
                    large_format_amount=large_format,
                    timestamp=entry_time
                )
                db.session.add(new_sale)
                db.session.commit()
                flash("Sales record saved successfully!", "success")

            elif form_type == 'expense':
                description = request.form.get('description', '').strip()
                expense_amount = float(request.form.get('expense_amount', 0) or 0)
                
                if not description or expense_amount <= 0:
                    flash("Please provide a valid description and amount for the expense.", "warning")
                    return redirect('/')

                new_expense = Expense(
                    description=description,
                    amount=expense_amount,
                    timestamp=entry_time
                )
                db.session.add(new_expense)
                db.session.commit()
                flash("Expense logged and queued for audit review.", "success")
                
        except ValueError:
            flash("Invalid input numeric formatting. Check fields and try again.", "danger")
        
        return redirect('/')

    sales = Sale.query.all()
    expenses = Expense.query.all()
    
    total_normal = sum(s.normal_print_amount for s in sales)
    total_large = sum(s.large_format_amount for s in sales)
    total_expenses = sum(e.amount for e in expenses)
    current_date = datetime.utcnow().strftime('%Y-%m-%d')

    return render_template('worker.html', 
                           total_normal=total_normal, 
                           total_large=total_large, 
                           total_expenses=total_expenses, 
                           current_date=current_date)


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
    all_expenses = Expense.query.order_by(Expense.timestamp.desc()).all()
    
    grand_normal = sum(s.normal_print_amount for s in all_sales)
    grand_large = sum(s.large_format_amount for s in all_sales)
    grand_total = grand_normal + grand_large
    
    grand_expenses = sum(e.amount for e in all_expenses)
    net_profit = grand_total - grand_expenses

    # --- ADVANCED BUSINESS ANALYTICS & INTELLIGENCE ENGINE ---
    normal_pct = 0.0
    large_pct = 0.0
    top_service = "None"
    recommendations = []

    # 1. Profitability Matrix Assessment
    if grand_total > 0:
        profit_margin_pct = (net_profit / grand_total) * 100
        normal_pct = (grand_normal / grand_total) * 100
        large_pct = (grand_large / grand_total) * 100
        
        if grand_normal > grand_large:
            top_service = "Normal Document Printing"
        elif grand_large > grand_normal:
            top_service = "Large Format / Banners"
        else:
            top_service = "Perfectly Balanced"
    else:
        profit_margin_pct = 0.0

    # 2. Algorithmic Financial Health Status Definitions
    if grand_total == 0 and grand_expenses == 0:
        health_status = "Awaiting Telemetry"
        health_color = "slate"
        health_desc = "No operational ledger data has been detected yet inside the terminal cache."
    elif net_profit > 0:
        if profit_margin_pct >= 40:
            health_status = "Optimal Profit Yield"
            health_color = "emerald"
            health_desc = f"Excellent capital efficiency. Operating with a robust {profit_margin_pct:.1f}% net margin. Scalable buffer exists."
        else:
            health_status = "Marginal Profitability"
            health_color = "amber"
            health_desc = f"Firm is operating in net-positive territory, but margins are tight ({profit_margin_pct:.1f}%). Evaluate and trim secondary overhead inputs."
    else:
        health_status = "Net Operating Loss"
        health_color = "rose"
        health_desc = f"Critical Exposure detected! Expenses exceed raw incoming revenue by GHS {abs(net_profit):.2f}. Implement immediate cash optimization protocols."

    # 3. Formulating Dynamic Insights
    if grand_total > 0:
        if top_service == "Normal Document Printing":
            recommendations.append({
                "type": "growth",
                "title": "Leverage High-Volume Document Traffic",
                "text": f"Normal printing generates {normal_pct:.1f}% of your revenue. Consider introducing a customer loyalty program or high-margin service bundles like binding/lamination at the counter."
            })
        elif top_service == "Large Format / Banners":
            recommendations.append({
                "type": "growth",
                "title": "Scale Large Format Infrastructure",
                "text": f"Large format brings in {large_pct:.1f}% of your cash flow. Secure ink and media vinyl stock lines early, and run targeted outreach campaigns to local event planners."
            })

        if profit_margin_pct < 20 and profit_margin_pct > 0:
            recommendations.append({
                "type": "warning",
                "title": "Expense Overhead Compaction Warning",
                "text": f"Overhead is absorbing {100 - profit_margin_pct:.1f}% of gross incoming margins. Audit individual material run-times and limit worker-logged petty cash allocations."
            })
        elif profit_margin_pct <= 0:
            recommendations.append({
                "type": "warning",
                "title": "Strategic Retrenchment Required",
                "text": "The operational facility is processing under cost parity. Temporarily halt unessential asset deployments, audit major structural spending lines, or re-evaluate baseline print pricing matrices."
            })

        recommendations.append({
            "type": "info",
            "title": "Routine Equipment Optimization",
            "text": "To guarantee smooth operational run-times, clean wide-format printheads and align cartridges every weekend. Dust is the primary cause of sudden downtime."
        })
    else:
        recommendations.append({
            "type": "info",
            "title": "Awaiting Initial Sales Data",
            "text": "Once data inputs start flowing cleanly through the worker terminal, your tailored smart analytics suggestions will formulate automatically here."
        })

    return render_template('dashboard.html', 
                           sales=all_sales,
                           expenses=all_expenses,
                           grand_normal=grand_normal, 
                           grand_large=grand_large, 
                           grand_total=grand_total,
                           grand_expenses=grand_expenses,
                           net_profit=net_profit,
                           normal_pct=normal_pct,
                           large_pct=large_pct,
                           top_service=top_service,
                           health_status=health_status,
                           health_color=health_color,
                           health_desc=health_desc,
                           recommendations=recommendations)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')