"""
Naveen Nimmala — Portfolio Website
Flask Application Backend (SQL Server database + Admin Dashboard + WhatsApp alerts)

Run locally:
    pip install -r requirements.txt
    python app.py
Then visit http://127.0.0.1:5000
Admin dashboard: http://127.0.0.1:5000/admin/login
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import urllib.parse
import urllib.request

import database as db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'naveen-portfolio-secret-2024')

# ─── Configuration (override via environment variables in production) ──
OWNER_EMAIL = os.environ.get('OWNER_EMAIL', 'naveennimmala227@gmail.com')
SMTP_HOST   = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT   = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER   = os.environ.get('SMTP_USER', '')   # leave blank to disable email
SMTP_PASS   = os.environ.get('SMTP_PASS', '')   # use a Gmail App Password, not your real password

# WhatsApp lead alerts via CallMeBot (https://www.callmebot.com/blog/free-api-whatsapp-messages/)
# 1. WhatsApp "I allow callmebot to send me messages" to +34 644 59 71 67
# 2. You'll receive an apikey in reply — set it below or as an env var
WHATSAPP_PHONE  = os.environ.get('WHATSAPP_PHONE', '919177393699')   # your number, country code, no +/spaces
WHATSAPP_APIKEY = os.environ.get('WHATSAPP_APIKEY', '')             # leave blank to disable WhatsApp alerts

# Admin dashboard login — CHANGE THIS before deploying publicly
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'naveen')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme123')

# Initialize database (creates portfolio.db + table if not present)
db.init_db()


# ─── Auth Decorator ────────────────────────────────────────────────────

def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return view_func(*args, **kwargs)
    return wrapped


# ─── Public Page Routes ─────────────────────────────────────────────────

@app.route('/')
def index():
    """Home page — hero, services overview, why-choose-me, portfolio preview, testimonials, FAQ."""
    return render_template('index.html', page='home')


@app.route('/about')
def about():
    """About page — profile, skills, experience timeline, mission & vision."""
    return render_template('about.html', page='about')


@app.route('/services')
def services():
    """Services page — detailed service breakdown with pricing hints and process."""
    return render_template('services.html', page='services')


@app.route('/portfolio')
def portfolio():
    """Portfolio page — project showcase with filterable grid and detail modals."""
    return render_template('portfolio.html', page='portfolio')


@app.route('/pricing')
def pricing():
    """Pricing page — package cards, comparison table, maintenance add-on."""
    return render_template('pricing.html', page='pricing')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page (GET) + lead-generation form handler (POST), now saved to SQLite."""
    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        email        = request.form.get('email', '').strip()
        phone        = request.form.get('phone', '').strip()
        business     = request.form.get('business', '').strip()
        service_type = request.form.get('service_type', '').strip()
        budget       = request.form.get('budget', '').strip()
        message      = request.form.get('message', '').strip()

        if not name or not email or not message:
            return jsonify({'status': 'error', 'msg': 'Name, email and project details are required.'}), 400

        inquiry = {
            'name': name, 'email': email, 'phone': phone,
            'business': business, 'service_type': service_type,
            'budget': budget, 'message': message,
        }

        try:
            db.add_inquiry(inquiry)
            _send_notification(inquiry)
            _send_whatsapp_alert(inquiry)
        except Exception as e:
            print(f"[CONTACT FORM WARNING] {e}")

        return jsonify({'status': 'success', 'msg': f"Thanks {name}! I'll get back to you within 24 hours."})

    return render_template('contact.html', page='contact')


# ─── Admin Routes ────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Simple username/password login for the admin dashboard."""
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid username or password.'
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Lead management dashboard — view, filter, search, and update inquiry status."""
    status_filter = request.args.get('status', 'All')
    search        = request.args.get('q', '').strip()

    leads = db.get_all_inquiries(status_filter=status_filter, search=search or None)
    stats = db.get_stats()

    return render_template(
        'admin_dashboard.html',
        leads=leads, stats=stats,
        current_status=status_filter, search=search,
    )


@app.route('/admin/api/leads')
@admin_required
def admin_api_leads():
    """JSON endpoint the dashboard polls periodically for near-real-time updates."""
    status_filter = request.args.get('status', 'All')
    search        = request.args.get('q', '').strip()

    leads = db.get_all_inquiries(status_filter=status_filter, search=search or None)
    stats = db.get_stats()
    return jsonify({'leads': leads, 'stats': stats})


@app.route('/admin/api/leads/<int:lead_id>/status', methods=['POST'])
@admin_required
def admin_update_status(lead_id):
    """AJAX endpoint to update a lead's status from the dashboard."""
    new_status = request.json.get('status') if request.is_json else request.form.get('status')
    try:
        ok = db.update_status(lead_id, new_status)
        return jsonify({'success': ok})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/admin/api/leads/<int:lead_id>/notes', methods=['POST'])
@admin_required
def admin_update_notes(lead_id):
    """AJAX endpoint to save internal notes on a lead."""
    notes = request.json.get('notes', '') if request.is_json else request.form.get('notes', '')
    ok = db.update_notes(lead_id, notes)
    return jsonify({'success': ok})


@app.route('/admin/api/leads/<int:lead_id>/delete', methods=['POST'])
@admin_required
def admin_delete_lead(lead_id):
    """AJAX endpoint to permanently delete a lead."""
    ok = db.delete_inquiry(lead_id)
    return jsonify({'success': ok})


# ─── Helpers ─────────────────────────────────────────────────────────────

def _send_whatsapp_alert(data: dict) -> None:
    """
    Send a WhatsApp message to the site owner via CallMeBot when a new lead
    comes in. Silently skipped if WHATSAPP_APIKEY isn't configured.
    """
    if not WHATSAPP_APIKEY:
        return

    text = (
        f"🔔 New Website Lead!\n\n"
        f"Name: {data['name']}\n"
        f"Phone: {data.get('phone') or '-'}\n"
        f"Business: {data.get('business') or '-'}\n"
        f"Service: {data.get('service_type') or '-'}\n"
        f"Budget: {data.get('budget') or '-'}\n\n"
        f"Message: {data['message'][:300]}"
    )

    params = urllib.parse.urlencode({
        'phone':  WHATSAPP_PHONE,
        'text':   text,
        'apikey': WHATSAPP_APIKEY,
    })
    url = f"https://api.callmebot.com/whatsapp.php?{params}"

    try:
        urllib.request.urlopen(url, timeout=10)
    except Exception as e:
        print(f"[WHATSAPP ALERT WARNING] {e}")


def _send_notification(data: dict) -> None:
    """Email the site owner about a new lead. Silently skipped if SMTP isn't configured."""
    if not SMTP_USER or not SMTP_PASS:
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"New Lead: {data['name']} – {data.get('service_type') or 'General Inquiry'}"
    msg['From']    = SMTP_USER
    msg['To']      = OWNER_EMAIL

    body = f"""New client inquiry received.

Name:      {data['name']}
Email:     {data['email']}
Phone:     {data['phone']}
Business:  {data['business']}
Service:   {data['service_type']}
Budget:    {data['budget']}

Message:
{data['message']}

View it in your dashboard: /admin/dashboard
"""
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, OWNER_EMAIL, msg.as_string())


# ─── Error Handlers ────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', page='home'), 404


# ─── Entrypoint ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
