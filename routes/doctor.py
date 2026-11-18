from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db
from models.user import User, Doctor, ASHAWorker
from models.patient import Patient
from models.report import PatientReport, DoctorResponse, Notification
from services.notifications import notify_worker_doctor_guidance
from routes.auth import doctor_required

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/dashboard')
@doctor_required
def dashboard():
    user_id = session.get('user_id')
    user = db.get_or_404(User, user_id)
    doctor = user.doctor_profile

    if not doctor:
        flash("Doctor profile not found. Please contact administrator.", "danger")
        return redirect(url_for('auth.logout'))

    # Filter parameters from query string
    priority_filter = request.args.get('priority', 'all')
    status_filter = request.args.get('status', 'all')
    worker_filter = request.args.get('worker', 'all')
    search_query = request.args.get('q', '').strip()

    # Query reports assigned to this doctor
    query = PatientReport.query.filter_by(doctor_id=doctor.id)

    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    if status_filter != 'all':
        query = query.filter_by(case_status=status_filter)
    if worker_filter != 'all':
        query = query.filter_by(asha_worker_id=int(worker_filter))
    if search_query:
        query = query.join(Patient).filter(
            (Patient.name.ilike(f"%{search_query}%")) |
            (Patient.patient_id_code.ilike(f"%{search_query}%"))
        )

    # Urgent cases sorted first, then by newest
    # SQLite / standard SQL: Case expression or sorting
    reports = query.order_by(
        db.case(
            (PatientReport.priority == 'Urgent', 1),
            (PatientReport.priority == 'Moderate', 2),
            else_=3
        ),
        PatientReport.created_at.desc()
    ).all()

    # Metrics across all reports for this doctor
    total_assigned_workers = doctor.assigned_workers.count()
    all_reports = PatientReport.query.filter_by(doctor_id=doctor.id)
    total_reports_count = all_reports.count()
    urgent_count = all_reports.filter_by(priority='Urgent').count()
    moderate_count = all_reports.filter_by(priority='Moderate').count()
    routine_count = all_reports.filter_by(priority='Routine').count()
    pending_count = all_reports.filter_by(case_status='Pending Review').count()

    assigned_workers = doctor.assigned_workers.all()
    notifications = Notification.query.filter_by(recipient_user_id=user.id).order_by(Notification.created_at.desc()).limit(10).all()
    unread_notifs = Notification.query.filter_by(recipient_user_id=user.id, is_read=False).count()

    return render_template(
        'doctor_dashboard.html',
        user=user,
        doctor=doctor,
        reports=reports,
        total_assigned_workers=total_assigned_workers,
        total_reports_count=total_reports_count,
        urgent_count=urgent_count,
        moderate_count=moderate_count,
        routine_count=routine_count,
        pending_count=pending_count,
        assigned_workers=assigned_workers,
        priority_filter=priority_filter,
        status_filter=status_filter,
        worker_filter=worker_filter,
        search_query=search_query,
        notifications=notifications,
        unread_notifs=unread_notifs
    )


@doctor_bp.route('/respond/<int:report_id>', methods=['POST'])
@doctor_required
def send_response(report_id):
    user_id = session.get('user_id')
    user = db.get_or_404(User, user_id)
    doctor = user.doctor_profile

    report = PatientReport.query.filter_by(id=report_id, doctor_id=doctor.id).first_or_404()

    guidance_text = request.form.get('guidance_text', '').strip()
    action_recommended = request.form.get('action_recommended', '').strip()
    status_updated_to = request.form.get('case_status', 'Guidance Sent')

    if not guidance_text:
        flash("Please provide medical guidance instructions before submitting.", "warning")
        return redirect(url_for('reports.view_report', report_id=report.id))

    # Create doctor response record
    doc_response = DoctorResponse(
        report_id=report.id,
        doctor_id=doctor.id,
        guidance_text=guidance_text,
        action_recommended=action_recommended or 'Clinical Guidance Provided',
        status_updated_to=status_updated_to
    )
    db.session.add(doc_response)

    # Update report status
    report.case_status = status_updated_to
    db.session.commit()

    # Trigger notification to ASHA Worker
    notify_worker_doctor_guidance(report, guidance_text, action_recommended)

    flash(f"Clinical guidance transmitted to ASHA Worker {report.asha_worker.user.full_name}. Case updated to '{status_updated_to}'.", "success")
    return redirect(url_for('reports.view_report', report_id=report.id))
