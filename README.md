# SkillSwap – Student Skill Exchange Platform

A peer-to-peer student skill exchange web app. Students list what they can teach and what they want to learn; the platform finds compatible learning partners using a rule-based matching algorithm.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask 3.1 |
| Database | SQLite (local) · PostgreSQL (Render) |
| ORM | Flask-SQLAlchemy |
| Auth / Security | Flask-WTF CSRF, Werkzeug password hashing |
| Frontend | HTML5, CSS3, Vanilla JS, Bootstrap Icons |
| Typography | Google Fonts – Inter |
| Deployment | Render (free tier) |

---

## Features

- Student registration & login
- Skill portfolio (teach / learn with proficiency levels)
- Explainable rule-based matching algorithm (0–100% score)
- Partner discovery with search & department filter
- Connection requests (send, accept, reject)
- Direct peer messaging
- Post-exchange ratings & feedback
- In-app notifications
- Admin panel (users, skills, connections, feedback)

---

## Matching Algorithm

```
Score = min(100, desired_match + offered_match + reciprocal_bonus)
```

| Rule | Points |
|---|---|
| Candidate teaches a skill you want to learn | +30 |
| Candidate wants to learn a skill you can teach | +20 |
| True mutual barter (both conditions above) | +50 bonus |
| Fallback discovery | 10 |

**Tiers:** 80–100% Strong Match · 50–79% Good Match · 20–49% Potential Match · <20% Discover

---

## Local Development

### 1. Clone and set up

```bash
git clone <your-repo-url>
cd skillswap
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY to any random string
```

### 3. Run

```bash
python app.py
```

Open **http://127.0.0.1:5000**

The SQLite database (`skillswap.db`) and demo accounts are created automatically on first run.

---

## Demo Accounts (password: `password123`)

| Name | Email | Teaches | Wants to Learn |
|---|---|---|---|
| Rahul Sharma | `rahul@example.com` | Python, C++ | React |
| Priya Patel | `priya@example.com` | React, UI/UX Design | Python |
| Aman Verma | `aman@example.com` | Java | Python |
| Neha Singh | `neha@example.com` | AutoCAD | HTML & CSS |

> **Demo tip:** Rahul ↔ Priya is a **100% Strong Match** (mutual Python ↔ React swap).

**Admin:** `admin@skillswap.local` / `admin123` → `/admin/login`

---

## Deploy to Render (Free)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<your-username>/skillswap.git
git push -u origin main
```

### Step 2 — Create Render account

Go to [render.com](https://render.com) and sign up for free (GitHub login recommended).

### Step 3 — New Web Service

1. Click **New → Web Service**
2. Connect your GitHub repository
3. Render auto-detects `render.yaml` — click **Apply**

That's it. Render will:
- Create a **free PostgreSQL database** (`skillswap-db`)
- Deploy the Flask app with **gunicorn**
- Set `DATABASE_URL` and `SECRET_KEY` automatically

### Step 4 — First deploy

The first deploy takes ~3 minutes. After it completes, your app is live at:
```
https://skillswap.onrender.com
```

> **Note:** The free tier spins down after 15 minutes of inactivity. The first request after sleep takes ~30 seconds to wake up — this is normal for free Render hosting.

### Manual setup (without render.yaml)

If you prefer manual setup on Render:

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT` |
| Environment Variables | `SECRET_KEY` = any random string · `FLASK_DEBUG` = `0` |

Then add a **free PostgreSQL** database from the Render dashboard and copy its **Internal Database URL** into an env var named `DATABASE_URL`.

---

## Project Structure

```
skillswap/
├── app.py                  # Flask routes & application factory
├── models.py               # SQLAlchemy models (User, Skill, Connection…)
├── config.py               # Configuration (SQLite local / PostgreSQL Render)
├── services/
│   └── matching.py         # Rule-based skill matching engine
├── templates/
│   ├── base.html           # Global layout (nav, footer, flash messages)
│   ├── index.html          # Landing page
│   ├── auth.html           # Login / Register (shared template)
│   ├── dashboard.html      # Student dashboard & match suggestions
│   ├── skills.html         # Manage teach/learn skills
│   ├── find_partners.html  # Browse & filter partners
│   ├── profile.html        # View student profile
│   ├── connections.html    # Accepted connections
│   ├── requests.html       # Incoming connection requests
│   ├── chat.html           # Direct peer chat
│   ├── messages.html       # Messages inbox
│   ├── feedback.html       # Submit exchange rating
│   ├── settings.html       # Account settings
│   ├── about.html          # About page
│   └── admin/              # Admin panel templates
├── static/
│   ├── css/style.css       # Branded design system
│   └── js/script.js        # Interactive UI
├── Procfile                # gunicorn start command for Render
├── render.yaml             # Render Blueprint (web service + free DB)
├── requirements.txt        # Python dependencies
└── .env.example            # Environment variable template
```

---

## Security

- All passwords hashed with Werkzeug (bcrypt)
- CSRF protection on every form via Flask-WTF
- SQLAlchemy parameterized queries (no raw SQL)
- Session-based authentication
