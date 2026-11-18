from datetime import datetime
from models import db

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    patient_id_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)  # 'Female', 'Male', 'Other'
    village = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    pregnancy_status = db.Column(db.String(50), default='Not Pregnant')
    medical_conditions = db.Column(db.Text, nullable=True)  # Existing conditions (e.g., Hypertension, Diabetes)
    
    asha_worker_id = db.Column(db.Integer, db.ForeignKey('asha_workers.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reports = db.relationship('PatientReport', backref='patient', lazy='dynamic', cascade='all, delete-orphan', order_by='desc(PatientReport.created_at)')

    @classmethod
    def generate_patient_code(cls):
        count = cls.query.count() + 1
        return f"ASH-PAT-{count:04d}"

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id_code': self.patient_id_code,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'village': self.village,
            'phone': self.phone or 'N/A',
            'pregnancy_status': self.pregnancy_status,
            'medical_conditions': self.medical_conditions or 'None reported',
            'created_at': self.created_at.strftime('%d-%b-%Y %I:%M %p')
        }

    def __repr__(self):
        return f"<Patient {self.patient_id_code} - {self.name}>"
