from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from models import db
from models.user import User, ASHAWorker, Doctor
from models.patient import Patient
from models.report import PatientReport
from routes.auth import login_required, worker_required

patients_bp = Blueprint('patients', __name__, url_prefix='/patients')

@patients_bp.route('/')
@login_required
def list_patients():
    user = db.get_or_404(User, session.get('user_id'))
    
    if user.role == 'asha_worker':
        worker = user.asha_profile
        patients = Patient.query.filter_by(asha_worker_id=worker.id).order_by(Patient.created_at.desc()).all()
    elif user.role == 'doctor':
        doctor = user.doctor_profile
        # Doctor views patients belonging to their assigned ASHA workers
        worker_ids = [w.id for w in doctor.assigned_workers]
        patients = Patient.query.filter(Patient.asha_worker_id.in_(worker_ids)).order_by(Patient.created_at.desc()).all() if worker_ids else []
    else:
        patients = []

    return render_template('patients_list.html', user=user, patients=patients)


@patients_bp.route('/register', methods=['GET', 'POST'])
@worker_required
def register_patient():
    user = db.get_or_404(User, session.get('user_id'))
    worker = user.asha_profile

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', 'Female')
        village = request.form.get('village', worker.village).strip()
        phone = request.form.get('phone', '').strip()
        pregnancy_status = request.form.get('pregnancy_status', 'Not Pregnant')
        medical_conditions = request.form.get('medical_conditions', '').strip()

        if not name or not age:
            flash("Patient name and age are required.", "warning")
            return render_template('patient_register.html', worker=worker)

        try:
            age_int = int(age)
        except ValueError:
            flash("Please enter a valid age in numbers.", "warning")
            return render_template('patient_register.html', worker=worker)

        # Auto-generate Patient ID Code (e.g., ASH-PAT-0005)
        patient_code = Patient.generate_patient_code()

        new_patient = Patient(
            patient_id_code=patient_code,
            name=name,
            age=age_int,
            gender=gender,
            village=village or worker.village,
            phone=phone if phone else None,
            pregnancy_status=pregnancy_status if gender == 'Female' else 'Not Applicable',
            medical_conditions=medical_conditions if medical_conditions else 'None reported',
            asha_worker_id=worker.id
        )

        db.session.add(new_patient)
        db.session.commit()

        flash(f"Patient {new_patient.name} registered successfully with ID: {new_patient.patient_id_code}", "success")
        
        # Option to immediately record voice note for this new patient
        if 'record_now' in request.form:
            return redirect(url_for('reports.record_voice', patient_id=new_patient.id))
        
        return redirect(url_for('patients.view_patient', patient_id=new_patient.id))

    return render_template('patient_register.html', worker=worker)


@patients_bp.route('/<int:patient_id>')
@login_required
def view_patient(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    user = db.get_or_404(User, session.get('user_id'))

    # Security check: Worker can only view their own patients
    if user.role == 'asha_worker':
        if patient.asha_worker_id != user.asha_profile.id:
            flash("Unauthorized access: You can only view your own registered patients.", "danger")
            return redirect(url_for('worker.dashboard'))
    elif user.role == 'doctor':
        # Doctor can only view patients assigned to them through their workers
        doctor = user.doctor_profile
        worker_ids = [w.id for w in doctor.assigned_workers]
        if patient.asha_worker_id not in worker_ids:
            flash("Unauthorized access: Patient is not assigned to your healthcare jurisdiction.", "danger")
            return redirect(url_for('doctor.dashboard'))

    # Retrieve patient's full clinical history / reports ordered chronologically
    reports = patient.reports.all()

    return render_template('patient.html', patient=patient, reports=reports, user=user)
