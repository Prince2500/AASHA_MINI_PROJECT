from datetime import datetime
import json
from models import db

class PatientReport(db.Model):
    __tablename__ = 'patient_reports'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    asha_worker_id = db.Column(db.Integer, db.ForeignKey('asha_workers.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False)
    
    # Priority: 'Urgent', 'Moderate', 'Routine'
    priority = db.Column(db.String(20), nullable=False, default='Routine', index=True)
    
    # Status: 'Pending Review', 'Guidance Sent', 'Action Taken', 'Resolved'
    case_status = db.Column(db.String(30), nullable=False, default='Pending Review', index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transcription = db.relationship('VoiceTranscription', backref='report', uselist=False, cascade='all, delete-orphan')
    ai_summary = db.relationship('AISummary', backref='report', uselist=False, cascade='all, delete-orphan')
    responses = db.relationship('DoctorResponse', backref='report', lazy='dynamic', cascade='all, delete-orphan', order_by='desc(DoctorResponse.created_at)')
    notifications = db.relationship('Notification', backref='report', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def latest_response(self):
        return self.responses.first()

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.name if self.patient else 'Unknown',
            'patient_code': self.patient.patient_id_code if self.patient else 'N/A',
            'patient_age': self.patient.age if self.patient else None,
            'patient_gender': self.patient.gender if self.patient else None,
            'village': self.patient.village if self.patient else 'N/A',
            'asha_worker_name': self.asha_worker.user.full_name if self.asha_worker and self.asha_worker.user else 'Unknown',
            'doctor_name': self.doctor.user.full_name if self.doctor and self.doctor.user else 'Unknown',
            'priority': self.priority,
            'case_status': self.case_status,
            'created_at': self.created_at.strftime('%d-%b-%Y %I:%M %p'),
            'updated_at': self.updated_at.strftime('%d-%b-%Y %I:%M %p') if self.updated_at else ''
        }

    def __repr__(self):
        return f"<PatientReport #{self.id} [{self.priority}] - {self.case_status}>"


class VoiceTranscription(db.Model):
    __tablename__ = 'voice_transcriptions'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('patient_reports.id', ondelete='CASCADE'), nullable=False, unique=True)
    audio_filename = db.Column(db.String(255), nullable=True)
    audio_path = db.Column(db.String(255), nullable=True)
    raw_transcript = db.Column(db.Text, nullable=False)
    edited_transcript = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), default='hi-IN')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<VoiceTranscription for Report #{self.report_id}>"


class AISummary(db.Model):
    __tablename__ = 'ai_summaries'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('patient_reports.id', ondelete='CASCADE'), nullable=False, unique=True)
    symptoms_json = db.Column(db.Text, default='[]')
    duration = db.Column(db.String(100), nullable=True)
    observations = db.Column(db.Text, nullable=True)
    pregnancy_notes = db.Column(db.Text, nullable=True)
    medicines_mentioned = db.Column(db.Text, nullable=True)
    other_information = db.Column(db.Text, nullable=True)
    structured_summary = db.Column(db.Text, nullable=False)
    triage_rationale = db.Column(db.Text, nullable=True)
    warning_signs_json = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def symptoms_list(self):
        try:
            return json.loads(self.symptoms_json) if self.symptoms_json else []
        except:
            return []

    @property
    def warning_signs_list(self):
        try:
            return json.loads(self.warning_signs_json) if self.warning_signs_json else []
        except:
            return []

    def __repr__(self):
        return f"<AISummary for Report #{self.report_id}>"


class DoctorResponse(db.Model):
    __tablename__ = 'doctor_responses'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('patient_reports.id', ondelete='CASCADE'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='CASCADE'), nullable=False)
    guidance_text = db.Column(db.Text, nullable=False)
    action_recommended = db.Column(db.String(255), nullable=True)
    status_updated_to = db.Column(db.String(50), nullable=False, default='Guidance Sent')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'doctor_name': self.doctor.user.full_name if self.doctor and self.doctor.user else 'Doctor',
            'guidance_text': self.guidance_text,
            'action_recommended': self.action_recommended or 'Medical Guidance Provided',
            'status_updated_to': self.status_updated_to,
            'created_at': self.created_at.strftime('%d-%b-%Y %I:%M %p')
        }

    def __repr__(self):
        return f"<DoctorResponse #{self.id} for Report #{self.report_id}>"


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    report_id = db.Column(db.Integer, db.ForeignKey('patient_reports.id', ondelete='CASCADE'), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info')  # 'urgent_alert', 'new_report', 'doctor_guidance', 'status_update'
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'report_id': self.report_id,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%d-%b-%Y %I:%M %p')
        }

    def __repr__(self):
        return f"<Notification #{self.id} to User #{self.recipient_user_id} - Read: {self.is_read}>"
