# Naveen Nimmala — Portfolio Website

A premium, multi-page Flask portfolio website built to generate leads for a
website-design and web-application development business.

**Stack:** Python · Flask · Jinja2 · HTML5 · CSS3 (no framework) · Vanilla JS · **SQL Server**

---

## 1. Project Structure

```
project/
│
├── app.py                  # Flask application & routes
├── database.py              # SQL Server data layer (leads/inquiries)
├── requirements.txt        # Python dependencies
│
├── templates/
│   ├── base.html             # Shared layout (nav, footer, WhatsApp float)
│   ├── index.html            # Home — hero, services, why-me, portfolio, testimonials, FAQ
│   ├── about.html            # About — profile, skills, timeline, mission/vision
│   ├── services.html         # Services — detailed breakdown + process
│   ├── portfolio.html        # Portfolio — filterable grid + project modals
│   ├── pricing.html          # Pricing — package cards + comparison table
│   ├── contact.html          # Contact — lead form + AJAX submit
│   ├── admin_login.html      # Admin — login page
│   ├── admin_dashboard.html  # Admin — lead management dashboard
│   └── partials/
│       └── _leads_rows.html  # Reusable table-rows partial
│
└── static/
    ├── css/style.css         # Main stylesheet (design system, responsive, animations)
    ├── css/admin.css         # Admin dashboard styles
    ├── js/script.js          # Public site: nav, cursor, scroll-reveal, counters, FAQ, modals
    ├── js/admin.js           # Admin dashboard: live polling, filters, status updates
    └── images/                # Add your real project screenshots here
```

---

## 2. Database Setup — SQL Server (one-time)

This project stores leads in **SQL Server** (via SSMS / Windows Authentication).
Before running the app for the first time, create the database and table:

1. Open **SQL Server Management Studio (SSMS)**, connect to `localhost`
2. Open a **New Query** window and run:

```sql
CREATE DATABASE PortfolioDB;
GO
USE PortfolioDB;
GO
CREATE TABLE inquiries (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    created_at    DATETIME      NOT NULL DEFAULT GETDATE(),
    name          NVARCHAR(200) NOT NULL,
    email         NVARCHAR(200) NOT NULL,
    phone         NVARCHAR(50),
    business      NVARCHAR(200),
    service_type  NVARCHAR(100),
    budget        NVARCHAR(100),
    message       NVARCHAR(MAX) NOT NULL,
    status        NVARCHAR(20)  NOT NULL DEFAULT 'New',
    notes         NVARCHAR(MAX) DEFAULT ''
);
GO
```

3. The app connects using **Windows Authentication** by default (same as
   SSMS), pointing at `localhost` / `PortfolioDB`. No password needed for
   local development.

**If your SQL Server uses a named instance** (e.g. `localhost\SQLEXPRESS`),
set it before running:
```bash
set SQL_SERVER=localhost\SQLEXPRESS
```

**If you use SQL Server Authentication instead of Windows Auth**, set:
```bash
set SQL_USER=your_sql_username
set SQL_PASSWORD=your_sql_password
```

**Driver requirement:** the app uses `pyodbc` with "ODBC Driver 17 for SQL
Server." This is usually already installed alongside SQL Server/SSMS. If you
get a driver-not-found error, download it from Microsoft's
[ODBC Driver for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) page.

---

## 3. Admin Dashboard — View & Manage Leads

Every contact form submission is saved to **SQL Server**, viewable from a
browser dashboard instead of SSMS or a text file.

**Access it at:** `http://127.0.0.1:5000/admin/login`

**Default login (CHANGE THIS):**
```
Username: naveen
Password: changeme123
```

Set your own credentials via environment variables before deploying:
```bash
set ADMIN_USERNAME=your-username
set ADMIN_PASSWORD=a-strong-password
```

**Dashboard features:**
- Live stat cards (Total, New, Contacted, Won, Lost)
- Filter leads by status, search by name/email/business
- Click any lead to view full details, add private notes, or delete
- Update lead status inline — changes save instantly
- Auto-refreshes every 8 seconds to show new leads as they arrive (pauses when tab isn't active)
- One-click WhatsApp or Email reply buttons on each lead

---

## 4. WhatsApp Lead Alerts (CallMeBot)

Get a WhatsApp message on your phone the instant someone submits the contact
form — no Meta Business approval needed, uses the free CallMeBot API.

**One-time setup:**
1. Save **+34 644 59 71 67** as a contact in your phone
2. WhatsApp this exact message to that number: `I allow callmebot to send me messages`
3. You'll receive a reply containing your **API key** (a number)
4. Set it as an environment variable before running the app:
```bash
set WHATSAPP_APIKEY=your_api_key_here
set WHATSAPP_PHONE=919177393699
```

If `WHATSAPP_APIKEY` is left blank, WhatsApp alerts are silently skipped —
leads are still saved to the database either way.

---

## 2. Running Locally

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py

# 4. Open in browser
http://127.0.0.1:5000
```

---

## 5. Configuring the Contact Form (Email Notifications)

By default, leads are saved to `inquiries.log`. To also receive an email for
every new lead, set these environment variables before running the app:

```bash
export OWNER_EMAIL="naveennimmala@gmail.com"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-sending-address@gmail.com"
export SMTP_PASS="your-gmail-app-password"   # NOT your normal password
```

> For Gmail, create an **App Password** under Google Account → Security →
> 2-Step Verification → App Passwords. Regular account passwords will not work.

If `SMTP_USER`/`SMTP_PASS` are left blank, email sending is silently skipped
and leads still get saved to the database (visible in the admin dashboard).

---

## 6. Before You Go Live — Checklist

- [ ] **Change the admin password** (`ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars) — this is critical
- [ ] Set up the SQL Server database/table (Section 2) before first run
- [ ] Replace placeholder WhatsApp number `919999999999` (search/replace across
      `base.html`, `index.html`, `portfolio.html`, `pricing.html`, `contact.html`)
- [ ] Update real email, LinkedIn, GitHub links in `base.html` footer
- [ ] Replace gradient placeholder project thumbnails (`.port-img--*` in
      `style.css`) with real screenshots in `static/images/` and update the
      `port-img` CSS rules to use `background-image: url(...)`
- [ ] Update testimonials with real client quotes (with permission)
- [ ] Set a strong `SECRET_KEY` environment variable in production
- [ ] Add Google Analytics / Search Console verification tag if desired
- [ ] Add a real `robots.txt` and `sitemap.xml` for SEO
- [ ] Test the contact form end-to-end with SMTP credentials configured

---

## 7. Deployment Instructions

### Option A — Render.com / Railway.app (easiest, free tier available)
1. Push this project to a GitHub repository.
2. Create a new **Web Service** on Render/Railway, connect your repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables (`SECRET_KEY`, `SMTP_USER`, `SMTP_PASS`, etc.) in
   the dashboard.
6. Deploy — you'll get a free `*.onrender.com` / `*.up.railway.app` URL. Point
   your custom domain to it via CNAME.

### Option B — DigitalOcean / VPS (more control)
```bash
# On the server
sudo apt update && sudo apt install python3-pip python3-venv nginx -y
git clone <your-repo-url> portfolio && cd portfolio
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run with gunicorn
gunicorn --workers 3 --bind 0.0.0.0:8000 app:app

# Configure Nginx as a reverse proxy → port 8000, and Certbot for free HTTPS:
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```
Use `systemd` or `supervisor` to keep gunicorn running after reboot.

### Option C — Hostinger Shared Hosting (Python apps)
1. Use Hostinger's "Setup Python App" feature in hPanel.
2. Upload the project via Git or File Manager.
3. Set the entry point to `app.py`, application object `app`.
4. Install `requirements.txt` from the hPanel interface.
5. Map your domain to the app.

---

## 8. Future Enhancements

- ~~Admin dashboard to view/manage leads~~ ✅ **Done** — see Section 3 above
- ~~Database instead of flat-file storage~~ ✅ **Done** — SQL Server via `database.py`
- ~~WhatsApp lead notifications~~ ✅ **Done** — via CallMeBot (Section 4)
- **Blog section** for SEO content marketing (Flask + Markdown or a simple CMS).
- **Live chat widget** as an alternative/complement to WhatsApp.
- **Client portal** — login area for active clients to track project status.
- **Case studies** with before/after results and metrics for each portfolio piece.
- **Multi-language support** (English/Telugu) using Flask-Babel.
- **Automated email drip** for leads who don't convert immediately.
- **Razorpay/Stripe integration** for accepting advance payments online.
- **Dark/Light theme toggle** (currently dark-mode only by design).
- **Export leads to CSV/Excel** directly from the admin dashboard.
- **Multiple admin users** with proper password hashing (currently a single
  shared username/password — fine for one person, not for a team).

---

Built by Naveen Nimmala — Guntur, Andhra Pradesh, India.
