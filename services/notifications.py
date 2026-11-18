"""
Notification Service for AASHA
Manages bidirectional real-time communication between ASHA workers and assigned Doctors.
"""

from models import db
from models.report import Notification

def create_notification(
    recipient_user_id: int,
    sender_user_id: int,
    report_id: int,
    title: str,
    message: str,
    notification_type: str = 'info'
) -> Notification:
    """
    Creates and commits a new notification in the database.
    """
    notif = Notification(
        recipient_user_id=recipient_user_id,
        sender_user_id=sender_user_id,
        report_id=report_id,
        title=title,
        message=message,
        notification_type=notification_type,
        is_read=False
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def notify_doctor_new_report(report) -> Notification:
    """
    Alerts the assigned Doctor when their ASHA worker submits a new patient voice report.
    """
    doctor_user_id = report.doctor.user_id
    worker_user_id = report.asha_worker.user_id
    worker_name = report.asha_worker.user.full_name
    village = report.asha_worker.village
    patient_name = report.patient.name
    priority = report.priority

    if priority == 'Urgent':
        title = f"CRITICAL ALERT: Urgent Case from {worker_name}"
        msg = f"ASHA Worker {worker_name} ({village}) submitted an URGENT report for patient {patient_name} ({report.patient.patient_id_code}). Immediate review required."
        notif_type = 'urgent_alert'
    elif priority == 'Moderate':
        title = f"Moderate Priority Case: {patient_name}"
        msg = f"ASHA Worker {worker_name} submitted a moderate priority report for patient {patient_name}. Timely review requested."
        notif_type = 'new_report'
    else:
        title = f"Routine Report: {patient_name}"
        msg = f"New routine health report submitted by {worker_name} for patient {patient_name}."
        notif_type = 'new_report'

    return create_notification(
        recipient_user_id=doctor_user_id,
        sender_user_id=worker_user_id,
        report_id=report.id,
        title=title,
        message=msg,
        notification_type=notif_type
    )


def notify_worker_doctor_guidance(report, guidance_text: str, action: str) -> Notification:
    """
    Alerts the ASHA Worker when their assigned Doctor responds with clinical guidance.
    """
    doctor_user_id = report.doctor.user_id
    worker_user_id = report.asha_worker.user_id
    doctor_name = report.doctor.user.full_name
    patient_name = report.patient.name

    title = f"Doctor Guidance Received: {patient_name}"
    msg = f"Dr. {doctor_name} has provided clinical guidance for patient {patient_name} ({report.patient.patient_id_code}). Action: '{action}'."

    return create_notification(
        recipient_user_id=worker_user_id,
        sender_user_id=doctor_user_id,
        report_id=report.id,
        title=title,
        message=msg,
        notification_type='doctor_guidance'
    )


def get_user_notifications(user_id: int, limit: int = 20):
    return Notification.query.filter_by(recipient_user_id=user_id).order_by(Notification.created_at.desc()).limit(limit).all()


def get_unread_count(user_id: int) -> int:
    return Notification.query.filter_by(recipient_user_id=user_id, is_read=False).count()
