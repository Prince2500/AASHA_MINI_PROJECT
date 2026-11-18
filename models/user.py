from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'asha_worker' or 'doctor'
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 1-to-1 profiles
    asha_profile = db.relationship('ASHAWorker', backref='user', uselist=False, cascade='all, delete-orphan')
    doctor_profile = db.relationship('Doctor', backref='user', uselist=False, cascade='all, delete-orphan')

    # Notifications
    received_notifications = db.relationship(
        'Notification', 
        foreign_keys='Notification.recipient_user_id', 
        backref='recipient', 
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    sent_notifications = db.relationship(
        'Notification', 
        foreign_keys='Notification.sender_user_id', 
        backref='sender', 
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    reg_number = db.Column(db.String(50), unique=True, nullable=False)  # Medical registration number
    specialisation = db.Column(db.String(100), nullable=False)
    hospital_centre = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assigned_workers = db.relationship('ASHAWorker', backref='assigned_doctor', lazy='dynamic')
    reports = db.relationship('PatientReport', backref='doctor', lazy='dynamic')
    responses = db.relationship('DoctorResponse', backref='doctor', lazy='dynamic')

    def __repr__(self):
        return f"<Doctor {self.reg_number} - {self.specialisation}>"


class ASHAWorker(db.Model):
    __tablename__ = 'asha_workers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    village = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patients = db.relationship('Patient', backref='asha_worker', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('PatientReport', backref='asha_worker', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ASHAWorker {self.village}, {self.district}>"
