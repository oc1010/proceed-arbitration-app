import streamlit as st
from datetime import datetime, date
import vertexai
from vertexai.language_models import TextGenerationModel
from db import load_complex_data, load_full_config

# --- 1. LOGIC ENGINES ---

def calculate_doc_prod_score(role):
    """
    [cite_start]Calculates the 'Proportionality Score' based on rejected requests[cite: 55].
    [cite_start]Logic: Ratio Trigger = Requests Rejected / Total Requests * 100[cite: 59].
    """
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    
    # [cite_start]Load threshold from settings (Default 75%) [cite: 61]
    threshold = meta.get('cost_settings', {}).get('doc_prod_threshold', 75.0)
    
    # Get requests made BY this role
    requests = data.get('doc_prod', {}).get(role, [])
    
    if not requests:
        return 0.0, False
    
    total = len(requests)
    # Count requests where status is specifically 'Denied'
    rejected = sum(1 for r in requests if r.get('status') == 'Denied')
    
    # Calculate Ratio
    if total > 0:
        ratio = (rejected / total) * 100
    else:
        ratio = 0.0
        
    # [cite_start]Check if penalty is triggered [cite: 61]
    penalty_triggered = ratio > threshold
    
    return ratio, penalty_triggered

def calculate_delay_penalties(role):
    """
    [cite_start]Calculates deductions for delays based on 24-hour periods[cite: 69].
    Logic: Checks for items marked 'Awaiting Compliance' and counts days overdue.
    """
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    
    # [cite_start]Load penalty rate (Default 0.5% per day) [cite: 71]
    rate = meta.get('cost_settings', {}).get('delay_penalty_rate', 0.5)
    
    timeline = data.get('timeline', [])
    total_deduction_percent = 0.0
    delay_log = []

    for item in timeline:
        # [cite_start]Check if item belongs to this role [cite: 145]
        # responsible_party key used per Procedural Timetable doc changes
        responsible = item.get('responsible_party', '').lower()
        
        # Match role (handling "Both" or "All" implies both parties might be liable, 
        # but strict logic usually targets specific 'Claimant' or 'Respondent' tasks)
        if responsible == role or responsible in ['both', 'all']:
            deadline_str = item.get('deadline')
            status = item.get('compliance_status', 'Commenced and Pending')
            
            # [cite_start]Logic: If status is 'Awaiting Compliance', it is currently overdue [cite: 67]
            if status == "Awaiting Compliance" and deadline_str:
                try:
                    d_dead = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                    d_now = date.today()
                    
                    if d_now > d_dead:
                        delta = (d_now - d_dead).days
                        penalty = delta * rate
                        
                        # Accumulate totals
                        total_deduction_percent += penalty
                        delay_log.append(f"{item['milestone']}: {delta} days overdue (-{penalty}%)")
                except Exception:
                    pass
            
            # Note: For 'Completed' items, a more advanced version would check 
            # 'completed_at' timestamp vs 'deadline' to calculate historical penalties.
            # [cite_start]For this version, we focus on active delays as per the 'Awaiting Compliance' trigger[cite: 67].

    return total_deduction_percent, delay_log

def check_sealed_offers(final_award_val):
    """
    [cite_start]Checks if a sealed offer triggers cost reversal[cite: 87].
    Logic: If Award < Rejected Offer, cost reversal is triggered.
    """
    data = load_complex_data()
    offers = data.get('costs', {}).get('sealed_offers', [])
    
    reversal_triggers = []
    
    for offer in offers:
        try:
            offer_val = float(offer.get('amount', 0.0))
            offerer = offer.get('offerer')
            
            # Logic: If the Final Award is LESS than the Offer, the Offerer 
            # 'won' the settlement game (they offered more than the Tribunal awarded).
            # [cite_start]Therefore, the Rejecting Party should pay costs from the Offer Date. [cite: 87]
            if final_award_val < offer_val:
                reversal_triggers.append({
                    "offerer": offerer,
                    "offer_date": offer.get('date'),
                    "offer_amount": offer_val,
                    "award_amount": final_award_val
                })
        except Exception:
            pass
            
    return reversal_triggers

# --- 2. AI GENERATION (VERTEX) ---

def generate_cost_award_draft(case_id):
    """
    [cite_start]Generates the Final Cost Allocation Summary[cite: 105].
    Synthesizes Doc Prod scores, Delay penalties, and general principles.
    """
    try:
        # 1. Gather Context Metrics
        c_score, c_pen = calculate_doc_prod_score('claimant')
        r_score, r_pen = calculate_doc_prod_score('respondent')
        
        c_delay_pct, c_delay_log = calculate_delay_penalties('claimant')
        r_delay_pct, r_delay_log = calculate_delay_penalties('respondent')
        
        # 2. Construct Prompt for the LLM
        # We act as a helpful assistant drafting the 'Costs' section of the award.
        prompt = f"""
        You are an International Arbitrator drafting the 'Final Award on Costs' for Case {case_id}.
        
        Based on the PROCEED Platform data, draft a reasoned analysis of the cost allocation (approx 200 words).
        
        DATA INPUTS:
        
        A. DOCUMENT PRODUCTION CONDUCT (Proportionality Score):
        - Claimant: {c_score:.1f}% Rejection Rate. (Penalty Triggered: {c_pen})
        - Respondent: {r_score:.1f}% Rejection Rate. (Penalty Triggered: {r_pen})
        *Rule: If rejection rate > 75%, the requesting party bears 100% of their own document production costs.*
        
        B. PROCEDURAL EFFICIENCY (Delay Penalties):
        - Claimant Total Penalty Deduction: -{c_delay_pct}% of recoverable costs.
          Details: {', '.join(c_delay_log) if c_delay_log else 'No current delays.'}
        - Respondent Total Penalty Deduction: -{r_delay_pct}% of recoverable costs.
          Details: {', '.join(r_delay_log) if r_delay_log else 'No current delays.'}
        
        C. GENERAL COST PRINCIPLE:
        - "Costs follow the event" (The loser pays the winner's costs), subject to the conduct adjustments above.
        
        INSTRUCTIONS:
        Draft the 'Analysis on Costs' section. 
        1. Start by stating the general principle.
        2. Address Document Production: Specifically mention if anyone triggered the 75% threshold penalty.
        3. Address Delays: Mention specific deductions if applicable.
        4. Conclude with a summary of how these factors adjust the final figure.
        """
        
        # 3. Call Vertex AI
        # Note: This checks for the specific service account structure used in the app.
        if "gcp_service_account" in st.secrets:
            try:
                # Initialize Vertex AI (This requires Project ID from secrets)
                project_id = st.secrets["gcp_service_account"]["project_id"]
                vertexai.init(project=project_id, location="us-central1")
                
                model = TextGenerationModel.from_pretrained("text-bison")
                
                parameters = {
                    "temperature": 0.2, # Low temperature for legal/formal consistency
                    "max_output_tokens": 512,
                    "top_p": 0.8,
                    "top_k": 40
                }
                
                response = model.predict(prompt, **parameters)
                return response.text
                
            except Exception as e_ai:
                return f"**[AI System Note]** Vertex AI connection established, but generation failed: {e_ai}\n\n**Fallback Draft:**\n{_generate_fallback_draft(c_score, c_pen, r_score, r_pen, c_delay_pct, r_delay_pct)}"
        else:
            # Fallback for when no API key is present (Demo Mode)
            return _generate_fallback_draft(c_score, c_pen, r_score, r_pen, c_delay_pct, r_delay_pct)

    except Exception as e:
        return f"System Error generating award: {e}"

def _generate_fallback_draft(c_score, c_pen, r_score, r_pen, c_delay, r_delay):
    """
    Deterministic fallback text if AI is offline.
    """
    text = "### ⚖️ Tribunal's Analysis on Costs (Draft)\n\n"
    text += "**1. General Principle**\n"
    text += "The Tribunal applies the principle that costs follow the event, subject to the Parties' conduct during the proceedings.\n\n"
    
    text += "**2. Document Production (Proportionality Score)**\n"
    if c_pen:
        text += f"- **Claimant:** The Claimant's document requests resulted in a rejection rate of {c_score:.1f}%, exceeding the 75% threshold. Accordingly, the Claimant shall bear 100% of its own costs related to the document production phase.\n"
    else:
        text += f"- **Claimant:** The rejection rate of {c_score:.1f}% was within reasonable limits.\n"
        
    if r_pen:
        text += f"- **Respondent:** The Respondent's rejection rate was {r_score:.1f}%, triggering the automatic cost penalty.\n"
    else:
        text += f"- **Respondent:** Conduct was within acceptable parameters ({r_score:.1f}% rejected).\n"
    
    text += "\n**3. Procedural Delays**\n"
    if c_delay > 0:
        text += f"- The Claimant's recoverable costs are reduced by **{c_delay}%** due to recorded procedural delays.\n"
    if r_delay > 0:
        text += f"- The Respondent's recoverable costs are reduced by **{r_delay}%** due to recorded procedural delays.\n"
        
    if c_delay == 0 and r_delay == 0:
        text += "- No deductions for delay are applied to either Party.\n"
        
    return text
