# System architecture

The browser renders HTML from Jinja templates and submits normal form requests to Flask. Flask validates input, checks the session, calls SQLAlchemy models, and renders the next view. SQLite stores the data locally without a separate server.

`app.py` is intentionally the main route module so a student can trace a request from URL to database operation. The matching calculation is isolated in `services/matching.py`, while models remain in `models.py`. Shared navigation and flash messaging live in `templates/base.html`.
