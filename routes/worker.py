from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db
from models.user import User, ASHAWorker, Doctor
from models.patient import Patient
from models.report import PatientReport, DoctorResponse, Notification
from routes.auth import worker_required

worker_bp = Blueprint('worker', __name__, url_prefix='/worker')

@worker_bp.route('/dashboard')
@worker_required
def dashboard():
    user_id = session.get('user_id')
    user = db.get_or_404(User, user_id)
    worker = user.asha_profile

    if not worker:
        flash("ASHA Worker profile not found. Please contact administrator.", "danger")
        return redirect(url_for('auth.logout'))

    # Metrics
    total_patients = Patient.query.filter_by(asha_worker_id=worker.id).count()
    total_reports = PatientReport.query.filter_by(asha_worker_id=worker.id).count()
    urgent_reports = PatientReport.query.filter_by(asha_worker_id=worker.id, priority='Urgent').count()
    pending_doctor = PatientReport.query.filter_by(asha_worker_id=worker.id, case_status='Pending Review').count()
    guidance_received = PatientReport.query.filter_by(asha_worker_id=worker.id, case_status='Guidance Sent').count()

    # Recent reports (ordered by newest first)
    recent_reports = PatientReport.query.filter_by(asha_worker_id=worker.id).order_by(PatientReport.created_at.desc()).limit(10).all()

    # Worker's patients (for quick action dropdown in recording studio)
    patients = Patient.query.filter_by(asha_worker_id=worker.id).order_by(Patient.name.asc()).all()

    # Recent doctor responses to this worker's cases
    recent_responses = DoctorResponse.query.join(PatientReport).filter(PatientReport.asha_worker_id == worker.id).order_by(DoctorResponse.created_at.desc()).limit(5).all()

    # Assigned Doctor info
    assigned_doctor = worker.assigned_doctor

    # Notifications
    notifications = Notification.query.filter_by(recipient_user_id=user.id).order_by(Notification.created_at.desc()).limit(10).all()
    unread_notifs = Notification.query.filter_by(recipient_user_id=user.id, is_read=False).count()

    return render_template(
        'worker_dashboard.html',
        user=user,
        worker=worker,
        assigned_doctor=assigned_doctor,
        total_patients=total_patients,
        total_reports=total_reports,
        urgent_reports=urgent_reports,
        pending_doctor=pending_doctor,
        guidance_received=guidance_received,
        recent_reports=recent_reports,
        patients=patients,
        recent_responses=recent_responses,
        notifications=notifications,
        unread_notifs=unread_notifs
    )


@worker_bp.route('/profile', methods=['GET', 'POST'])
@worker_required
def profile():
    user = db.get_or_404(User, session.get('user_id'))
    worker = user.asha_profile
    doctors = Doctor.query.join(User).all()

    if request.method == 'POST':
        user.full_name = request.form.get('full_name', user.full_name).strip()
        user.phone = request.form.get('phone', user.phone).strip()
        worker.village = request.form.get('village', worker.village).strip()
        worker.district = request.form.get('district', worker.district).strip()
        worker.state = request.form.get('state', worker.state).strip()
        
        doc_id = request.form.get('assigned_doctor_id')
        if doc_id:
            worker.assigned_doctor_id = int(doc_id)

        db.session.commit()
        session['full_name'] = user.full_name
        flash("Worker profile updated successfully.", "success")
        return redirect(url_for('worker.dashboard'))

    return render_template('worker_profile.html', user=user, worker=worker, doctors=doctors)
