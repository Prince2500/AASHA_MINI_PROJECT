from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models import db
from models.user import User, ASHAWorker, Doctor

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def worker_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access the ASHA Worker portal.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'asha_worker':
            flash('Access restricted to registered ASHA Workers.', 'danger')
            return redirect(url_for('doctor.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access the Doctor portal.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'doctor':
            flash('Access restricted to registered Doctors.', 'danger')
            return redirect(url_for('worker.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'asha_worker':
            return redirect(url_for('worker.dashboard'))
        else:
            return redirect(url_for('doctor.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            session['email'] = user.email
            session['full_name'] = user.full_name
            session['role'] = user.role

            flash(f"Welcome back, {user.full_name}!", "success")
            if user.role == 'asha_worker':
                return redirect(url_for('worker.dashboard'))
            else:
                return redirect(url_for('doctor.dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('login.html')


@auth_bp.route('/demo-login/<role>')
def demo_login(role):
    """
    Convenience route for rapid testing and reviewer evaluation.
    """
    if role == 'worker':
        user = User.query.filter_by(role='asha_worker').first()
    elif role == 'doctor':
        user = User.query.filter_by(role='doctor').first()
    else:
        flash("Invalid demo role.", "danger")
        return redirect(url_for('auth.login'))

    if user:
        session.clear()
        session['user_id'] = user.id
        session['email'] = user.email
        session['full_name'] = user.full_name
        session['role'] = user.role
        flash(f"Logged in as Demo {user.role.replace('_', ' ').title()}: {user.full_name}", "info")
        if user.role == 'asha_worker':
            return redirect(url_for('worker.dashboard'))
        else:
            return redirect(url_for('doctor.dashboard'))
    else:
        flash("Sample accounts not initialized yet.", "warning")
        return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Pass available doctors for ASHA worker assignment dropdown
    doctors = Doctor.query.join(User).all()

    if request.method == 'POST':
        role = request.form.get('role')
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not full_name or not email or not password or not phone:
            flash("Please fill in all mandatory fields.", "warning")
            return render_template('register.html', doctors=doctors)

        # Check existing user
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please log in.", "danger")
            return render_template('register.html', doctors=doctors)

        new_user = User(
            email=email,
            role=role,
            full_name=full_name,
            phone=phone
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        if role == 'asha_worker':
            village = request.form.get('village', '').strip()
            district = request.form.get('district', '').strip()
            state = request.form.get('state', '').strip()
            assigned_doctor_id = request.form.get('assigned_doctor_id')
            
            # If no doctor chosen, select the first available doctor
            if not assigned_doctor_id and doctors:
                assigned_doctor_id = doctors[0].id

            worker = ASHAWorker(
                user_id=new_user.id,
                village=village or 'Gram Panchayat',
                district=district or 'Rural District',
                state=state or 'State',
                assigned_doctor_id=int(assigned_doctor_id) if assigned_doctor_id else None
            )
            db.session.add(worker)

        elif role == 'doctor':
            reg_number = request.form.get('reg_number', '').strip()
            specialisation = request.form.get('specialisation', '').strip()
            hospital_centre = request.form.get('hospital_centre', '').strip()

            # Check reg number uniqueness
            if Doctor.query.filter_by(reg_number=reg_number).first():
                flash("A doctor with this Medical Registration Number already exists.", "danger")
                db.session.rollback()
                return render_template('register.html', doctors=doctors)

            doctor = Doctor(
                user_id=new_user.id,
                reg_number=reg_number or f"MCI-{new_user.id:05d}",
                specialisation=specialisation or 'General Medicine / Primary Care',
                hospital_centre=hospital_centre or 'Primary Health Centre'
            )
            db.session.add(doctor)

        db.session.commit()

        # Log user in directly
        session.clear()
        session['user_id'] = new_user.id
        session['email'] = new_user.email
        session['full_name'] = new_user.full_name
        session['role'] = new_user.role

        flash(f"Registration successful! Welcome to AASHA, {new_user.full_name}.", "success")
        if role == 'asha_worker':
            return redirect(url_for('worker.dashboard'))
        else:
            return redirect(url_for('doctor.dashboard'))

    return render_template('register.html', doctors=doctors)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('index'))
