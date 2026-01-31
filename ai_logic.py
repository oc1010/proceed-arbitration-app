import streamlit as st
from datetime import datetime, date
import vertexai
from vertexai.generative_models import GenerativeModel # UPDATED IMPORT
from google.oauth2 import service_account
from db import load_complex_data, load_full_config

# ==============================================================================
# 1. DETERMINISTIC CALCULATION ENGINE (NO AI HALLUCINATIONS)
# ==============================================================================

def calculate_doc_prod_score(role):
    """Calculates the 'Proportionality Score' strictly via math."""
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    threshold = meta.get('cost_settings', {}).get('doc_prod_threshold', 75.0)
    
    requests = data.get('doc_prod', {}).get(role, [])
    if not requests: return 0.0, False
    
    total = len(requests)
    rejected = sum(1 for r in requests if r.get('status') == 'Denied')
    
    ratio = (rejected / total) * 100 if total > 0 else 0.0
    penalty_triggered = ratio > threshold
    
    return ratio, penalty_triggered

def calculate_delay_penalties(role):
    """Calculates delay deductions based on 'Approved' extension requests."""
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    rate = meta.get('cost_settings', {}).get('delay_penalty_rate', 0.5)
    
    delays_log = data.get('delays', [])
    total_deduction_percent = 0.0
    detailed_log = []

    for d in delays_log:
        if d.get('requestor') == role and d.get('status') == 'Approved':
            days = 7 # Estimated for demo
            penalty = days * rate
            total_deduction_percent += penalty
            detailed_log.append(f"{d['event']} ({days} days @ {rate}%/day)")

    return total_deduction_percent, detailed_log

def calculate_reversal_amount(offerer_role, offer_date_str):
    """Filters and sums costs incurred AFTER the specific cut-off date."""
    data = load_complex_data()
    costs = data.get('costs', {})
    
    rejecting_party = 'respondent' if offerer_role == 'claimant' else 'claimant'
    target_log = costs.get(f"{rejecting_party}_log", [])
    
    cutoff_date = datetime.strptime(offer_date_str, "%Y-%m-%d").date()
    reversal_sum = 0.0
    
    for entry in target_log:
        try:
            entry_date = datetime.strptime(entry['date'], "%Y-%m-%d").date()
            if entry_date > cutoff_date:
                reversal_sum += float(entry['amount'])
        except:
            continue
            
    return reversal_sum, rejecting_party

def calculate_burn_rate(role):
    """Calculates average spend per day."""
    data = load_complex_data()
    costs = data.get('costs', {}).get(f"{role}_log", [])
    
    if not costs: return 0.0
    
    total_spend = sum(float(c['amount']) for c in costs)
    
    dates = []
    for c in costs:
        try:
            dates.append(datetime.strptime(c['date'], "%Y-%m-%d"))
        except: pass
            
    if not dates: return 0.0
    
    duration_days = (max(dates) - min(dates)).days
    if duration_days < 1: duration_days = 1
    
    return total_spend / duration_days

# ==============================================================================
# 2. LOGIC CONTROLLER
# ==============================================================================

def check_sealed_offers(final_award_val):
    """Checks the 'Vault' for any offers higher than the Award."""
    data = load_complex_data()
    offers = data.get('costs', {}).get('sealed_offers', [])
    reversal_triggers = []
    
    for offer in offers:
        try:
            offer_val = float(offer.get('amount', 0.0))
            if final_award_val < offer_val:
                reversal_amt, payer = calculate_reversal_amount(offer['offerer'], offer['date'])
                reversal_triggers.append({
                    "offerer": offer['offerer'],
                    "payer": payer,
                    "offer_date": offer['date'],
                    "offer_amount": offer_val,
                    "reversal_sum": reversal_amt
                })
        except: pass
            
    return reversal_triggers

# ==============================================================================
# 3. AI DRAFTING LAYER (GEMINI)
# ==============================================================================

def generate_cost_award_draft(case_id, final_award_val):
    try:
        # A. RUN CALCULATIONS FIRST
        c_score, c_pen = calculate_doc_prod_score('claimant')
        r_score, r_pen = calculate_doc_prod_score('respondent')
        
        c_delay_pct, c_log = calculate_delay_penalties('claimant')
        r_delay_pct, r_log = calculate_delay_penalties('respondent')
        
        c_burn = calculate_burn_rate('claimant')
        r_burn = calculate_burn_rate('respondent')
        
        reversals = check_sealed_offers(final_award_val) if final_award_val else []
        
        # B. CONSTRUCT PROMPT
        prompt = f"""
        You are an International Arbitrator drafting the 'Final Award on Costs' for Case {case_id}.
        
        DATA:
        1. CONDUCT:
        - Claimant: {c_score:.1f}% Doc Rejection. Burn Rate: €{c_burn:,.2f}/day.
        - Respondent: {r_score:.1f}% Doc Rejection. Burn Rate: €{r_burn:,.2f}/day.
        *Rule: Rejection >75% triggers 100% cost penalty.*
        
        2. DELAYS:
        - Claimant: -{c_delay_pct}% deduction. Reason: {c_log}
        - Respondent: -{r_delay_pct}% deduction. Reason: {r_log}
        
        3. SEALED OFFERS:
        {f"- TRIGGERED: {reversals[0]['payer']} pays {reversals[0]['offerer']} post-offer costs of €{reversals[0]['reversal_sum']:,.2f}" if reversals else "- None triggered."}
        
        Draft a formal legal analysis (3 paragraphs) determining the net cost allocation.
        """
        
        # C. GENERATE WITH GEMINI
        if "gcp_service_account" in st.secrets:
            # 1. Auth
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            project_id = st.secrets["gcp_service_account"]["project_id"]
            
            # 2. Init
            vertexai.init(project=project_id, location="us-central1", credentials=creds)
            
            # 3. Model Switch -> Gemini 1.5 Flash (Faster/Newer)
            model = GenerativeModel("gemini-1.5-flash")
            
            # 4. Generate
            response = model.generate_content(prompt)
            return response.text
        else:
            return f"**[Demo Mode]** Vertex AI not connected.\n\nPrompt Context:\n{prompt}"

    except Exception as e:
        return f"Error during AI Generation: {e}"
