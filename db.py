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

# --- 1. STRUCTURE ---
def load_structure():
    url = f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json().get('record', resp.json())
            if "initial_setup" in data: return None
            return data
    except: pass
    return None

def save_structure(data):
    url = f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}"
    requests.put(url, json=data, headers=HEADERS)

# --- 2. RESPONSES ---
def load_responses():
    url = f"https://api.jsonbin.io/v3/b/{BIN_RESP}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json().get('record', resp.json())
            if "initial_setup" in data: return {"claimant": {}, "respondent": {}}
            return data
    except: pass
    return {"claimant": {}, "respondent": {}}

def save_responses(data):
    url = f"https://api.jsonbin.io/v3/b/{BIN_RESP}"
    requests.put(url, json=data, headers=HEADERS)

# --- 3. TIMELINE ---
def load_timeline():
    url = f"https://api.jsonbin.io/v3/b/{BIN_TIME}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json().get('record', resp.json())
            if isinstance(data, list):
                return [x for x in data if "initial_setup" not in x]
            return []
    except: pass
    return []

def save_timeline(data):
    url = f"https://api.jsonbin.io/v3/b/{BIN_TIME}"
    requests.put(url, json=data, headers=HEADERS)
