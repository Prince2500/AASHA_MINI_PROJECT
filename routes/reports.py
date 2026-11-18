import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_from_directory
from models import db
from models.user import User, ASHAWorker, Doctor
from models.patient import Patient
from models.report import PatientReport, VoiceTranscription, AISummary, DoctorResponse, Notification
from services.ai_extraction import process_clinical_note
from services.triage import assess_triage
from services.speech_to_text import save_audio_file, get_preset_scenarios
from services.notifications import notify_doctor_new_report, get_user_notifications, get_unread_count
from routes.auth import login_required, worker_required

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/record')
@worker_required
def record_voice():
    user = db.get_or_404(User, session.get('user_id'))
    worker = user.asha_profile

    # Patients registered by this worker
    patients = Patient.query.filter_by(asha_worker_id=worker.id).order_by(Patient.name.asc()).all()
    
    # Pre-select patient if passed in query param
    selected_patient_id = request.args.get('patient_id', type=int)
    preset_scenarios = get_preset_scenarios()

    if not worker.assigned_doctor:
        flash("Notice: You currently do not have an assigned Doctor. Please update your profile or select a Doctor so reports can be reviewed.", "warning")

    return render_template(
        'record_voice.html',
        user=user,
        worker=worker,
        patients=patients,
        selected_patient_id=selected_patient_id,
        preset_scenarios=preset_scenarios
    )


@reports_bp.route('/api/analyze-preview', methods=['POST'])
@login_required
def analyze_preview():
    """
    Real-time API to preview AI clinical extraction and smart triage
    before final submission.
    """
    data = request.get_json() or {}
    transcript = data.get('transcript', '').strip()
    patient_id = data.get('patient_id')

    if not transcript:
        return jsonify({'error': 'Transcript text is required'}), 400

    patient_info = None
    if patient_id:
        patient = db.session.get(Patient, patient_id)
        if patient:
            patient_info = patient.to_dict()

    # 1. AI Extraction
    extraction_result = process_clinical_note(transcript, patient_info)

    # 2. Smart Triage Assessment
    triage_result = assess_triage(
        text=transcript,
        patient_age=patient_info.get('age') if patient_info else None,
        pregnancy_status=patient_info.get('pregnancy_status') if patient_info else None,
        existing_conditions=patient_info.get('medical_conditions') if patient_info else None
    )

    return jsonify({
        'extraction': extraction_result,
        'triage': triage_result
    })


@reports_bp.route('/reports/submit', methods=['POST'])
@worker_required
def submit_report():
    user = db.get_or_404(User, session.get('user_id'))
    worker = user.asha_profile

    patient_id = request.form.get('patient_id')
    raw_transcript = request.form.get('raw_transcript', '').strip()
    edited_transcript = request.form.get('edited_transcript', '').strip() or raw_transcript
    language = request.form.get('language', 'hi-IN')

    if not patient_id:
        flash("Please select a patient.", "warning")
        return redirect(url_for('reports.record_voice'))

    patient = Patient.query.filter_by(id=patient_id, asha_worker_id=worker.id).first_or_404()

    if not edited_transcript:
        flash("Voice transcript cannot be empty. Please speak or enter the patient update.", "warning")
        return redirect(url_for('reports.record_voice', patient_id=patient.id))

    # Doctor assignment check
    doctor = worker.assigned_doctor
    if not doctor:
        # Fallback to any doctor if not assigned
        doctor = Doctor.query.first()
        if not doctor:
            flash("No doctors are currently registered in the system. Please register a doctor first.", "danger")
            return redirect(url_for('worker.dashboard'))

    # Handle Audio file upload (if recorded via browser MediaRecorder or uploaded)
    audio_file = request.files.get('audio_file')
    audio_filename = None
    if audio_file and audio_file.filename:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        audio_filename = save_audio_file(audio_file, upload_folder)

    # 1. AI Clinical Extraction
    patient_context = patient.to_dict()
    extraction_result = process_clinical_note(edited_transcript, patient_context)

    # 2. Smart Triage Assessment
    triage_result = assess_triage(
        text=edited_transcript,
        patient_age=patient.age,
        pregnancy_status=patient.pregnancy_status,
        existing_conditions=patient.medical_conditions
    )

    # 3. Create Patient Report Record
    report = PatientReport(
        patient_id=patient.id,
        asha_worker_id=worker.id,
        doctor_id=doctor.id,
        priority=triage_result['priority'],
        case_status='Pending Review'
    )
    db.session.add(report)
    db.session.flush()

    # 4. Save Voice Transcription
    transcription = VoiceTranscription(
        report_id=report.id,
        audio_filename=audio_filename,
        audio_path=f"uploads/audio/{audio_filename}" if audio_filename else None,
        raw_transcript=raw_transcript or edited_transcript,
        edited_transcript=edited_transcript,
        language=language
    )
    db.session.add(transcription)

    # 5. Save AI Summary & Triage
    summary = AISummary(
        report_id=report.id,
        symptoms_json=json.dumps(extraction_result.get('symptoms', [])),
        duration=extraction_result.get('duration', 'Not explicitly stated'),
        observations=extraction_result.get('observations', ''),
        pregnancy_notes=extraction_result.get('pregnancy_notes', ''),
        medicines_mentioned=extraction_result.get('medicines_mentioned', ''),
        other_information=extraction_result.get('other_information', ''),
        structured_summary=extraction_result.get('structured_summary', ''),
        triage_rationale=triage_result.get('rationale', ''),
        warning_signs_json=json.dumps(triage_result.get('warning_signs', []))
    )
    db.session.add(summary)
    db.session.commit()

    # 6. Notify Doctor immediately
    notify_doctor_new_report(report)

    if report.priority == 'Urgent':
        flash(f"CRITICAL WARNING: Case marked as URGENT! Instant alert transmitted to Dr. {doctor.user.full_name}.", "danger")
    else:
        flash(f"Report submitted successfully and routed to Dr. {doctor.user.full_name} for clinical review.", "success")

    return redirect(url_for('reports.view_report', report_id=report.id))


@reports_bp.route('/reports/<int:report_id>')
@login_required
def view_report(report_id):
    report = db.get_or_404(PatientReport, report_id)
    user = db.get_or_404(User, session.get('user_id'))

    # Access control: Only the assigned ASHA Worker or assigned Doctor can view this report
    if user.role == 'asha_worker':
        if report.asha_worker_id != user.asha_profile.id:
            flash("Unauthorized access: You cannot view reports submitted by other healthcare workers.", "danger")
            return redirect(url_for('worker.dashboard'))
    elif user.role == 'doctor':
        if report.doctor_id != user.doctor_profile.id:
            flash("Unauthorized access: You cannot view reports assigned to other doctors.", "danger")
            return redirect(url_for('doctor.dashboard'))

    return render_template('report.html', report=report, user=user)


@reports_bp.route('/uploads/audio/<filename>')
def serve_audio(filename):
    """
    Serves recorded patient voice audio files.
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, filename)


# --- Notification API Endpoints ---

@reports_bp.route('/api/notifications')
@login_required
def fetch_notifications():
    user_id = session.get('user_id')
    notifs = get_user_notifications(user_id, limit=15)
    unread = get_unread_count(user_id)
    return jsonify({
        'unread_count': unread,
        'notifications': [n.to_dict() for n in notifs]
    })


@reports_bp.route('/api/notifications/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    user_id = session.get('user_id')
    notif = Notification.query.filter_by(id=notif_id, recipient_user_id=user_id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'unread_count': get_unread_count(user_id)})


@reports_bp.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user_id = session.get('user_id')
    Notification.query.filter_by(recipient_user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True, 'unread_count': 0})
