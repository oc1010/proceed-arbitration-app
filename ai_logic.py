import streamlit as st
from datetime import datetime, date
import vertexai
from vertexai.language_models import TextGenerationModel
from db import load_complex_data, load_full_config

# ==============================================================================
# 1. DETERMINISTIC CALCULATION ENGINE (NO AI HALLUCINATIONS)
# ==============================================================================

def calculate_doc_prod_score(role):
    """
    Calculates the 'Proportionality Score' strictly via math.
    Source: Cost Allocation Tool (AI).docx [cite: 114-118]
    """
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    threshold = meta.get('cost_settings', {}).get('doc_prod_threshold', 75.0)
    
    requests = data.get('doc_prod', {}).get(role, [])
    if not requests: return 0.0, False
    
    total = len(requests)
    rejected = sum(1 for r in requests if r.get('status') == 'Denied')
    
    # Python Math: Impossible to make a calculation error here
    ratio = (rejected / total) * 100
    penalty_triggered = ratio > threshold
    
    return ratio, penalty_triggered

def calculate_delay_penalties(role):
    """
    Calculates delay deductions.
    Source: Cost Allocation Tool (AI).docx [cite: 128-130]
    """
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    rate = meta.get('cost_settings', {}).get('delay_penalty_rate', 0.5) # 0.5% per day
    
    delays_log = data.get('delays', [])
    total_deduction_percent = 0.0
    detailed_log = []

    for d in delays_log:
        # Strict Logic: Only penalize if status is 'Approved' (meaning delay happened) 
        # and requestor is the role in question.
        if d.get('requestor') == role and d.get('status') == 'Approved':
            # In a real app, we would calc exact days. For demo, we estimate 7 days per request 
            # or parse from the 'tribunal_decision' string if it contains "Extended by X days"
            days = 7 
            penalty = days * rate
            total_deduction_percent += penalty
            detailed_log.append(f"{d['event']} ({days} days @ {rate}%/day)")

    return total_deduction_percent, detailed_log

def calculate_reversal_amount(offerer_role, offer_date_str):
    """
    Filters and sums costs incurred AFTER the specific cut-off date.
    Source: Cost Allocation Tool (AI).docx [cite: 155]
    """
    data = load_complex_data()
    costs = data.get('costs', {})
    
    # Identify the "Loser" of the settlement offer (the one who rejected it)
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
    """
    Calculates average spend per month/phase to detect inflation.
    Source: Cost Allocation Tool (AI).docx 
    """
    data = load_complex_data()
    costs = data.get('costs', {}).get(f"{role}_log", [])
    
    if not costs: return 0.0
    
    total_spend = sum(float(c['amount']) for c in costs)
    
    # Find duration
    dates = [datetime.strptime(c['date'], "%Y-%m-%d") for c in costs]
    if not dates: return 0.0
    
    duration_days = (max(dates) - min(dates)).days
    if duration_days < 1: duration_days = 1
    
    burn_rate_daily = total_spend / duration_days
    return burn_rate_daily

def calculate_interest(principal, rate_percent=2.0, years=1.0):
    """
    Simple Interest Calculator (LIBOR + X%).
    Source: PROCEED - Tool Functionality .docx 
    """
    return principal * (rate_percent / 100) * years

# ==============================================================================
# 2. LOGIC CONTROLLER
# ==============================================================================

def check_sealed_offers(final_award_val):
    """
    Checks the 'Vault' for any offers higher than the Award.
    Source: Cost Allocation Tool (AI).docx [cite: 145-146]
    """
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
# 3. AI DRAFTING LAYER (VERTEX AI)
# ==============================================================================

def generate_cost_award_draft(case_id, final_award_val):
    try:
        # A. RUN CALCULATIONS FIRST (Safe Zone)
        c_score, c_pen = calculate_doc_prod_score('claimant')
        r_score, r_pen = calculate_doc_prod_score('respondent')
        
        c_delay_pct, c_log = calculate_delay_penalties('claimant')
        r_delay_pct, r_log = calculate_delay_penalties('respondent')
        
        c_burn = calculate_burn_rate('claimant')
        r_burn = calculate_burn_rate('respondent')
        
        reversals = check_sealed_offers(final_award_val) if final_award_val else []
        
        # B. CONSTRUCT PROMPT (Feed facts to AI)
        prompt = f"""
        You are an International Arbitrator drafting the 'Final Award on Costs' for Case {case_id}.
        
        Strictly adhere to the following CALCULATED DATA. Do not invent numbers.
        
        1. CONDUCT METRICS:
        - Claimant: {c_score:.1f}% Doc Rejection Rate. Burn Rate: €{c_burn:,.2f}/day.
        - Respondent: {r_score:.1f}% Doc Rejection Rate. Burn Rate: €{r_burn:,.2f}/day.
        *Rule: Rejection >75% triggers 100% cost allocation penalty.*
        
        2. DELAY PENALTIES:
        - Claimant: -{c_delay_pct}% deduction. Reason: {c_log}
        - Respondent: -{r_delay_pct}% deduction. Reason: {r_log}
        
        3. SEALED OFFERS (Reverse Cost Shifting):
        {f"- TRIGGERED: {reversals[0]['payer']} pays {reversals[0]['offerer']} post-offer costs of €{reversals[0]['reversal_sum']:,.2f}" if reversals else "- None triggered."}
        
        Draft a formal legal analysis (3 paragraphs) determining the net cost allocation. 
        Cite the 'Burn Rate' as a measure of reasonableness.
        """
        
        # C. GENERATE
        if "gcp_service_account" in st.secrets:
            project_id = st.secrets["gcp_service_account"]["project_id"]
            vertexai.init(project=project_id, location="us-central1")
            model = TextGenerationModel.from_pretrained("text-bison")
            response = model.predict(prompt, temperature=0.2, max_output_tokens=512)
            return response.text
        else:
            return f"**[Demo Mode]** Vertex AI not connected.\n\nPrompt Context:\n{prompt}"

    except Exception as e:
        return f"Error: {e}"
