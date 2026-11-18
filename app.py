import os
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, session, g
from config import Config
from models import db
from models.user import User, ASHAWorker, Doctor
from models.patient import Patient
from models.report import PatientReport, VoiceTranscription, AISummary, DoctorResponse, Notification
from routes import auth_bp, worker_bp, doctor_bp, patients_bp, reports_bp
from services.notifications import get_unread_count

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(reports_bp)

    # Global context processor for navbars, unread badges and current user
    @app.context_processor
    def inject_global_data():
        current_user = None
        unread_notifications = 0
        if 'user_id' in session:
            current_user = db.session.get(User, session['user_id'])
            if current_user:
                unread_notifications = get_unread_count(current_user.id)
        return {
            'current_user': current_user,
            'unread_notifications_count': unread_notifications,
            'now': datetime.now(timezone.utc)
        }

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('500.html'), 500

    return app


def seed_sample_data(app):
    """
    Populates realistic Indian rural healthcare demonstration data.
    """
    with app.app_context():
        db.create_all()

        # Check if already seeded
        if User.query.first():
            return

        print("Seeding AASHA rural healthcare sample dataset...")

        # 1. Create Doctors
        doc1_user = User(
            email='dr.sharma@phc.in',
            full_name='Dr. Rajesh Sharma',
            role='doctor',
            phone='+91 94150 12345'
        )
        doc1_user.set_password('aasha123')
        db.session.add(doc1_user)

        doc2_user = User(
            email='dr.priya@chc.in',
            full_name='Dr. Priya Verma',
            role='doctor',
            phone='+91 94150 67890'
        )
        doc2_user.set_password('aasha123')
        db.session.add(doc2_user)
        db.session.flush()

        doc1 = Doctor(
            user_id=doc1_user.id,
            reg_number='MCI-10492-UP',
            specialisation='General Medicine / Public Health Officer',
            hospital_centre='Rupaidiha Primary Health Centre (PHC), Bahraich'
        )
        db.session.add(doc1)

        doc2 = Doctor(
            user_id=doc2_user.id,
            reg_number='MCI-21944-UP',
            specialisation='Obstetrics & Maternal Child Health Specialist',
            hospital_centre='Bhinga Community Health Centre (CHC), Shravasti'
        )
        db.session.add(doc2)
        db.session.flush()

        # 2. Create ASHA Workers
        worker1_user = User(
            email='anita.devi@aasha.in',
            full_name='Anita Devi',
            role='asha_worker',
            phone='+91 98390 11223'
        )
        worker1_user.set_password('aasha123')
        db.session.add(worker1_user)

        worker2_user = User(
            email='sunita.yadav@aasha.in',
            full_name='Sunita Yadav',
            role='asha_worker',
            phone='+91 98390 44556'
        )
        worker2_user.set_password('aasha123')
        db.session.add(worker2_user)
        db.session.flush()

        worker1 = ASHAWorker(
            user_id=worker1_user.id,
            village='Madhopur',
            district='Bahraich',
            state='Uttar Pradesh',
            assigned_doctor_id=doc1.id
        )
        db.session.add(worker1)

        worker2 = ASHAWorker(
            user_id=worker2_user.id,
            village='Shivpur',
            district='Bahraich',
            state='Uttar Pradesh',
            assigned_doctor_id=doc2.id
        )
        db.session.add(worker2)
        db.session.flush()

        # 3. Create Sample Patients
        p1 = Patient(
            patient_id_code='ASH-PAT-0001',
            name='Ramesh Kumar',
            age=45,
            gender='Male',
            village='Madhopur',
            phone='+91 98765 43210',
            pregnancy_status='Not Applicable',
            medical_conditions='Hypertension (mild), Smoker',
            asha_worker_id=worker1.id,
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(p1)

        p2 = Patient(
            patient_id_code='ASH-PAT-0002',
            name='Meena Devi',
            age=24,
            gender='Female',
            village='Madhopur',
            phone='+91 98765 88990',
            pregnancy_status='Pregnant - 3rd Trimester (32 weeks)',
            medical_conditions='First pregnancy, mild anemia reported at last ANC',
            asha_worker_id=worker1.id,
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        db.session.add(p2)

        p3 = Patient(
            patient_id_code='ASH-PAT-0003',
            name='Aarav Singh',
            age=3,
            gender='Male',
            village='Madhopur',
            phone='+91 98765 11223',
            pregnancy_status='Not Applicable',
            medical_conditions='Full immunization up to age 2 completed',
            asha_worker_id=worker1.id,
            created_at=datetime.utcnow() - timedelta(days=1, hours=4)
        )
        db.session.add(p3)

        p4 = Patient(
            patient_id_code='ASH-PAT-0004',
            name='Savitri Bai',
            age=58,
            gender='Female',
            village='Shivpur',
            phone='+91 98765 99001',
            pregnancy_status='Not Applicable',
            medical_conditions='Osteoarthritis in knees',
            asha_worker_id=worker2.id,
            created_at=datetime.utcnow() - timedelta(days=3)
        )
        db.session.add(p4)
        db.session.flush()

        # 4. Create Sample Reports, Transcriptions, AI Summaries, and Doctor Guidance
        # Case 1: Ramesh Kumar (Urgent: High Fever + Breathlessness)
        rep1 = PatientReport(
            patient_id=p1.id,
            asha_worker_id=worker1.id,
            doctor_id=doc1.id,
            priority='Urgent',
            case_status='Guidance Sent',
            created_at=datetime.utcnow() - timedelta(hours=6)
        )
        db.session.add(rep1)
        db.session.flush()

        t1 = VoiceTranscription(
            report_id=rep1.id,
            raw_transcript="Patient has high fever since yesterday, is very weak, and is having difficulty breathing.",
            edited_transcript="Patient has high fever since yesterday, is very weak, and is having difficulty breathing.",
            language="en-IN",
            created_at=rep1.created_at
        )
        db.session.add(t1)

        s1 = AISummary(
            report_id=rep1.id,
            symptoms_json=json.dumps(['High Fever', 'Breathing Difficulty', 'Severe Weakness / Fatigue']),
            duration='Since yesterday',
            observations='Patient visibly distressed; increased respiratory effort noted; unable to stand without support',
            pregnancy_notes='Not applicable',
            medicines_mentioned='None mentioned in voice recording',
            other_information='Pre-existing hypertension noted in patient chart',
            structured_summary="Patient Summary:\n• High Fever: Reported (Since yesterday)\n• Breathing Difficulty: Reported (Severe respiratory effort)\n• Severe Weakness: Reported",
            triage_rationale="Identified red flag: 'difficulty breathing' indicates severe respiratory distress. High fever combined with shortness of breath warrants immediate medical triage.",
            warning_signs_json=json.dumps([
                "[Respiratory Distress] Severe respiratory distress or breathlessness detected",
                "[Severe Febrile Illness] High-grade fever with systemic warning signs"
            ]),
            created_at=rep1.created_at
        )
        db.session.add(s1)

        resp1 = DoctorResponse(
            report_id=rep1.id,
            doctor_id=doc1.id,
            guidance_text="Urgent case: Keep patient in upright 45-degree propped position. Administer oral Paracetamol 500mg if temperature >101F. Call 108 ambulance immediately for direct transfer to Rupaidiha PHC for pulse oximetry, oxygen support and chest examination.",
            action_recommended="Emergency 108 Ambulance Referral to PHC Rupaidiha",
            status_updated_to="Guidance Sent",
            created_at=datetime.utcnow() - timedelta(hours=4)
        )
        db.session.add(resp1)

        # Case 2: Meena Devi (Urgent Maternal Case: Severe Abdominal Pain & Swollen Feet)
        rep2 = PatientReport(
            patient_id=p2.id,
            asha_worker_id=worker1.id,
            doctor_id=doc1.id,
            priority='Urgent',
            case_status='Pending Review',
            created_at=datetime.utcnow() - timedelta(minutes=45)
        )
        db.session.add(rep2)
        db.session.flush()

        t2 = VoiceTranscription(
            report_id=rep2.id,
            raw_transcript="Marij 32 hafte ki garbhvati mahila hai. Subah se tez pet dard ho raha hai, sar dard hai aur dono pairo me bahut sujan hai. BP badha hua lag raha hai.",
            edited_transcript="Marij 32 hafte ki garbhvati mahila hai. Subah se tez pet dard ho raha hai, sar dard hai aur dono pairo me bahut sujan hai. BP badha hua lag raha hai.",
            language="hi-IN",
            created_at=rep2.created_at
        )
        db.session.add(t2)

        s2 = AISummary(
            report_id=rep2.id,
            symptoms_json=json.dumps(['Abdominal Pain', 'Headache', 'Swelling (Edema)']),
            duration='Since morning / Today',
            observations='Pregnant woman in third trimester with bilateral pedal edema and acute cephalalgia',
            pregnancy_notes='Patient is 32 weeks pregnant (Third Trimester)',
            medicines_mentioned='None reported',
            other_information='Blood pressure concern noted by ASHA worker',
            structured_summary="Patient Summary:\n• Abdominal Pain: Reported (Severe, since morning)\n• Headache: Reported\n• Swelling (Edema): Reported in both feet\n• Obstetric Context: 32 weeks pregnant (Third Trimester)",
            triage_rationale="Identified red flag: 'swollen feet with headache' and 'severe abdominal pain' in 32-week pregnancy indicate high pre-eclampsia danger signs.",
            warning_signs_json=json.dumps([
                "[Maternal Red Flag] High-risk obstetric danger sign (severe pain, pedal edema, headache)",
                "[Obstetric Alert] Potential pre-eclampsia / hypertensive disorder of pregnancy"
            ]),
            created_at=rep2.created_at
        )
        db.session.add(s2)

        # Case 3: Aarav Singh (Moderate: Pediatric Diarrhea)
        rep3 = PatientReport(
            patient_id=p3.id,
            asha_worker_id=worker1.id,
            doctor_id=doc1.id,
            priority='Moderate',
            case_status='Guidance Sent',
            created_at=datetime.utcnow() - timedelta(hours=18)
        )
        db.session.add(rep3)
        db.session.flush()

        t3 = VoiceTranscription(
            report_id=rep3.id,
            raw_transcript="Child is 3 years old, having watery diarrhea for 2 days. Mild fever, but child is alert and drinking water. No blood in stool.",
            edited_transcript="Child is 3 years old, having watery diarrhea for 2 days. Mild fever, but child is alert and drinking water. No blood in stool.",
            language="en-IN",
            created_at=rep3.created_at
        )
        db.session.add(t3)

        s3 = AISummary(
            report_id=rep3.id,
            symptoms_json=json.dumps(['Diarrhea / Loose Stool', 'Fever']),
            duration='2 day(s)',
            observations='Child is conscious, alert, able to drink liquids; no severe dehydration signs currently',
            pregnancy_notes='Not applicable',
            medicines_mentioned='None mentioned in voice recording',
            other_information='No blood in stool reported',
            structured_summary="Patient Summary:\n• Diarrhea: Reported (Watery, 2 days)\n• Fever: Reported (Mild)\n• Observations: Child alert, drinking fluids, no blood in stool",
            triage_rationale="Detected symptom: 'diarrhea' warrants timely medical assessment. Child is currently alert and drinking fluids (Moderate risk, not in severe shock).",
            warning_signs_json=json.dumps([
                "[Gastrointestinal] Gastrointestinal upset with risk of dehydration",
                "[Febrile Episode] Fever without immediately life-threatening signs"
            ]),
            created_at=rep3.created_at
        )
        db.session.add(s3)

        resp3 = DoctorResponse(
            report_id=rep3.id,
            doctor_id=doc1.id,
            guidance_text="Start oral rehydration salts (ORS) immediately: 1 packet in 1 liter clean drinking water. Give 50-100ml after every loose stool. Provide Zinc 20mg dispersible tablet once daily for 14 continuous days. Advise mother to continue home feeding. If vomiting everything or sunken eyes appear, bring to PHC immediately.",
            action_recommended="Administer ORS + Zinc 20mg for 14 days, monitor hydration",
            status_updated_to="Guidance Sent",
            created_at=datetime.utcnow() - timedelta(hours=16)
        )
        db.session.add(resp3)

        # 5. Create Realistic Notifications
        # Doctor 1 notification: Urgent alert for Meena Devi
        notif_doc1 = Notification(
            recipient_user_id=doc1_user.id,
            sender_user_id=worker1_user.id,
            report_id=rep2.id,
            title="CRITICAL ALERT: Urgent Case from Anita Devi",
            message=f"ASHA Worker Anita Devi (Madhopur) submitted an URGENT report for patient Meena Devi (ASH-PAT-0002). Pre-eclampsia danger signs flagged.",
            notification_type="urgent_alert",
            is_read=False,
            created_at=datetime.utcnow() - timedelta(minutes=45)
        )
        db.session.add(notif_doc1)

        # Worker 1 notification: Doctor guidance received for Ramesh Kumar
        notif_w1 = Notification(
            recipient_user_id=worker1_user.id,
            sender_user_id=doc1_user.id,
            report_id=rep1.id,
            title="Doctor Guidance Received: Ramesh Kumar",
            message="Dr. Rajesh Sharma has provided clinical guidance for patient Ramesh Kumar (ASH-PAT-0001). Action: 'Emergency 108 Ambulance Referral to PHC Rupaidiha'.",
            notification_type="doctor_guidance",
            is_read=False,
            created_at=datetime.utcnow() - timedelta(hours=4)
        )
        db.session.add(notif_w1)

        db.session.commit()
        print("Sample data successfully initialized! Ready for testing.")


app = create_app()

# Initialize tables and seed sample data
with app.app_context():
    seed_sample_data(app)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
