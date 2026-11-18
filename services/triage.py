"""
Smart Triage System for AASHA
Rule-based clinical warning system adhering to Indian National Health Mission (NHM)
and Integrated Management of Neonatal & Childhood Illness (IMNCI) guidelines.

SAFETY PRINCIPLE:
AI does NOT diagnose diseases or prescribe medication.
It assists healthcare workers with immediate clinical prioritization and documentation.
"""

import re
from typing import Dict, Any, List

# Configured Warning Signs & Red Flags for Rural Field Healthcare
CRITICAL_WARNING_RULES = [
    # 1. Respiratory Emergencies
    {
        'id': 'RESP_SEVERE',
        'category': 'Respiratory Distress',
        'keywords': [
            'difficulty breathing', 'shortness of breath', 'saans lene me takleef',
            'saans fulna', 'breathless', 'gasping', 'choking', 'stridor', 
            'severe breathing difficulty', 'chest retractions', 'wheezing severe',
            'oxygen low', 'blue lips', 'cyanosis'
        ],
        'priority': 'Urgent',
        'warning_text': 'Severe respiratory distress or breathlessness detected',
        'action': 'Immediate doctor attention and emergency referral to nearest CHC/Hospital with oxygen support.'
    },
    # 2. Maternal / Obstetric Emergencies (High Risk Pregnancy)
    {
        'id': 'OBSTETRIC_DANGER',
        'category': 'Maternal Red Flag',
        'keywords': [
            'pregnant', 'pregnancy', 'garbhvati', 'trimester', 'bleeding in pregnancy',
            'heavy bleeding', 'vaginal bleeding', 'severe abdominal pain', 'pait me tez dard',
            'convulsions pregnancy', 'eclampsia', 'blurred vision', 'swollen feet with headache',
            'high blood pressure pregnant', 'bp high pregnant', 'water broken', 'loss of fetal movement',
            'bacha hil nahi raha'
        ],
        'requires_pregnancy_context': True,
        'priority': 'Urgent',
        'warning_text': 'High-risk obstetric danger sign (bleeding, severe pain, or pre-eclampsia signs)',
        'action': 'Emergency 108/102 ambulance referral to First Referral Unit (FRU) / CHC immediately.'
    },
    # 3. Cardiovascular / Chest Pain
    {
        'id': 'CARDIO_CHEST_PAIN',
        'category': 'Cardiovascular Alert',
        'keywords': [
            'chest pain', 'chhati me dard', 'seene me dard', 'radiating pain', 
            'left arm pain', 'profuse sweating', 'crushing pain', 'heart attack',
            'palpitations severe', 'cold clammy skin'
        ],
        'priority': 'Urgent',
        'warning_text': 'Acute chest pain with cardiac warning symptoms',
        'action': 'Immediate medical evaluation by Medical Officer. Keep patient calm, at rest, prepare transfer.'
    },
    # 4. Neurological Emergencies
    {
        'id': 'NEURO_CONVULSIONS',
        'category': 'Neurological Alert',
        'keywords': [
            'convulsions', 'seizures', 'fits', 'daura', 'doure', 'unconscious',
            'behosh', 'unresponsive', 'altered mental state', 'confusion', 
            'stiff neck', 'gardan akdan', 'fainting', 'sudden weakness one side'
        ],
        'priority': 'Urgent',
        'warning_text': 'Convulsions, loss of consciousness, or acute altered mental state',
        'action': 'Protect airway, position on left side, urgently transfer to medical facility.'
    },
    # 5. Severe Pediatric Danger Signs (IMNCI)
    {
        'id': 'PEDIATRIC_DANGER',
        'category': 'Pediatric Danger Sign',
        'keywords': [
            'unable to drink', 'unable to breastfeed', 'doodh nahi pee raha',
            'vomits everything', 'sunken eyes', 'lethargic', 'hypothermia', 'cold skin child',
            'severe diarrhea child', 'dast bacha', 'continuous crying', 'chest indrawing'
        ],
        'priority': 'Urgent',
        'warning_text': 'IMNCI critical danger sign in infant/child (unable to feed, lethargic, or severe dehydration)',
        'action': 'Start ORS if able, urgent referral to Pediatrician / Medical Officer at CHC.'
    },
    # 6. High Fever with Complications
    {
        'id': 'FEVER_HIGH',
        'category': 'Severe Febrile Illness',
        'keywords': [
            'high fever', 'tez bukhar', '103', '104', '105', 'fever with chills severe',
            'shivering uncontrollable', 'fever with rash', 'fever with bleeding', 'delirium fever'
        ],
        'priority': 'Urgent',
        'warning_text': 'High-grade fever with systemic warning signs',
        'action': 'Cold sponging, paracetamol under standing order, fast-track medical officer evaluation.'
    },
    # 7. Severe Dehydration / Hemorrhage
    {
        'id': 'SEVERE_DEHYDRATION_BLEEDING',
        'category': 'Severe Fluid Loss / Trauma',
        'keywords': [
            'heavy bleeding', 'severe bleeding', 'khoon beh raha', 'profuse diarrhea',
            'rice watery stool', 'cholera', 'no urine 24 hours', 'peshab nahi aaya'
        ],
        'priority': 'Urgent',
        'warning_text': 'Severe acute fluid loss or uncontrolled bleeding',
        'action': 'Start IV line / continuous oral rehydration and transfer urgently.'
    }
]

MODERATE_WARNING_RULES = [
    {
        'id': 'PERSISTENT_COUGH',
        'category': 'Respiratory Subacute',
        'keywords': [
            'cough for 2 weeks', 'cough 3 weeks', 'khasi do hafte', 'coughing blood',
            'night sweats', 'weight loss with cough', 'tb symptoms', 'chronic cough'
        ],
        'priority': 'Moderate',
        'warning_text': 'Persistent cough (>2 weeks) or hemoptysis — presumptive TB/chronic respiratory check required',
        'action': 'Arrange sputum testing (Nikshay / TB screening) and doctor consultation.'
    },
    {
        'id': 'MODERATE_FEVER',
        'category': 'Febrile Episode',
        'keywords': [
            'fever', 'bukhar', 'tap', 'pyrexia', 'body heat', 'mild fever', 'fever since yesterday',
            'fever 2 days', 'kal se bukhar', 'halka bukhar'
        ],
        'priority': 'Moderate',
        'warning_text': 'Fever without immediately life-threatening signs',
        'action': 'Test for malaria/dengue as per local protocol, hydration, paracetamol under protocol.'
    },
    {
        'id': 'GI_MODERATE',
        'category': 'Gastrointestinal',
        'keywords': [
            'diarrhea', 'dast', 'loose motion', 'vomiting', 'ulti', 'pet kharab',
            'abdominal pain', 'pet dard', 'mild dehydration', 'loss of appetite'
        ],
        'priority': 'Moderate',
        'warning_text': 'Gastrointestinal upset with risk of dehydration',
        'action': 'Provide ORS packets + Zinc (for children), advise frequent small sips, doctor review within 24 hours.'
    },
    {
        'id': 'HYPERTENSION_DM_ROUTINE',
        'category': 'Chronic Disease Flare',
        'keywords': [
            'blood pressure', 'bp high', 'diabetes', 'sugar high', 'sugar low',
            'chakkar', 'dizziness', 'joint pain severe', 'swelling feet'
        ],
        'priority': 'Moderate',
        'warning_text': 'Chronic condition symptom report (Hypertension / Diabetes / Geriatric)',
        'action': 'Review BP and blood sugar readings with Medical Officer during regular clinic hours.'
    }
]


def assess_triage(
    text: str, 
    patient_age: int = None, 
    pregnancy_status: str = None, 
    existing_conditions: str = None
) -> Dict[str, Any]:
    """
    Evaluates patient notes/voice transcription against clinical rule base.
    Returns:
      - priority: 'Urgent', 'Moderate', or 'Routine'
      - rationale: Human-readable clinical justification
      - warning_signs: List of detected warning flags
      - recommended_action: Suggested workflow action for ASHA worker and Doctor
    """
    normalized_text = (text or '').lower()
    conditions_text = (existing_conditions or '').lower()
    preg_context = (pregnancy_status or '').lower()
    is_pregnant = ('pregnant' in preg_context) or ('trimester' in preg_context) or ('garbhvati' in normalized_text)

    detected_warnings: List[str] = []
    highest_priority = 'Routine'
    rationale_points: List[str] = []
    actions: List[str] = []

    # 1. Evaluate Critical Urgent Rules
    for rule in CRITICAL_WARNING_RULES:
        # If rule requires pregnancy context, check if patient is pregnant or text mentions pregnancy
        if rule.get('requires_pregnancy_context') and not is_pregnant:
            # Check if pregnancy is specifically mentioned in text
            if not any(k in normalized_text for k in ['pregnant', 'garbhvati', 'trimester', 'delivery']):
                continue

        for keyword in rule['keywords']:
            # Use word boundary or substring match
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, normalized_text) or (keyword in normalized_text):
                warning_desc = f"[{rule['category']}] {rule['warning_text']}"
                if warning_desc not in detected_warnings:
                    detected_warnings.append(warning_desc)
                    rationale_points.append(f"Identified red flag: '{keyword}' indicates {rule['category'].lower()}.")
                    actions.append(rule['action'])
                highest_priority = 'Urgent'
                break

    # 2. Evaluate Moderate Rules (if not already Urgent)
    if highest_priority != 'Urgent':
        for rule in MODERATE_WARNING_RULES:
            for keyword in rule['keywords']:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, normalized_text) or (keyword in normalized_text):
                    warning_desc = f"[{rule['category']}] {rule['warning_text']}"
                    if warning_desc not in detected_warnings:
                        detected_warnings.append(warning_desc)
                        rationale_points.append(f"Detected symptom: '{keyword}' warrants timely medical assessment.")
                        actions.append(rule['action'])
                    highest_priority = 'Moderate'
                    break

    # Age specific checks: infants under 1 year with any illness
    if patient_age is not None and patient_age <= 1 and highest_priority == 'Routine' and len(normalized_text) > 10:
        highest_priority = 'Moderate'
        detected_warnings.append("[Pediatric Alert] Infant under 12 months requires close monitoring")
        rationale_points.append("Age vulnerability: Infants under 1 year can deteriorate rapidly.")
        actions.append("Timely medical evaluation by Primary Health Centre doctor.")

    # High risk existing condition check
    if 'hypertension' in conditions_text and is_pregnant and highest_priority != 'Urgent':
        highest_priority = 'Urgent'
        detected_warnings.append("[Obstetric Alert] Known hypertension in pregnancy — high pre-eclampsia risk")
        rationale_points.append("Pregnancy with underlying hypertension requires immediate physician review.")
        actions.append("Emergency assessment of blood pressure and urine protein by Doctor.")

    # Default routine rationale
    if highest_priority == 'Routine':
        rationale_points.append("No acute clinical danger signs or critical red flags detected in worker's voice note.")
        actions.append("Proceed with routine field care, patient education, and scheduled follow-up.")

    # Priority badge details
    priority_labels = {
        'Urgent': 'Urgent – Immediate medical review recommended',
        'Moderate': 'Moderate – Timely medical review recommended',
        'Routine': 'Routine – Normal review'
    }

    return {
        'priority': highest_priority,
        'priority_display': priority_labels[highest_priority],
        'warning_signs': detected_warnings,
        'rationale': " ".join(rationale_points),
        'recommended_action': " | ".join(actions) if actions else "Routine follow-up.",
        'disclaimer': (
            "NOTICE: AASHA is an AI-assisted documentation and prioritization tool. "
            "It does NOT replace professional medical diagnosis or clinical judgment. "
            "In case of critical emergencies, initiate standard emergency protocols without delay."
        )
    }
