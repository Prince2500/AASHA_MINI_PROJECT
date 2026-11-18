"""
Automated End-to-End Workflow Verification Test for AASHA
"""

import sys
import unittest
from app import create_app, seed_sample_data
from models import db
from models.user import User, ASHAWorker, Doctor
from models.patient import Patient
from models.report import PatientReport, Notification

class AASHATestSuite(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            seed_sample_data(self.app)

    def test_01_landing_page(self):
        """Step 1: Landing Page renders properly"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AASHA', response.data)
        self.assertIn(b'Voice for the Worker', response.data)
        print("✓ Step 1: Landing page verified.")

    def test_02_demo_login(self):
        """Step 2: Login for ASHA Worker and Doctor"""
        # Test Worker Demo Login
        res_worker = self.client.get('/demo-login/worker', follow_redirects=True)
        self.assertEqual(res_worker.status_code, 200)
        self.assertIn(b'Anita Devi', res_worker.data)
        self.assertIn(b'ASHA Worker', res_worker.data)

        # Test Doctor Demo Login
        res_doc = self.client.get('/demo-login/doctor', follow_redirects=True)
        self.assertEqual(res_doc.status_code, 200)
        self.assertIn(b'Dr. Rajesh Sharma', res_doc.data)
        self.assertIn(b'Triage Queue', res_doc.data)
        print("✓ Step 2: Role authentication verified.")

    def test_03_patient_registration(self):
        """Step 4: Register a new patient and verify auto-generated ID"""
        # Login as worker
        self.client.get('/demo-login/worker')
        
        post_data = {
            'name': 'Gita Kumari',
            'age': '29',
            'gender': 'Female',
            'village': 'Madhopur',
            'phone': '+91 99887 76655',
            'pregnancy_status': 'Pregnant - 2nd Trimester (13-27 wks)',
            'medical_conditions': 'Mild anemia, routine check'
        }
        res = self.client.post('/patients/register', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Gita Kumari', res.data)
        self.assertIn(b'ASH-PAT-', res.data)
        print("✓ Step 4: Patient registration with auto-generated ID verified.")

    def test_04_ai_extraction_and_triage_preview_api(self):
        """Step 6 & 7: Test real-time AI extraction and smart triage API"""
        self.client.get('/demo-login/worker')

        payload = {
            'transcript': 'Patient has high fever since yesterday, is very weak, and is having difficulty breathing.'
        }
        res = self.client.post('/api/analyze-preview', json=payload)
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()

        self.assertIn('extraction', json_data)
        self.assertIn('triage', json_data)
        self.assertEqual(json_data['triage']['priority'], 'Urgent')
        self.assertTrue(len(json_data['triage']['warning_signs']) > 0)
        print(f"✓ Step 6 & 7: AI extraction & smart triage API verified. Priority: {json_data['triage']['priority']}")

    def test_05_complete_voice_report_to_doctor_guidance_flow(self):
        """Step 5, 8, 9, 10: Complete Worker -> Voice Submit -> Doctor Review -> Worker Guidance"""
        # 1. Login as Worker
        self.client.get('/demo-login/worker')

        # Get first patient ID
        with self.app.app_context():
            patient = Patient.query.first()
            p_id = patient.id
            doc = Doctor.query.first()

        # Submit Voice Report
        form_data = {
            'patient_id': str(p_id),
            'raw_transcript': 'Patient has severe chest pain, left arm radiating pain and cold sweat since morning.',
            'edited_transcript': 'Patient has severe chest pain, left arm radiating pain and cold sweat since morning.',
            'language': 'en-IN'
        }
        submit_res = self.client.post('/reports/submit', data=form_data, follow_redirects=True)
        self.assertEqual(submit_res.status_code, 200)
        self.assertIn(b'Urgent', submit_res.data)

        # 2. Verify Doctor received urgent notification
        with self.app.app_context():
            latest_report = PatientReport.query.order_by(PatientReport.id.desc()).first()
            self.assertEqual(latest_report.priority, 'Urgent')
            self.assertEqual(latest_report.case_status, 'Pending Review')
            
            notif = Notification.query.filter_by(report_id=latest_report.id).first()
            self.assertIsNotNone(notif)
            report_id = latest_report.id

        # 3. Doctor logs in and views dashboard
        self.client.get('/demo-login/doctor')
        dash_res = self.client.get('/doctor/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'Urgent', dash_res.data)

        # 4. Doctor submits clinical guidance
        guidance_data = {
            'guidance_text': 'Emergency acute coronary syndrome protocol: Administer Aspirin 300mg chewable under standing order. Keep patient at absolute rest. Dispatch 108 ambulance for immediate transit to District Hospital.',
            'action_recommended': 'Immediate 108 Cardiac Transport to District Hospital',
            'case_status': 'Guidance Sent'
        }
        guidance_res = self.client.post(f'/doctor/respond/{report_id}', data=guidance_data, follow_redirects=True)
        self.assertEqual(guidance_res.status_code, 200)
        self.assertIn(b'Clinical guidance transmitted', guidance_res.data)

        # 5. Worker logs back in and verifies response received
        self.client.get('/demo-login/worker')
        worker_dash = self.client.get('/worker/dashboard')
        self.assertEqual(worker_dash.status_code, 200)
        self.assertIn(b'Doctor Guidance Inbox', worker_dash.data)
        self.assertIn(b'Immediate 108 Cardiac Transport', worker_dash.data)
        print("✓ Step 8, 9, 10: Complete 1-to-1 doctor connection and bidirectional guidance loop verified!")

    def test_06_patient_history_timeline(self):
        """Step 11: Patient history and consultation timeline"""
        self.client.get('/demo-login/worker')
        with self.app.app_context():
            patient = Patient.query.first()
            p_id = patient.id

        res = self.client.get(f'/patients/{p_id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Clinical Voice Reports & Treatment Timeline', res.data)
        self.assertIn(b'Structured Clinical Extraction', res.data)
        print("✓ Step 11: Patient longitudinal history verified.")

if __name__ == '__main__':
    unittest.main()
