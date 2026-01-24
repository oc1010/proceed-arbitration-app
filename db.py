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

# --- 1. CONFIGURATION & RELEASE STATUS ---
@st.cache_data(ttl=60)
def load_full_config():
    """Loads the entire configuration object (questions + status flags)."""
    url = f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            return resp.json().get('record', {})
    except: pass
    return {}

def load_structure(phase="phase2"):
    """Returns the list of questions for a specific phase."""
    data = load_full_config()
    return data.get(phase, [])

def get_release_status():
    """Returns dictionary of release flags (e.g. {'phase1': True, 'phase2': False})."""
    data = load_full_config()
    # Default: Phase 1 is released if it exists, Phase 2 starts hidden
    return {
        "phase1": data.get("phase1_released", False),
        "phase2": data.get("phase2_released", False)
    }

def save_structure(new_questions, phase="phase2"):
    """Saves questions without changing release status."""
    current_data = load_full_config()
    current_data[phase] = new_questions
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json=current_data, headers=HEADERS)
    load_full_config.clear()

def set_release_status(phase, status=True):
    """Updates just the release flag."""
    current_data = load_full_config()
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
            data = resp.json().get('record', {})
            if "initial_setup" in data: return {"claimant": {}, "respondent": {}}
            return data.get(phase, {"claimant": {}, "respondent": {}})
    except: pass
    return {"claimant": {}, "respondent": {}}

def save_responses(new_phase_data, phase="phase2"):
    url = f"https://api.jsonbin.io/v3/b/{BIN_RESP}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        current_full_data = resp.json().get('record', {})
    except: 
        current_full_data = {}
    
    current_full_data[phase] = new_phase_data
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_RESP}", json=current_full_data, headers=HEADERS)
    load_responses.clear()

# --- 3. TIMELINE ---
@st.cache_data(ttl=5)
def load_timeline():
    url = f"https://api.jsonbin.io/v3/b/{BIN_TIME}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json().get('record', [])
            if isinstance(data, list):
                return [x for x in data if "initial_setup" not in x]
    except: pass
    return []

def save_timeline(data):
    url = f"https://api.jsonbin.io/v3/b/{BIN_TIME}"
    requests.put(url, json=data, headers=HEADERS)
    load_timeline.clear()

# --- 4. RESET ---
def reset_database():
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json={"initial_setup": True}, headers=HEADERS)
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_RESP}", json={"initial_setup": True}, headers=HEADERS)
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=[{"initial_setup": True}], headers=HEADERS)
    load_full_config.clear()
    load_responses.clear()
    load_timeline.clear()
    return True
