import streamlit as st
from datetime import datetime, date
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from google.api_core.exceptions import NotFound, Forbidden, ServiceUnavailable, InvalidArgument
from db import load_complex_data, load_full_config

# ==============================================================================
# 1. DETERMINISTIC CALCULATION ENGINE (Hard Math - No Hallucinations)
# ==============================================================================

def calculate_doc_prod_score(role):
    """
    Calculates the 'Proportionality Score' strictly via math.
    Source: Cost Allocation Tool (AI)
    """
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
    """
    Calculates delay deductions based on 'Approved' extension requests.
    Source: Cost Allocation Tool (AI)
    """
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    rate = meta.get('cost_settings', {}).get('delay_penalty_rate', 0.5)
    
    delays_log = data.get('delays', [])
    total_deduction_percent = 0.0
    detailed_log = []

    for d in delays_log:
        if d.get('requestor') == role and d.get('status') == 'Approved':
            # For demo purposes, we estimate typical delay lengths if precise days aren't logged
            days = 14 if "Statement" in d['event'] else 7 
            penalty = days * rate
            total_deduction_percent += penalty
            detailed_log.append(f"{d['event']} ({days} days @ {rate}%/day)")

    return total_deduction_percent, detailed_log

def calculate_reversal_amount(offerer_role, offer_date_str):
    """
    Filters and sums costs incurred AFTER the specific cut-off date.
    Source: Cost Allocation Tool (AI)
    """
    data = load_complex_data()
    costs = data.get('costs', {})
    
    # The Party who REJECTED the offer (the Opposing Party) is the one who pays
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
    Calculates average spend per day to detect inflation/reasonableness.
    Source: Cost Allocation Tool (AI)
    """
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

def check_sealed_offers(final_award_val):
    """
    Checks the 'Vault' for any offers higher than the Award.
    Source: Cost Allocation Tool (AI)
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
# 2. AI DRAFTING LAYER (Robust Multi-Model Fallback)
# ==============================================================================

def try_generate_with_fallback(prompt, project_id, credentials):
    """
    Attempts to generate content using a prioritized list of models.
    Falls back sequentially if a model is 404 Not Found or 403 Forbidden.
    """
    
    # PRIORITY LIST (Newest 2.5 -> 2.0 -> Legacy 1.5/1.0)
    models_to_try = [
        "gemini-2.5-pro",           # Best available (June 2025 release)
        "gemini-2.5-flash",         # Fast alternative
        "gemini-2.0-flash-001",     # Previous stable (Feb 2025)
        "gemini-1.5-pro-001",       # Legacy stable
        "gemini-1.5-flash-001",     # Legacy fast
        "gemini-1.0-pro"            # Absolute backup
    ]
    
    last_error = None
    
    # Try initializing Vertex AI once
    try:
        vertexai.init(project=project_id, location="us-central1", credentials=credentials)
    except Exception as e:
        return f"**[Connection Error]** Failed to initialize Vertex AI: {e}"

    # Loop through models
    for model_name in models_to_try:
        try:
            model = GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
            
        except (NotFound, Forbidden, InvalidArgument, ServiceUnavailable) as e:
            # Catch specific Google Cloud errors indicating model unavailability
            last_error = f"{model_name}: {e}"
            continue # Try the next model in the list
            
        except Exception as e:
            # Catch unexpected errors
            last_error = f"{model_name} (Unexpected): {e}"
            continue

    # If ALL models fail
    return f"""
    **[System Error]** AI Generation Failed.
    
    Tried the following models without success:
    {', '.join(models_to_try)}
    
    **Last Error:** {last_error}
    
    *Please check Google Cloud Console > Vertex AI > Model Garden to see which models are enabled for your project.*
    """

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
        
        # B. CONSTRUCT PROMPT (THE "JUNIOR ASSOCIATE" PERSONA)
        # We explicitly instruct the AI to be deferential and data-driven.
        prompt = f"""
        You are acting as the Tribunal Secretary preparing a DRAFT Cost Allocation Memorandum for the Sole Arbitrator in Case {case_id}.
        
        YOUR TASK:
        Provide a reasoned recommendation for cost allocation based SOLELY on the hard data below. 
        Use professional, neutral legal language. 
        Do NOT decide the case; explicitly frame conclusions as "recommendations based on the data" subject to Tribunal discretion.
        
        HARD DATA FROM CASE MANAGEMENT SYSTEM:
        
        1. DOCUMENT PRODUCTION CONDUCT (Proportionality Metric):
        - Claimant: {c_score:.1f}% of requests were Denied. (Burn Rate: €{c_burn:,.2f}/day)
        - Respondent: {r_score:.1f}% of requests were Denied. (Burn Rate: €{r_burn:,.2f}/day)
        *Framework Rule: A rejection rate >75% is flagged as potentially excessive.*
        
        2. PROCEDURAL EFFICIENCY (Delay Penalties):
        - Claimant: {c_delay_pct}% total deduction recommended. Details: {c_log}
        - Respondent: {r_delay_pct}% total deduction recommended. Details: {r_log}
        *Framework Rule: 0.5% cost deduction per 24h of non-consensual delay.*
        
        3. SETTLEMENT BEHAVIOR (Sealed Offer Vault):
        {f"- ALERT: A Sealed Offer was rejected. The Award is LESS favorable than the offer. The Rejecting Party ({reversals[0]['payer']}) should typically bear costs incurred after {reversals[0]['offer_date']} (approx €{reversals[0]['reversal_sum']:,.2f})." if reversals else "- No sealed offers triggered a reversal."}
        
        DRAFTING STRUCTURE:
        1. **Analysis of Conduct:** Compare the parties' document production ratios and efficiency, citing the burn rates.
        2. **Financial Implications:** Apply the specific penalties calculated above.
        3. **Recommendation:** Summarize the net allocation (e.g., "Claimant should recover X% of costs"), subject to the Tribunal's final discretion.
        """
        
        # C. GENERATE USING FALLBACK LOGIC
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            project_id = st.secrets["gcp_service_account"]["project_id"]
            
            return try_generate_with_fallback(prompt, project_id, creds)
        else:
            return f"**[Demo Mode]** Vertex AI not connected.\n\nPrompt Context:\n{prompt}"

    except Exception as e:
        return f"Error during AI Generation: {e}"
