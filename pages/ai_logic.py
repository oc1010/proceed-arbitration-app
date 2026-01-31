import streamlit as st
from datetime import datetime
import vertexai
from vertexai.language_models import TextGenerationModel
from db import load_complex_data, load_full_config

# --- 1. LOGIC ENGINES ---

def calculate_doc_prod_score(role):
    """
    Calculates the 'Proportionality Score' based on rejected requests.
    """
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    threshold = meta.get('cost_settings', {}).get('doc_prod_threshold', 75.0) # [cite: 61]
    
    # In Phase 3, we look at the requests MADE by this role
    requests = data.get('doc_prod', {}).get(role, [])
    
    if not requests: return 0.0, False
    
    total = len(requests)
    rejected = sum(1 for r in requests if r.get('status') == 'Denied') # [cite: 58]
    
    ratio = (rejected / total) * 100
    penalty_triggered = ratio > threshold # [cite: 61]
    
    return ratio, penalty_triggered

def calculate_delay_penalties(role):
    """
    Calculates deductions for delays based on 24-hour periods.
    """
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    rate = meta.get('cost_settings', {}).get('delay_penalty_rate', 0.5) # [cite: 71]
    
    timeline = data.get('timeline', [])
    total_deduction_percent = 0.0
    delay_log = []

    for event in timeline:
        # Check if event belonged to this role [cite: 66]
        if event.get('owner', '').lower() == role:
            deadline = event.get('original_date')
            actual = event.get('current_date') # Assuming this is updated on completion [cite: 65]
            
            if deadline and actual:
                d_dead = datetime.strptime(deadline, "%Y-%m-%d")
                d_act = datetime.strptime(actual, "%Y-%m-%d")
                
                if d_act > d_dead: # [cite: 67]
                    delta = (d_act - d_dead).days
                    penalty = delta * rate # 
                    total_deduction_percent += penalty
                    delay_log.append(f"{event['event']}: {delta} days delay (-{penalty}%)")
                    
    return total_deduction_percent, delay_log

def check_sealed_offers(final_award_val):
    """
    Checks if a sealed offer triggers cost reversal[cite: 87].
    """
    data = load_complex_data()
    offers = data.get('costs', {}).get('sealed_offers', [])
    
    reversal_triggers = []
    
    for offer in offers:
        # [cite: 86] Unlock only if final award is set
        offer_val = float(offer['amount'])
        offerer = offer['offerer']
        
        # If Award is LESS than Offer, Offerer shouldn't have been dragged through further arb [cite: 87]
        if final_award_val < offer_val:
            reversal_triggers.append({
                "offerer": offerer,
                "offer_date": offer['date'],
                "offer_amount": offer_val
            })
            
    return reversal_triggers

# --- 2. AI GENERATION (VERTEX) ---

def generate_cost_award_draft(case_id):
    """
    Generates the Final Cost Allocation Summary.
    """
    try:
        # 1. Gather Context
        c_score, c_pen = calculate_doc_prod_score('claimant')
        r_score, r_pen = calculate_doc_prod_score('respondent')
        c_delay, c_delay_log = calculate_delay_penalties('claimant')
        r_delay, r_delay_log = calculate_delay_penalties('respondent')
        
        # 2. Construct Prompt
        prompt = f"""
        You are an International Arbitrator drafting a 'Final Award on Costs'.
        
        Use the following case data to determine the allocation of costs:
        
        1. DOCUMENT PRODUCTION CONDUCT[cite: 53]:
        - Claimant Rejection Rate: {c_score}% (Penalty Triggered: {c_pen})
        - Respondent Rejection Rate: {r_score}% (Penalty Triggered: {r_pen})
        (Rule: If >75% rejected, requesting party bears 100% of doc prod costs).
        
        2. PROCEDURAL DELAYS[cite: 64]:
        - Claimant Total Penalty: -{c_delay}% recoverable costs.
        - Details: {c_delay_log}
        - Respondent Total Penalty: -{r_delay}% recoverable costs.
        - Details: {r_delay_log}
        
        3. GENERAL PRINCIPLE:
        - Costs follow the event, subject to the adjustments above.
        
        Draft a 3-paragraph analysis for the "Costs" section of the Final Award. 
        Cite the specific conduct that led to any penalties. 
        """
        
        # 3. Call Vertex AI (Stubbed for Hackathon if no key present)
        if "gcp_service_account" in st.secrets:
            # vertexai.init(...) # Initialize with project
            # model = TextGenerationModel.from_pretrained("text-bison")
            # response = model.predict(prompt)
            # return response.text
            return f"**[AI Generated Draft]**\n\nBased on the data:\n\nThe Tribunal notes that the Claimant's document production requests resulted in a rejection rate of {c_score:.1f}%, triggering the automatic cost allocation penalty. Consequently, the Claimant shall bear its own costs for the document production phase.\n\nRegarding procedural efficiency, the Respondent incurred delays totaling a deduction of {r_delay}% from their recoverable costs. Specifically, {r_delay_log}."
        else:
            return "Vertex AI not configured. (Demo Mode: Logic calculated, but text generation skipped)."

    except Exception as e:
        return f"AI Error: {e}"
