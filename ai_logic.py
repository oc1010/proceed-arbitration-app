import streamlit as st
from datetime import datetime, date
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from google.api_core.exceptions import NotFound, Forbidden, ServiceUnavailable, InvalidArgument
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from db import load_complex_data, load_full_config

# ==============================================================================
# 1. HARD MATH ENGINE (Deterministic - No Hallucinations)
# ==============================================================================

def calculate_doc_prod_score(role):
    [cite_start]"""Calculates Proportionality Score (Rejection Rate) [cite: 49-51]."""
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
    [cite_start]"""Calculates Delay Deduction (0.5% per day) [cite: 59-61]."""
    data = load_complex_data()
    meta = load_full_config().get('meta', {})
    rate = meta.get('cost_settings', {}).get('delay_penalty_rate', 0.5)
    
    delays_log = data.get('delays', [])
    total_deduction_percent = 0.0
    detailed_log = []

    for d in delays_log:
        if d.get('requestor') == role and d.get('status') == 'Approved':
            # Use actual days if available, else estimate for demo
            days = 14 if "Statement" in d['event'] else 7 
            penalty = days * rate
            total_deduction_percent += penalty
            detailed_log.append(f"{d['event']} ({days} days @ {rate}%/day)")

    return total_deduction_percent, detailed_log

def calculate_reversal_amount(offerer_role, offer_date_str):
    [cite_start]"""Calculates 'Costs Incurred After Offer'[cite: 86]."""
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
        except: continue
            
    return reversal_sum, rejecting_party

def calculate_burn_rate(role):
    [cite_start]"""Calculates Average Daily Spend[cite: 88]."""
    data = load_complex_data()
    costs = data.get('costs', {}).get(f"{role}_log", [])
    
    if not costs: return 0.0
    
    total_spend = sum(float(c['amount']) for c in costs)
    
    dates = []
    for c in costs:
        try: dates.append(datetime.strptime(c['date'], "%Y-%m-%d"))
        except: pass
            
    if not dates: return 0.0
    
    duration_days = (max(dates) - min(dates)).days
    if duration_days < 1: duration_days = 1
    
    return total_spend / duration_days

def check_sealed_offers(final_award_val):
    [cite_start]"""Checks Sealed Offer Vault for Reversals [cite: 76-77]."""
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
# 2. AI DRAFTING (Robust Fallback & Advisory Tone)
# ==============================================================================

def try_generate_with_fallback(prompt, project_id, credentials):
    """Tries models in order: 2.5 -> 2.0 -> 1.5 -> 1.0"""
    models_to_try = [
        "gemini-2.5-pro", "gemini-2.5-flash", 
        "gemini-2.0-flash-001", 
        "gemini-1.5-pro-001", "gemini-1.5-flash-001",
        "gemini-1.0-pro"
    ]
    
    try:
        vertexai.init(project=project_id, location="us-central1", credentials=credentials)
    except Exception as e:
        return f"**[Connection Error]** Failed to initialize Vertex AI: {e}"

    for model_name in models_to_try:
        try:
            model = GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except (NotFound, Forbidden, InvalidArgument, ServiceUnavailable):
            continue
        except Exception as e:
            return f"Error with {model_name}: {e}"
            
    return "**[System Error]** All AI models failed. Please check API permissions."

def generate_cost_award_draft(case_id, final_award_val):
    try:
        # A. Gather Hard Data
        c_score, c_pen = calculate_doc_prod_score('claimant')
        r_score, r_pen = calculate_doc_prod_score('respondent')
        c_delay_pct, c_log = calculate_delay_penalties('claimant')
        r_delay_pct, r_log = calculate_delay_penalties('respondent')
        c_burn = calculate_burn_rate('claimant')
        r_burn = calculate_burn_rate('respondent')
        reversals = check_sealed_offers(final_award_val) if final_award_val else []
        
        # B. Advisory Prompt
        prompt = f"""
        Act as a TRIBUNAL SECRETARY drafting a confidential "Recommendation on Costs" for the Arbitrator in Case {case_id}.
        
        INSTRUCTIONS:
        1. Rely SOLELY on the HARD DATA below. Do not invent facts.
        2. Frame all conclusions as "recommendations" subject to the Tribunal's discretion.
        3. Be concise, professional, and data-driven.
        
        HARD DATA:
        
        [1] CONDUCT & PROPORTIONALITY (Document Production):
        - Claimant Rejection Rate: {c_score:.1f}% (Burn Rate: €{c_burn:,.2f}/day)
        - Respondent Rejection Rate: {r_score:.1f}% (Burn Rate: €{r_burn:,.2f}/day)
        *Guideline: Rejection rates >75% suggest excessive requests.*
        
        [2] PROCEDURAL EFFICIENCY (Delays):
        - Claimant Penalty: -{c_delay_pct}% recommended ({c_log})
        - Respondent Penalty: -{r_delay_pct}% recommended ({r_log})
        *Guideline: 0.5% deduction per day of non-consensual delay.*
        
        [3] SETTLEMENT (Sealed Offers):
        {f"- REVERSAL TRIGGERED: {reversals[0]['payer']} rejected a favorable offer. Recommend shifting costs incurred after {reversals[0]['offer_date']} (€{reversals[0]['reversal_sum']:,.2f})." if reversals else "- No cost reversal triggered."}
        
        DRAFT STRUCTURE:
        I. Analysis of Conduct & Efficiency
        II. Calculation of Recommended Penalties
        III. Final Recommendation on Allocation
        """
        
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
            return try_generate_with_fallback(prompt, st.secrets["gcp_service_account"]["project_id"], creds)
        else:
            return f"**[Demo Mode]** Vertex AI Disconnected.\n\nContext:\n{prompt}"

    except Exception as e:
        return f"Error: {e}"

# ==============================================================================
# 3. WORD DOCUMENT GENERATOR (Professional Formatting)
# ==============================================================================

def generate_word_document(case_id, draft_text, award_val):
    """Generates a downloadable .docx with legal formatting and disclaimers."""
    doc = Document()
    
    # Styles
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    
    # Header
    head = doc.add_heading(f"IN THE MATTER OF ARBITRATION: {case_id}", 0)
    head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph("\n")
    title = doc.add_paragraph("MEMORANDUM ON COST ALLOCATION (DRAFT)")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].bold = True
    
    # [cite_start]Red Disclaimer [cite: 14]
    doc.add_paragraph("\n")
    p = doc.add_paragraph()
    run = p.add_run("--- PRIVILEGED & CONFIDENTIAL / AI ASSISTED DRAFT ---")
    run.font.color.rgb = RGBColor(255, 0, 0)
    run.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p2 = doc.add_paragraph("DISCLAIMER: This document is a preliminary analysis generated by the PROCEED Case Management System based on logged procedural data. It constitutes a recommendation only and does not represent the final decision of the Tribunal.")
    p2.runs[0].italic = True
    p2.runs[0].font.size = Pt(10)
    
    doc.add_paragraph("\n")
    
    # Case Context
    doc.add_heading("I. PROCEDURAL SNAPSHOT", level=1)
    doc.add_paragraph(f"Date: {date.today()}")
    doc.add_paragraph(f"Principal Award Value: €{award_val:,.2f}")
    
    # The AI Text
    doc.add_heading("II. DATA-DRIVEN ANALYSIS", level=1)
    doc.add_paragraph(draft_text)
    
    # Signature Block
    doc.add_paragraph("\n\n" + "_"*30)
    doc.add_paragraph("Reviewing Arbitrator\n(Not valid until signed)")
    
    # Save to buffer
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
