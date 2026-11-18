"""
Speech-to-Text & Audio Management Service for AASHA
Handles audio file uploads, transcription processing, and preset field scenarios.
"""

import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'webm', 'm4a', 'aac'}

# Common rural field scenarios for quick demonstration & testing
PRESET_CLINICAL_SCENARIOS = [
    {
        'id': 'scenario_urgent_fever_dyspnea',
        'title': 'High Fever & Breathlessness (Urgent)',
        'language': 'en-IN',
        'transcript': 'Patient has high fever since yesterday, is very weak, and is having difficulty breathing.',
        'patient_context': 'Adult male, 45 years'
    },
    {
        'id': 'scenario_urgent_maternal',
        'title': 'Pregnant with Severe Abdominal Pain & Swelling (Urgent)',
        'language': 'hi-IN',
        'transcript': 'Marij 32 hafte ki garbhvati mahila hai. Subah se tez pet dard ho raha hai, sar dard hai aur dono pairo me bahut sujan hai. BP badha hua lag raha hai.',
        'patient_context': 'Pregnant woman, 24 years, 3rd Trimester'
    },
    {
        'id': 'scenario_urgent_pediatric',
        'title': 'Child with Dehydration & Persistent Vomiting (Urgent)',
        'language': 'en-IN',
        'transcript': 'Child is three years old, having severe watery diarrhea for 2 days. Vomits everything, has sunken eyes, lethargic and unable to drink liquids.',
        'patient_context': 'Child, 3 years'
    },
    {
        'id': 'scenario_moderate_cough',
        'title': 'Persistent Cough > 2 Weeks (Moderate)',
        'language': 'hi-IN',
        'transcript': 'Marij ko pichle do hafte se lagatar khansi hai, sham ko halka bukhar rehta hai aur bhookh kam lag rahi hai. Vajan bhi kam hua hai.',
        'patient_context': 'Adult female, 52 years'
    },
    {
        'id': 'scenario_routine_antenatal',
        'title': 'Routine Antenatal Checkup (Routine)',
        'language': 'en-IN',
        'transcript': 'Regular 5th month routine antenatal checkup. Patient feels fetal movement, taking regular iron and folic acid tablets. No complaints, no swelling.',
        'patient_context': 'Pregnant woman, 22 years, 2nd Trimester'
    }
]


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_audio_file(file, upload_folder: str) -> str:
    """
    Saves uploaded audio file with a safe unique filename and returns its relative path.
    """
    if not file or file.filename == '':
        return None

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder, exist_ok=True)

    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'webm'
    unique_name = f"voice_{uuid.uuid4().hex[:12]}.{extension}"
    file_path = os.path.join(upload_folder, unique_name)
    file.save(file_path)
    return unique_name


def get_preset_scenarios():
    return PRESET_CLINICAL_SCENARIOS
