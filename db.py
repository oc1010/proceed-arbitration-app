import streamlit as st
import requests
import json

# --- CONFIG ---
API_KEY = st.secrets["X_MASTER_KEY"]
BIN_STRUCT = st.secrets["BIN_ID_STRUCT"]
BIN_RESP = st.secrets["BIN_ID_RESP"]
BIN_TIME = st.secrets["BIN_ID_TIME"]

HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": API_KEY
}

# --- 1. CONFIGURATION ---
@st.cache_data(ttl=60)
def load_full_config():
    """Loads the entire configuration object."""
    url = f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            val = resp.json()
            data = val.get('record')
            return data if isinstance(data, dict) else {}
    except: pass
    return {}

def load_structure(phase="phase2"):
    data = load_full_config()
    return data.get(phase, [])

def get_release_status():
    data = load_full_config()
    if data is None: data = {}
    return {
        "phase1": data.get("phase1_released", False),
        "phase2": data.get("phase2_released", False),
        "phase3": data.get("phase3_released", False), # Doc Prod
        "phase4": data.get("phase4_released", True),  # Timeline (Always active)
        "phase5": data.get("phase5_released", True)   # Costs (Always active)
    }

def save_structure(new_questions, phase="phase2"):
    current_data = load_full_config()
    if current_data is None: current_data = {}
    current_data[phase] = new_questions
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json=current_data, headers=HEADERS)
    load_full_config.clear()

def set_release_status(phase, status=True):
    current_data = load_full_config()
    if current_data is None: current_data = {}
    current_data[f"{phase}_released"] = status
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json=current_data, headers=HEADERS)
    load_full_config.clear()

# --- 2. RESPONSES ---
@st.cache_data(ttl=2)
def load_responses(phase="phase2"):
    url = f"https://api.jsonbin.io/v3/b/{BIN_RESP}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json().get('record')
            if data is None or "initial_setup" in data: return {"claimant": {}, "respondent": {}}
            return data.get(phase, {"claimant": {}, "respondent": {}})
    except: pass
    return {"claimant": {}, "respondent": {}}

def save_responses(new_phase_data, phase="phase2"):
    try:
        resp = requests.get(f"https://api.jsonbin.io/v3/b/{BIN_RESP}/latest", headers=HEADERS)
        current_full_data = resp.json().get('record')
        if current_full_data is None: current_full_data = {}
    except: current_full_data = {}
    
    current_full_data[phase] = new_phase_data
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_RESP}", json=current_full_data, headers=HEADERS)
    load_responses.clear()

# --- 3. COMPLEX DATA (Timeline, Docs, Costs) ---
# Stored in BIN_TIME to organize dynamic case data
@st.cache_data(ttl=2)
def load_complex_data():
    url = f"https://api.jsonbin.io/v3/b/{BIN_TIME}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json().get('record')
            if isinstance(data, dict): return data
    except: pass
    return {}

def save_complex_data(key, sub_data):
    """
    Updates a specific key (e.g., 'timeline', 'doc_prod', 'costs') preserving others.
    """
    full_data = load_complex_data()
    full_data[key] = sub_data
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=full_data, headers=HEADERS)
    load_complex_data.clear()

# --- 4. RESET ---
def reset_database():
    empty_complex = {
        "timeline": [], 
        "delays": [],
        "doc_prod": {"claimant": [], "respondent": []}, 
        "costs": {
            "claimant_log": [], "respondent_log": [], 
            "tribunal_ledger": {"deposits": 0, "balance": 0, "history": []}, 
            "app_tagging": []
        }
    }
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json={"initial_setup": True}, headers=HEADERS)
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_RESP}", json={"initial_setup": True}, headers=HEADERS)
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=empty_complex, headers=HEADERS)
    
    load_full_config.clear()
    load_responses.clear()
    load_complex_data.clear()
    return True
