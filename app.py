import os
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup, escape
from sqlalchemy import or_

from config import Config
from models import Connection, Feedback, Message, Notification, Skill, User, UserSkill, db
from services.matching import calculate_match

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = Path(app.config['UPLOAD_FOLDER'])
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
db.init_app(app)
csrf = CSRFProtect(app)

CATEGORIES = ['Programming', 'Web Development', 'Mobile Development', 'Design', 'Communication', 'Marketing', 'Video Editing', 'Photography', 'Music', 'Academic', 'Languages', 'Other']
SEED_SKILLS = [('Python', 'Programming'), ('C++', 'Programming'), ('Java', 'Programming'), ('React', 'Web Development'), ('HTML & CSS', 'Web Development'), ('UI/UX Design', 'Design'), ('Git', 'Programming'), ('AutoCAD', 'Design'), ('Public Speaking', 'Communication'), ('Photography', 'Photography')]


def current_user():
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def skill_names(user, skill_type):
    return [item.skill.skill_name for item in user.skills_by_type(skill_type)]


def partner_match(user, candidate):
    return calculate_match(skill_names(user, 'teach'), skill_names(user, 'learn'), skill_names(candidate, 'teach'), skill_names(candidate, 'learn'))


@app.context_processor
def inject_globals():
    user = current_user()
    unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count() if user else 0
    def csrf_field():
        return Markup(f'<input type="hidden" name="csrf_token" value="{escape(generate_csrf())}">')
    return {'current_user': user, 'categories': CATEGORIES, 'unread_count': unread_count, 'skill_names': skill_names, 'partner_match': partner_match, 'csrf_token': csrf_field}


@app.route('/')
def index():
    return render_template('index.html', title='Learn from your peers')


@app.route('/about')
def about():
    return render_template('about.html', title='About')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user():
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not name or not email or not request.form.get('college') or not request.form.get('department'):
            flash('Complete all required profile fields.', 'danger')
        elif len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('That email is already registered.', 'danger')
        else:
            user = User(name=name, email=email, college=request.form['college'].strip(), department=request.form['department'], year=request.form.get('year', ''), bio=request.form.get('bio', '').strip())
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Account created. You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('auth.html', title='Create account', mode='register')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user():
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email', '').strip().lower()).first()
        if user and user.check_password(request.form.get('password', '')):
            session.clear()
            session['user_id'] = user.id
            flash(f'Welcome back, {user.name.split()[0]}.', 'success')
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('We could not match that email and password.', 'danger')
    return render_template('auth.html', title='Log in', mode='login')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user()
    candidates = User.query.filter(User.id != user.id).all()
    suggestions = sorted(((candidate, partner_match(user, candidate)) for candidate in candidates), key=lambda pair: pair[1]['score'], reverse=True)[:6]
    connection_count = Connection.query.filter(Connection.status == 'accepted', or_(Connection.sender_id == user.id, Connection.receiver_id == user.id)).count()
    return render_template('dashboard.html', title='Dashboard', suggestions=suggestions, connection_count=connection_count)


@app.route('/profile')
@login_required
def profile():
    user = current_user()
    user_id = user.id

    # --- Stats ---
    teach_count = len(user.skills_by_type('teach'))
    learn_count = len(user.skills_by_type('learn'))
    accepted_connections = Connection.query.filter(
        Connection.status == 'accepted',
        or_(Connection.sender_id == user_id, Connection.receiver_id == user_id)
    ).all()
    connection_count = len(accepted_connections)

    # --- Requests ---
    incoming_requests = Connection.query.filter_by(receiver_id=user_id, status='pending').order_by(Connection.created_at.desc()).all()
    outgoing_requests = Connection.query.filter_by(sender_id=user_id, status='pending').order_by(Connection.created_at.desc()).all()

    # --- Recent messages (last 5 distinct conversations) ---
    sent = db.session.query(Message.receiver_id).filter_by(sender_id=user_id).distinct().limit(5).all()
    received = db.session.query(Message.sender_id).filter_by(receiver_id=user_id).distinct().limit(5).all()
    chat_partner_ids = list({uid for (uid,) in sent + received})[:5]
    chat_partners = []
    for pid in chat_partner_ids:
        partner = db.session.get(User, pid)
        if partner:
            last_msg = Message.query.filter(
                or_(
                    (Message.sender_id == user_id) & (Message.receiver_id == pid),
                    (Message.sender_id == pid) & (Message.receiver_id == user_id)
                )
            ).order_by(Message.created_at.desc()).first()
            unread = Message.query.filter_by(sender_id=pid, receiver_id=user_id, is_read=False).count()
            chat_partners.append({'user': partner, 'last_message': last_msg, 'unread': unread})

    # --- Feedback received ---
    feedback_received = Feedback.query.filter_by(to_user_id=user_id).order_by(Feedback.created_at.desc()).all()
    avg_rating = 0
    if feedback_received:
        avg_rating = round(sum(f.rating for f in feedback_received) / len(feedback_received), 1)

    # --- Notifications (last 8) ---
    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(8).all()
    unread_notifs = sum(1 for n in notifications if not n.is_read)

    return render_template('profile.html', title='My profile', profile_user=user, own_profile=True,
                           teach_count=teach_count, learn_count=learn_count,
                           connection_count=connection_count, accepted_connections=accepted_connections,
                           incoming_requests=incoming_requests, outgoing_requests=outgoing_requests,
                           chat_partners=chat_partners,
                           feedback_received=feedback_received, avg_rating=avg_rating,
                           notifications=notifications, unread_notifs=unread_notifs)


@app.route('/profile/<int:user_id>')
@login_required
def partner_profile(user_id):
    profile_user = db.get_or_404(User, user_id)
    if profile_user.id == current_user().id:
        return redirect(url_for('profile'))
    return render_template('profile.html', title=profile_user.name, profile_user=profile_user, own_profile=False, match=partner_match(current_user(), profile_user))


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = current_user()
    if request.method == 'POST':
        user.name = request.form.get('name', '').strip() or user.name
        user.college = request.form.get('college', '').strip() or user.college
        user.department = request.form.get('department', user.department)
        user.year = request.form.get('year', '').strip()
        user.bio = request.form.get('bio', '').strip()
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', title='Edit profile', profile_user=user)


@app.route('/skills', methods=['GET', 'POST'])
@login_required
def skills():
    user = current_user()
    if request.method == 'POST':
        skill_name = request.form.get('skill_name', '').strip()
        skill_type = request.form.get('type')
        level = request.form.get('level', 'Beginner')
        if skill_type not in ('teach', 'learn') or not skill_name:
            flash('Choose a skill and skill direction.', 'danger')
        else:
            skill = Skill.query.filter_by(skill_name=skill_name).first()
            if not skill:
                skill = Skill(skill_name=skill_name, category=request.form.get('category', 'Other'))
                db.session.add(skill)
                db.session.flush()
            duplicate = UserSkill.query.filter_by(user_id=user.id, skill_id=skill.id, type=skill_type).first()
            if duplicate:
                flash('That skill is already on your profile.', 'info')
            else:
                db.session.add(UserSkill(user_id=user.id, skill_id=skill.id, type=skill_type, level=level))
                db.session.commit()
                flash('Skill added.', 'success')
        return redirect(url_for('skills'))
    all_skills = Skill.query.order_by(Skill.skill_name).all()
    return render_template('skills.html', title='My skills', all_skills=all_skills)


@app.post('/skills/<int:skill_id>/remove')
@login_required
def remove_skill(skill_id):
    item = UserSkill.query.filter_by(id=skill_id, user_id=current_user().id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Skill removed.', 'success')
    return redirect(url_for('skills'))


@app.route('/find-partners')
@login_required
def find_partners():
    user = current_user()
    query = User.query.filter(User.id != user.id)
    skill_query = request.args.get('skill', '').strip().lower()
    department = request.args.get('department', '').strip()
    college = request.args.get('college', '').strip()
    candidates = query.filter(User.department == department) if department else query
    candidates = candidates.filter(User.college.ilike(f'%{college}%')) if college else candidates
    results = []
    for candidate in candidates.all():
        match = partner_match(user, candidate)
        if not skill_query or any(skill_query in name.lower() for name in skill_names(candidate, 'teach') + skill_names(candidate, 'learn')):
            results.append((candidate, match))
    results.sort(key=lambda pair: pair[1]['score'], reverse=True)
    return render_template('find_partners.html', title='Find partners', results=results, selected_skill=skill_query, selected_department=department)


@app.post('/connections/request/<int:user_id>')
@login_required
def send_request(user_id):
    user = current_user()
    if user.id == user_id:
        flash('You cannot connect with yourself.', 'danger')
        return redirect(request.referrer or url_for('find_partners'))
    receiver = db.get_or_404(User, user_id)
    existing = Connection.query.filter(or_((Connection.sender_id == user.id) & (Connection.receiver_id == receiver.id), (Connection.sender_id == receiver.id) & (Connection.receiver_id == user.id))).first()
    if existing and existing.status == 'pending':
        flash('A connection request is already pending.', 'info')
    elif existing and existing.status == 'accepted':
        flash('You are already connected.', 'info')
    else:
        connection = existing or Connection(sender_id=user.id, receiver_id=receiver.id)
        connection.sender_id = user.id
        connection.receiver_id = receiver.id
        connection.status = 'pending'
        db.session.add(connection)
        db.session.add(Notification(user_id=receiver.id, type='request', message=f'{user.name} sent you a skill exchange request.'))
        db.session.commit()
        flash('Connection request sent.', 'success')
    return redirect(request.referrer or url_for('find_partners'))


@app.route('/requests')
@login_required
def requests_page():
    incoming = Connection.query.filter_by(receiver_id=current_user().id, status='pending').order_by(Connection.created_at.desc()).all()
    return render_template('requests.html', title='Requests', incoming=incoming)


@app.post('/requests/<int:connection_id>/<action>')
@login_required
def request_action(connection_id, action):
    connection = db.get_or_404(Connection, connection_id)
    if connection.receiver_id != current_user().id or action not in ('accept', 'reject'):
        abort(403)
    connection.status = 'accepted' if action == 'accept' else 'rejected'
    if action == 'accept':
        db.session.add(Notification(user_id=connection.sender_id, type='accepted', message=f'{current_user().name} accepted your connection request.'))
    db.session.commit()
    flash(f'Request {action}ed.', 'success')
    return redirect(request.referrer or url_for('requests_page'))


@app.post('/requests/<int:connection_id>/cancel')
@login_required
def cancel_request(connection_id):
    connection = db.get_or_404(Connection, connection_id)
    if connection.sender_id != current_user().id or connection.status != 'pending':
        abort(403)
    db.session.delete(connection)
    db.session.commit()
    flash('Request cancelled.', 'success')
    return redirect(request.referrer or url_for('profile'))


@app.post('/notifications/read-all')
@login_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user().id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(request.referrer or url_for('profile'))


@app.route('/connections')
@login_required
def connections():
    user_id = current_user().id
    items = Connection.query.filter(Connection.status == 'accepted', or_(Connection.sender_id == user_id, Connection.receiver_id == user_id)).all()
    return render_template('connections.html', title='Connections', connections=items)


@app.route('/messages')
@login_required
def messages():
    return render_template('messages.html', title='Messages', connections=connections_for(current_user().id))


def connections_for(user_id):
    return Connection.query.filter(Connection.status == 'accepted', or_(Connection.sender_id == user_id, Connection.receiver_id == user_id)).all()


@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat(user_id):
    user = current_user()
    other = db.get_or_404(User, user_id)
    if request.method == 'POST':
        message_text = request.form.get('message', '').strip()
        if message_text:
            db.session.add(Message(sender_id=user.id, receiver_id=other.id, message=message_text))
            db.session.add(Notification(user_id=other.id, type='message', message=f'{user.name} sent you a new message.'))
            db.session.commit()
            return redirect(url_for('chat', user_id=other.id))
        flash('Message cannot be empty.', 'danger')
    chat_messages = Message.query.filter(or_((Message.sender_id == user.id) & (Message.receiver_id == other.id), (Message.sender_id == other.id) & (Message.receiver_id == user.id))).order_by(Message.created_at.asc()).all()
    return render_template('chat.html', title=f'Chat with {other.name}', other=other, chat_messages=chat_messages)


@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    user = current_user()
    if request.method == 'POST':
        connection_id = int(request.form['connection_id'])
        connection = db.get_or_404(Connection, connection_id)
        target = connection.receiver if connection.sender_id == user.id else connection.sender
        if Feedback.query.filter_by(from_user_id=user.id, connection_id=connection_id).first():
            flash('You already left feedback for this exchange.', 'info')
        else:
            db.session.add(Feedback(from_user_id=user.id, to_user_id=target.id, connection_id=connection_id, rating=int(request.form['rating']), comment=request.form.get('comment', '').strip()))
            db.session.add(Notification(user_id=target.id, type='feedback', message=f'{user.name} left feedback for your exchange.'))
            db.session.commit()
            flash('Thanks for sharing your feedback.', 'success')
    return render_template('feedback.html', title='Feedback', connections=connections_for(user.id))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    return render_template('settings.html', title='Settings')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email', '').strip().lower(), is_admin=True).first()
        if user and user.check_password(request.form.get('password', '')):
            session['user_id'] = user.id
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'danger')
    return render_template('admin/login.html', title='Admin login')


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html', title='Admin dashboard', stats={'users': User.query.count(), 'skills': Skill.query.count(), 'connections': Connection.query.count(), 'feedback': Feedback.query.count()})


@app.route('/admin/users')
@admin_required
def admin_users():
    return render_template('admin/users.html', title='Users', users=User.query.order_by(User.created_at.desc()).all())


@app.route('/admin/skills')
@admin_required
def admin_skills():
    return render_template('admin/skills.html', title='Skills', all_skills=Skill.query.order_by(Skill.category, Skill.skill_name).all())


@app.route('/admin/connections')
@admin_required
def admin_connections():
    return render_template('admin/connections.html', title='Connections', connections=Connection.query.order_by(Connection.created_at.desc()).all())


@app.route('/admin/feedback')
@admin_required
def admin_feedback():
    return render_template('admin/feedback.html', title='Feedback', feedback=Feedback.query.order_by(Feedback.created_at.desc()).all())


def seed_database():
    if Skill.query.count() == 0:
        db.session.add_all([Skill(skill_name=name, category=category) for name, category in SEED_SKILLS])
    if User.query.count() == 0:
        demo_data = [
            ('Rahul Sharma', 'rahul@example.com', 'Computer Science', ['Python', 'C++'], ['React']),
            ('Priya Patel', 'priya@example.com', 'Information Technology', ['React', 'UI/UX Design'], ['Python']),
            ('Aman Verma', 'aman@example.com', 'Computer Science', ['Java'], ['Python']),
            ('Neha Singh', 'neha@example.com', 'Mechanical', ['AutoCAD'], ['HTML & CSS']),
        ]
        for name, email, department, teaches, learns in demo_data:
            user = User(name=name, email=email, college='Northbridge University', department=department, year='2nd year', bio='Curious about learning by building with other students.')
            user.set_password('password123')
            db.session.add(user)
            db.session.flush()
            for skill_name in teaches:
                skill = Skill.query.filter_by(skill_name=skill_name).first()
                if skill:
                    db.session.add(UserSkill(user_id=user.id, skill_id=skill.id, type='teach', level='Intermediate'))
            for skill_name in learns:
                skill = Skill.query.filter_by(skill_name=skill_name).first()
                if skill:
                    db.session.add(UserSkill(user_id=user.id, skill_id=skill.id, type='learn', level='Beginner'))
        admin = User(name='SkillSwap Admin', email='admin@skillswap.local', college='SkillSwap', department='Administration', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_database()


if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', '1') == '1')
