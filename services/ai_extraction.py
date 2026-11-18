"""
AI Clinical Information Extraction Service for AASHA
Parses unstructured natural voice notes (Hindi, Hinglish, English) into
accurate, structured clinical documentation.

Extracts:
1. Symptoms & Severity
2. Duration of symptoms
3. Patient Observations (vitals, appearance, mobility)
4. Pregnancy status (if mentioned)
5. Current/reported Medicines (if mentioned)
6. Other medical facts
7. Clean structured bullet-point summary
"""

import os
import re
import json
import logging
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Common clinical symptom keywords in English, Hindi, and transliterated Hinglish
SYMPTOM_DICTIONARY = [
    {
        'canonical': 'High Fever',
        'patterns': [
            r'high fever', r'tez bukhar', r'bahut tez bukhar', r'heavy fever', 
            r'10[0-5]\s*degrees?', r'10[0-5]\s*f', r'severe fever'
        ]
    },
    {
        'canonical': 'Fever',
        'patterns': [
            r'fever', r'bukhar', r'tap', r'pyrexia', r'garam sharir', r'temperature'
        ]
    },
    {
        'canonical': 'Breathing Difficulty',
        'patterns': [
            r'difficulty breathing', r'shortness of breath', r'saans lene me takleef',
            r'saans ful rahi', r'saans me taklif', r'breathless', r'gasping', 
            r'dam ghutna', r'dyspnea', r'choking'
        ]
    },
    {
        'canonical': 'Severe Weakness / Fatigue',
        'patterns': [
            r'very weak', r'extreme weakness', r'bahut kamzori', r'kamzor', 
            r'lethargic', r'exhaustion', r'uth nahi pa raha', r'unable to stand',
            r'chakkar aana', r'dizziness', r'faintness'
        ]
    },
    {
        'canonical': 'Chest Pain',
        'patterns': [
            r'chest pain', r'chhati me dard', r'seene me dard', r'heart pain',
            r'pressure in chest', r'left arm pain'
        ]
    },
    {
        'canonical': 'Abdominal Pain',
        'patterns': [
            r'abdominal pain', r'stomach ache', r'pet dard', r'pait me dard',
            r'lower abdomen pain', r'cramping'
        ]
    },
    {
        'canonical': 'Vomiting',
        'patterns': [
            r'vomit\w*', r'ulti\w*', r'nausea', r'ji machlana', r'qai'
        ]
    },
    {
        'canonical': 'Diarrhea / Loose Stool',
        'patterns': [
            r'diarrhea', r'loose motion', r'dast', r'watery stool', r'pet kharab'
        ]
    },
    {
        'canonical': 'Cough',
        'patterns': [
            r'cough', r'khansi', r'khasi', r'phlegm', r'balgam', r'dry cough'
        ]
    },
    {
        'canonical': 'Headache',
        'patterns': [
            r'headache', r'sar dard', r'sar me dard', r'migraine', r'heavy head'
        ]
    },
    {
        'canonical': 'Swelling (Edema)',
        'patterns': [
            r'swelling', r'swollen feet', r'pair me sujan', r'sujan', r'edema', r'puffy face'
        ]
    },
    {
        'canonical': 'Vaginal Bleeding / Hemorrhage',
        'patterns': [
            r'bleeding', r'khoon aana', r'vaginal bleeding', r'heavy bleeding', r'spotting'
        ]
    },
    {
        'canonical': 'Convulsions / Fits',
        'patterns': [
            r'convulsions?', r'seizures?', r'fits', r'daura', r'mirgi', r'twitching'
        ]
    },
    {
        'canonical': 'Chills / Shivering',
        'patterns': [
            r'chills', r'shivering', r'kapkapi', r'thand lagna'
        ]
    },
    {
        'canonical': 'Loss of Appetite',
        'patterns': [
            r'loss of appetite', r'bhookh nahi lagna', r'not eating', r'khana nahi kha raha'
        ]
    }
]

# Duration patterns
DURATION_PATTERNS = [
    (r'(since\s+yesterday|kal\s+se)', 'Since yesterday'),
    (r'(today|aaj\s+se|since\s+morning|subah\s+se)', 'Since morning / Today'),
    (r'(\d+)\s*(days?|din|dino)\s*(se|ago|since)?', lambda m: f"{m.group(1)} day(s)"),
    (r'(\d+)\s*(weeks?|hafte|hafto)\s*(se|ago|since)?', lambda m: f"{m.group(1)} week(s)"),
    (r'(\d+)\s*(months?|mahine)\s*(se|ago|since)?', lambda m: f"{m.group(1)} month(s)"),
    (r'(last\s+night|raat\s+se)', 'Since last night'),
    (r'(for\s+a\s+few\s+days|kuchh\s+dino\s+se)', 'For a few days'),
]

# Medicine patterns
MEDICINE_PATTERNS = [
    r'paracetamol', r'pcm', r'ors', r'zinc', r'iron\s*tablet', r'folic\s*acid',
    r'amoxicillin', r'azithromycin', r'cetirizine', r'cough\s*syrup', r'insulin',
    r'bp\s*tablet', r'sugar\s*tablet', r'inhaler', r'dawa', r'goli', r'antibiotic'
]

# Pregnancy mentions
PREGNANCY_PATTERNS = [
    r'pregnant', r'pregnancy', r'garbhvati', r'trimester', r'(\d+)\s*weeks?\s*pregnant',
    r'(\d+)\s*months?\s*pregnant', r'(\d+)\s*mahine\s*ka\s*garbh', r'delivery\s*due'
]


def extract_with_rules(transcript: str, patient_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Deterministic rule-based clinical entity extractor for Hindi, Hinglish, and English text.
    Strictly extracts ONLY explicitly stated information without inventing data.
    """
    text = transcript.strip()
    lower_text = text.lower()
    
    # 1. Extract Symptoms
    extracted_symptoms = []
    # Check for High Fever first so normal fever doesn't duplicate if already categorized as high fever
    high_fever_matched = False
    
    for item in SYMPTOM_DICTIONARY:
        name = item['canonical']
        if high_fever_matched and name == 'Fever':
            continue
            
        for pat in item['patterns']:
            if re.search(pat, lower_text):
                extracted_symptoms.append(name)
                if name == 'High Fever':
                    high_fever_matched = True
                break

    # 2. Extract Duration
    detected_duration = "Not explicitly stated"
    for pat, formatter in DURATION_PATTERNS:
        match = re.search(pat, lower_text)
        if match:
            if callable(formatter):
                detected_duration = formatter(match)
            else:
                detected_duration = formatter
            break

    # 3. Extract Observations
    observations = []
    if 'weak' in lower_text or 'kamzor' in lower_text:
        observations.append("Patient appears physically weak / fatigued")
    if 'unable to walk' in lower_text or 'chal nahi' in lower_text or 'uth nahi' in lower_text:
        observations.append("Impaired mobility / unable to stand")
    if 'sweat' in lower_text or 'paseena' in lower_text:
        observations.append("Profuse perspiration noted")
    if 'breath' in lower_text or 'saans' in lower_text:
        observations.append("Respiratory effort visibly increased")
    if 'crying' in lower_text or 'ro raha' in lower_text:
        observations.append("Patient irritable / in distress")
    if not observations:
        observations.append("General vitals to be checked on physical review")

    # 4. Pregnancy Mention
    pregnancy_notes = None
    for pat in PREGNANCY_PATTERNS:
        m = re.search(pat, lower_text)
        if m:
            pregnancy_notes = f"Pregnancy context mentioned in voice note: '{m.group(0)}'"
            break
    if not pregnancy_notes and patient_info and patient_info.get('pregnancy_status') not in ['Not Pregnant', None, '']:
        pregnancy_notes = f"Patient profile indicates: {patient_info.get('pregnancy_status')}"

    # 5. Medicines Mentioned
    medicines = []
    for med in MEDICINE_PATTERNS:
        m = re.search(r'\b' + med + r'\b', lower_text)
        if m:
            medicines.append(m.group(0).title())
    medicines_str = ", ".join(list(set(medicines))) if medicines else "None mentioned in voice recording"

    # 6. Other relevant info
    other_info = []
    if 'sugar' in lower_text or 'diabetes' in lower_text:
        other_info.append("Blood sugar/diabetes context noted")
    if 'bp' in lower_text or 'blood pressure' in lower_text:
        other_info.append("Blood pressure concern noted")
    if patient_info and patient_info.get('medical_conditions'):
        other_info.append(f"Pre-existing conditions: {patient_info.get('medical_conditions')}")

    # Build Structured Patient Summary matching standard clinical summary format
    summary_lines = ["Patient Summary:"]
    if extracted_symptoms:
        for s in extracted_symptoms:
            summary_lines.append(f"• {s}: Reported")
    else:
        summary_lines.append("• Symptoms: General health check / unspecific complaints recorded")

    if detected_duration != "Not explicitly stated":
        summary_lines.append(f"• Duration: {detected_duration}")

    if observations:
        summary_lines.append(f"• Observations: {'; '.join(observations)}")

    if pregnancy_notes:
        summary_lines.append(f"• Obstetric Context: {pregnancy_notes}")

    if medicines and medicines_str != "None mentioned in voice recording":
        summary_lines.append(f"• Medicines Taken: {medicines_str}")

    return {
        'symptoms': extracted_symptoms,
        'duration': detected_duration,
        'observations': "; ".join(observations),
        'pregnancy_notes': pregnancy_notes or "Not applicable / Not mentioned",
        'medicines_mentioned': medicines_str,
        'other_information': "; ".join(other_info) if other_info else "None",
        'structured_summary': "\n".join(summary_lines),
        'engine': 'AASHA Rural Clinical NLP (Rule-Based & Multilingual)'
    }


def extract_with_gemini(transcript: str, patient_info: Dict[str, Any] = None, api_key: str = None) -> Dict[str, Any]:
    """
    Calls Google Gemini API for clinical information extraction if an API key is available.
    Falls back gracefully to rule-based extraction upon any network or API issue.
    """
    key = api_key or os.environ.get('GEMINI_API_KEY', '')
    if not key:
        return extract_with_rules(transcript, patient_info)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""You are AASHA, an AI Clinical Assistant assisting rural healthcare workers (ASHA workers) in India.
Your task is to extract medical information from the worker's voice note transcript.

TRANSCRIPT:
"{transcript}"

PATIENT CONTEXT:
Name: {patient_info.get('name', 'N/A') if patient_info else 'N/A'}
Age: {patient_info.get('age', 'N/A') if patient_info else 'N/A'}
Gender: {patient_info.get('gender', 'N/A') if patient_info else 'N/A'}
Pregnancy Status: {patient_info.get('pregnancy_status', 'N/A') if patient_info else 'N/A'}
Existing Medical Conditions: {patient_info.get('medical_conditions', 'N/A') if patient_info else 'N/A'}

STRICT CLINICAL RULES:
1. Extract ONLY facts explicitly stated in the transcript. NEVER INVENT OR ASSUME UNMENTIONED MEDICAL CONDITIONS.
2. DO NOT DIAGNOSE OR PRESCRIBE MEDICATION.
3. Return a valid JSON object strictly matching this schema:
{{
  "symptoms": ["List of explicitly reported symptoms"],
  "duration": "Duration of symptoms or 'Not explicitly stated'",
  "observations": "Clinical observations of patient state",
  "pregnancy_notes": "Pregnancy details if mentioned or relevant",
  "medicines_mentioned": "Any medicines mentioned or 'None reported'",
  "other_information": "Any other relevant history",
  "structured_summary": "Clean bullet-pointed Patient Summary:\\n• Fever: Reported\\n• Weakness: Reported"
}}
Return ONLY the raw JSON object, no markdown fences or other text.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            raw_text = result['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(raw_text)
            data['engine'] = 'Google Gemini 1.5 Flash'
            return data
        else:
            logger.warning(f"Gemini API returned status {response.status_code}. Using local NLP extractor.")
    except Exception as e:
        logger.warning(f"Gemini API call failed: {e}. Falling back to rule-based NLP extractor.")

    return extract_with_rules(transcript, patient_info)


def process_clinical_note(transcript: str, patient_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main extraction interface. Tries LLM if configured, else uses comprehensive rural clinical NLP.
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if api_key:
        return extract_with_gemini(transcript, patient_info, api_key)
    return extract_with_rules(transcript, patient_info)
