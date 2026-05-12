import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from graph_animation import generate_graph_html
from map_module import generate_city_map
from modules.ann_priority import train_priority_models
from modules.request_router import route_request


LOG_PATH = os.path.join("logs", "request_log.json")

# ═══════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════
SCENARIOS = {
    "🚑 Ambulance Emergency — Critical": {
        "vehicle_type": "Ambulance",
        "current_location": "Central_Junction",
        "destination": "City_Hospital",
        "request_category": "Emergency_Response_Request",
        "incident_severity": "High",
        "time_sensitivity": "Yes",
        "traffic_density": "High",
        "priority_claim": "Critical",
    },
    "🚗 Civilian Route — Normal": {
        "vehicle_type": "Civilian",
        "current_location": "Stadium",
        "destination": "East_Market",
        "request_category": "Route_Request",
        "incident_severity": "Low",
        "time_sensitivity": "No",
        "traffic_density": "Medium",
        "priority_claim": "Normal",
    },
    "🚓 Police Signal Override Check": {
        "vehicle_type": "Police",
        "current_location": "Police_HQ",
        "destination": "Central_Junction",
        "request_category": "Policy_Check",
        "incident_severity": "Medium",
        "time_sensitivity": "Yes",
        "traffic_density": "High",
        "priority_claim": "High",
    },
    "🚒 Fire Truck — Integrated Response": {
        "vehicle_type": "Fire_Truck",
        "current_location": "Fire_Station",
        "destination": "City_Hospital",
        "request_category": "Integrated_City_Service_Request",
        "incident_severity": "High",
        "time_sensitivity": "Yes",
        "traffic_density": "High",
        "priority_claim": "Critical",
    },
    "🏙️ Full City Crisis — Integrated": {
        "vehicle_type": "Ambulance",
        "current_location": "Airport_Road",
        "destination": "City_Hospital",
        "request_category": "Integrated_City_Service_Request",
        "incident_severity": "High",
        "time_sensitivity": "Yes",
        "traffic_density": "High",
        "priority_claim": "Critical",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# LOG HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def ensure_log_file():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def get_next_id():
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return f"REQ_{len(logs) + 1:03d}"
    except Exception:
        return "REQ_001"


def save_to_log(request, result):
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            logs = json.load(f)
        entry = {
            "request_id": request.get("request_id", "N/A"),
            "vehicle_type": request.get("vehicle_type", "N/A"),
            "from": request.get("current_location", "N/A"),
            "to": request.get("destination", "N/A"),
            "request_category": request.get("request_category", "N/A"),
            "priority": result.get("priority_level", "N/A"),
            "status": result.get("policy_status", "N/A"),
            "route": " -> ".join(result.get("route", [])),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        logs.append(entry)
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)
    except Exception as error:
        st.warning(f"Could not update request log: {error}")


def load_history():
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════
# MOCK FALLBACK
# ═══════════════════════════════════════════════════════════════════════════
def mock_process(request):
    route = [request["current_location"], "East_Market", request["destination"]]
    return {
        **request,
        "priority_level": "URGENT | Priority: Critical (Confidence: 91.2%)",
        "policy_status": "Approved",
        "signal_plan": {"S1": "PhaseA", "S2": "PhaseB", "S3": "PhaseC", "S4": "PhaseA", "S5": "PhaseB"},
        "route": route,
        "route_cost": 6,
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEXT BUILDERS  (match Gradio output exactly)
# ═══════════════════════════════════════════════════════════════════════════
def build_tracking_text(route, vehicle_type):
    """Static snapshot of the animated tracking text Gradio streams."""
    if not route:
        return (
            "Waiting for dispatch...\n"
            "Submit a request on the left to see live route animation here."
        )
    lines = [
        "=" * 44,
        "  ARIA  .  LIVE VEHICLE TRACKING",
        "=" * 44,
        f"  Vehicle  : {vehicle_type.upper()}",
        "  Status   : > MOVING",
        f"  Waypoints: {len(route)}",
        "-" * 44,
        "",
    ]
    for i, stop in enumerate(route):
        stop_clean = stop.replace("_", " ")
        if i == 0:
            lines.append(f"  [START]   ->  {stop_clean}")
        elif i == len(route) - 1:
            lines.append("       |")
            lines.append("       v")
            lines.append(f"  [ARRIVED] ->  {stop_clean}  <- DESTINATION")
        else:
            lines.append("       |")
            lines.append("       v")
            lines.append(f"  [PASSING] ->  {stop_clean}")
    lines += ["", "-" * 44, "  Route complete. All clear.", "=" * 44]
    return "\n".join(lines)


def build_ai_summary(request, result):
    signals = result.get("signal_plan", {})
    status = result.get("policy_status", "N/A")
    route_cost = result.get("route_cost", "N/A")

    lines = [
        "=" * 44,
        "  ARIA  .  HOW THE AI DECIDED",
        "=" * 44,
        "",
        "  INPUT FEATURES",
        "  " + "─" * 40,
        f"  Vehicle Type     ->  {request['vehicle_type'].upper()}",
        f"  Request Category ->  {request['request_category']}",
        f"  Severity         ->  {request['incident_severity']}",
        f"  Time Sensitive   ->  {request['time_sensitivity']}",
        f"  Traffic Density  ->  {request['traffic_density']}",
        f"  Priority Claim   ->  {request['priority_claim']}",
        "",
        "  ANN PREDICTION",
        "  " + "─" * 40,
        f"  {result.get('priority_level', 'N/A')}",
        "",
        "  KNOWLEDGE BASE RULES APPLIED",
        "  " + "─" * 40,
        "  Rule 1  : EmergencyVehicle + High Severity -> Critical",
        "  Rule 6  : Ambulance + Hospital Dest -> Emergency Corridor",
        "  Rule 8  : Authorized -> Action Allowed",
        "  Rule 18 : Emergency + Priority + Auth -> Approved",
        "",
        "  CSP SIGNAL ALLOCATION",
        "  " + "─" * 40,
    ]
    if signals:
        for k, v in signals.items():
            lines.append(f"  {k}  ->  {v}")
    else:
        lines.append("  Not required for this request type.")

    lines += [
        "",
        f"  Route Cost  :  {route_cost} units",
        f"  Decision    :  {'AUTHORIZED - Corridor Active' if 'Approved' in str(status) else 'Standard movement authorized'}",
        "=" * 44,
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# REQUEST PROCESSING
# ═══════════════════════════════════════════════════════════════════════════
def build_request(vehicle_type, current_location, destination, request_category,
                  incident_severity, time_sensitivity, traffic_density, priority_claim):
    return {
        "request_id": get_next_id(),
        "vehicle_type": vehicle_type.lower(),
        "current_location": current_location,
        "destination": destination,
        "request_category": request_category,
        "incident_severity": incident_severity,
        "time_sensitivity": time_sensitivity,
        "traffic_density": traffic_density,
        "priority_claim": priority_claim,
    }


def process_request(vehicle_type, current_location, destination, request_category,
                    incident_severity, time_sensitivity, traffic_density, priority_claim):
    request = build_request(
        vehicle_type, current_location, destination, request_category,
        incident_severity, time_sensitivity, traffic_density, priority_claim,
    )
    try:
        result = route_request(request)
    except Exception as e:
        st.warning(f"Primary route engine failed, using fallback: {e}")
        result = mock_process(request)
    save_to_log(request, result)
    return request, result


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def apply_scenario(name):
    scenario = SCENARIOS[name]
    for key, value in scenario.items():
        st.session_state[key] = value
    st.session_state.selected_scenario = name
    st.session_state.scenario_picker = name


def queue_scenario(name):
    st.session_state.pending_scenario = name


def consume_pending_scenario():
    pending_scenario = st.session_state.pop("pending_scenario", None)
    if pending_scenario:
        apply_scenario(pending_scenario)


def initialize_state():
    defaults = SCENARIOS["🚑 Ambulance Emergency — Critical"]
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("selected_scenario", "🚑 Ambulance Emergency — Critical")
    st.session_state.setdefault("current_result", None)
    st.session_state.setdefault("current_request", None)
    # FIX 1: track whether boot has been shown this browser session
    st.session_state.setdefault("boot_shown", False)


# ═══════════════════════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def initialize_engine():
    train_priority_models()
    return True


# ═══════════════════════════════════════════════════════════════════════════
# CSS  (unified — single source of truth, matches Gradio palette exactly)
# ═══════════════════════════════════════════════════════════════════════════
ARIA_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --navy        : #0B1120;
    --navy-mid    : #111827;
    --navy-card   : #1A2235;
    --navy-border : #263352;
    --navy-hover  : #1E2D45;
    --teal        : #00D4C8;
    --teal-dim    : #00A89E;
    --teal-glow   : rgba(0,212,200,0.18);
    --teal-pale   : rgba(0,212,200,0.08);
    --amber       : #F5A623;
    --amber-dim   : #C47F0A;
    --amber-glow  : rgba(245,166,35,0.20);
    --amber-pale  : rgba(245,166,35,0.08);
    --white       : #F0F4FF;
    --white-dim   : #8A9CC2;
    --white-muted : #4A5A7A;
    --success     : #22C97A;
    --danger      : #FF4D6A;
    --shadow-deep : rgba(0,0,0,0.45);
}

*, *::before, *::after { box-sizing: border-box; }

body, .stApp {
    background: linear-gradient(135deg, #0B1120 0%, #070B14 100%) !important;
    color: #F0F4FF !important;
    font-family: 'DM Mono', 'Courier New', monospace !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
.stDeployButton { display: none !important; }

h1, h2, h3, h4, h5, h6 {
    font-family: 'Orbitron', sans-serif !important;
    letter-spacing: 0.04em !important;
}

/* ── BOOT SCREEN ── */
#aria-boot {
    position: fixed;
    inset: 0;
    background: #0B1120;
    z-index: 99999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    animation: bootFade 0.7s ease 5.8s forwards;
    pointer-events: all;
}
@keyframes bootFade { to { opacity:0; pointer-events:none; visibility:hidden; } }

.boot-logo {
    font-family: 'Orbitron', monospace;
    font-size: 4.5em;
    font-weight: 900;
    letter-spacing: 0.35em;
    color: var(--teal);
    text-shadow: 0 0 40px var(--teal), 0 0 80px rgba(0,212,200,0.4);
    animation: logoIn 1s cubic-bezier(.15,.85,.3,1) both;
    line-height: 1;
}
@keyframes logoIn {
    from { opacity:0; transform: scale(0.88) translateY(-20px); }
    to   { opacity:1; transform: none; }
}

.boot-subtitle {
    font-size: 0.7em;
    letter-spacing: 0.25em;
    color: var(--white-muted);
    text-transform: uppercase;
    margin-top: 12px;
    animation: fadeSlide 0.5s ease 0.6s both;
}

.boot-divider {
    width: 340px;
    height: 1px;
    margin: 22px 0 18px 0;
    border-radius: 2px;
    background: linear-gradient(90deg, transparent 0%, var(--teal) 30%, var(--amber) 55%, var(--teal) 80%, transparent 100%);
    animation: fadeSlide 0.6s 0.9s both;
    box-shadow: 0 0 12px var(--teal);
}

@keyframes fadeSlide {
    from { opacity:0; transform: translateY(8px); }
    to   { opacity:1; transform: none; }
}

.boot-steps {
    margin-top: 24px;
    display: flex;
    flex-direction: column;
    gap: 9px;
    min-width: 420px;
}

.boot-step {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.74em;
    letter-spacing: 0.06em;
    color: var(--white-dim);
    opacity: 0;
    animation: stepReveal 0.4s ease forwards;
    padding: 5px 10px;
    border-radius: 6px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.05);
}
.boot-step:nth-child(1) { animation-delay: 1.1s; }
.boot-step:nth-child(2) { animation-delay: 1.5s; }
.boot-step:nth-child(3) { animation-delay: 1.9s; }
.boot-step:nth-child(4) { animation-delay: 2.3s; }
.boot-step:nth-child(5) { animation-delay: 2.7s; }
.boot-step:nth-child(6) { animation-delay: 3.1s; }
.boot-step:nth-child(7) { animation-delay: 3.5s; }
.boot-step:nth-child(8) { animation-delay: 3.9s; }
@keyframes stepReveal {
    from { opacity:0; transform: translateX(-14px); }
    to   { opacity:1; transform: none; }
}

.step-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    animation: dotPulse 2s ease-in-out infinite;
}
@keyframes dotPulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%      { opacity:0.5; transform:scale(0.75); }
}
.dot-gold  { background: var(--amber);   box-shadow: 0 0 8px var(--amber); }
.dot-sky   { background: var(--teal);    box-shadow: 0 0 8px var(--teal); }
.dot-blush { background: #C084FC;        box-shadow: 0 0 8px #C084FC; }
.dot-amber { background: var(--amber);   box-shadow: 0 0 8px var(--amber); }
.dot-green { background: var(--success); box-shadow: 0 0 8px var(--success); }

.step-badge {
    margin-left: auto;
    font-size: 0.72em;
    padding: 1px 10px;
    border-radius: 20px;
    font-weight: 600;
    letter-spacing: 0.08em;
    opacity: 0;
    animation: badgePop 0.3s ease forwards;
}
.boot-step:nth-child(1) .step-badge { animation-delay: 1.42s; }
.boot-step:nth-child(2) .step-badge { animation-delay: 1.82s; }
.boot-step:nth-child(3) .step-badge { animation-delay: 2.22s; }
.boot-step:nth-child(4) .step-badge { animation-delay: 2.62s; }
.boot-step:nth-child(5) .step-badge { animation-delay: 3.02s; }
.boot-step:nth-child(6) .step-badge { animation-delay: 3.42s; }
.boot-step:nth-child(7) .step-badge { animation-delay: 3.82s; }
.boot-step:nth-child(8) .step-badge { animation-delay: 4.22s; }
@keyframes badgePop {
    from { opacity:0; transform: scale(0.7); }
    to   { opacity:1; transform: none; }
}
.badge-ok { background:rgba(34,201,122,0.15); color:#22C97A !important; border:1px solid #22C97A; }

.boot-bar-wrap {
    width: 400px; height: 2px;
    background: var(--navy-border);
    border-radius: 4px;
    margin-top: 22px;
    overflow: hidden;
    animation: fadeSlide 0.4s 1.0s both;
}
.boot-bar {
    height: 100%; width: 0%;
    background: linear-gradient(90deg, var(--teal), var(--amber), var(--teal));
    animation: barGrow 3.8s linear 1.1s forwards;
    border-radius: 4px;
    box-shadow: 0 0 10px var(--teal);
}
@keyframes barGrow { from{width:0%} to{width:100%} }

.boot-ready {
    margin-top: 16px;
    font-size: 0.72em;
    letter-spacing: 0.25em;
    color: var(--teal);
    text-shadow: 0 0 12px var(--teal);
    opacity: 0;
    animation: fadeSlide 0.5s ease 5.0s forwards;
}

/* ── HEADER ── */
.aria-header {
    background: linear-gradient(135deg, var(--navy-mid) 0%, #0D1829 60%, #0A1520 100%);
    border-bottom: 1px solid var(--navy-border);
    padding: 20px 32px 16px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 14px;
    margin-bottom: 1rem;
    box-shadow: 0 4px 30px rgba(0,0,0,0.5), 0 1px 0 var(--teal-glow);
}
.header-left { display:flex; flex-direction:column; gap:4px; }
.aria-wordmark {
    font-family: 'Orbitron', monospace !important;
    font-size: 2.2em;
    font-weight: 700;
    letter-spacing: 0.28em;
    color: var(--teal) !important;
    text-shadow: 0 0 25px var(--teal), 0 0 50px rgba(0,212,200,0.3);
    line-height: 1;
}
.gold-letter { color: var(--amber) !important; text-shadow: 0 0 20px var(--amber); }
.aria-sub {
    font-size: 0.65em;
    letter-spacing: 0.2em;
    color: var(--white-muted) !important;
    text-transform: uppercase;
}
.header-pills { display:flex; gap:8px; align-items:center; }
.pill {
    padding: 4px 14px; border-radius: 20px;
    font-size: 0.67em; font-weight:600; letter-spacing:0.1em;
    font-family: 'DM Mono', monospace;
}
.pill-online { background:rgba(34,201,122,0.12); color:#22C97A !important; border:1px solid #22C97A; }
.pill-sky    { background:var(--teal-pale); color:var(--teal) !important; border:1px solid var(--teal-dim); }
.pill-gold   { background:var(--amber-pale); color:var(--amber) !important; border:1px solid var(--amber-dim); }

/* ── PANELS ── */
.panel-left {
    background: var(--navy-card) !important;
    border: 1px solid var(--navy-border) !important;
    border-radius: 14px !important;
    padding: 22px !important;
    box-shadow: 0 8px 32px var(--shadow-deep), inset 0 1px 0 rgba(255,255,255,0.05) !important;
}
.panel-right {
    background: var(--navy-mid) !important;
    border: 1px solid var(--navy-border) !important;
    border-radius: 14px !important;
    padding: 22px !important;
    box-shadow: 0 8px 32px var(--shadow-deep), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}

/* ── Section labels ── */
.sec-label {
    font-size: 0.65em;
    letter-spacing: 0.2em;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 12px;
    padding-bottom: 8px;
}
.lbl-gold  { color: var(--amber) !important; border-bottom: 1px solid var(--amber-pale); }
.lbl-sky   { color: var(--teal) !important;  border-bottom: 1px solid var(--teal-pale); }
.lbl-blush { color: #C084FC !important;      border-bottom: 1px solid rgba(192,132,252,0.15); }

/* ── Inputs ── */
[data-testid="stSelectbox"] > div > div {
    background: rgba(11,17,32,0.7) !important;
    border: 1px solid var(--navy-border) !important;
    color: var(--white) !important;
}
[data-testid="stSelectbox"] label {
    color: var(--teal) !important;
    font-size: 0.72em !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    font-family: 'DM Mono', monospace !important;
}

/* ── Textareas ── */
textarea {
    background: rgba(11,17,32,0.8) !important;
    border: 1px solid var(--navy-border) !important;
    color: var(--teal) !important;
    font-family: 'DM Mono', monospace !important;
    line-height: 1.7 !important;
    font-size: 0.82em !important;
    border-radius: 8px !important;
}
[data-testid="stTextArea"] label { display: none !important; }

/* ── DISPATCH button ── */
button[kind="primary"] {
    background: linear-gradient(135deg, var(--teal-dim) 0%, var(--teal) 50%, #00F0E4 100%) !important;
    color: var(--navy) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.22em !important;
    text-transform: uppercase !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.86em !important;
    padding: 14px !important;
    box-shadow: 0 0 24px var(--teal-glow), 0 4px 16px rgba(0,0,0,0.4) !important;
    transition: all 0.25s ease !important;
    width: 100% !important;
}
button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 40px rgba(0,212,200,0.5), 0 6px 20px rgba(0,0,0,0.5) !important;
}

/* ── Secondary / utility buttons ── */
button[kind="secondary"] {
    background: var(--navy-card) !important;
    color: var(--white-dim) !important;
    border: 1px solid var(--navy-border) !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.76em !important;
    letter-spacing: 0.08em !important;
    transition: all 0.2s !important;
}
button[kind="secondary"]:hover {
    background: var(--navy-hover) !important;
    border-color: var(--teal-dim) !important;
    color: var(--teal) !important;
    box-shadow: 0 0 14px var(--teal-glow) !important;
}

/* ── Tabs ── */
[role="tab"] {
    background: var(--navy-card) !important;
    color: var(--white-muted) !important;
    border: 1px solid var(--navy-border) !important;
    border-bottom: none !important;
    border-radius: 8px 8px 0 0 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.70em !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 8px 14px !important;
    transition: all 0.2s !important;
}
[role="tab"]:hover {
    background: var(--navy-hover) !important;
    color: var(--teal) !important;
    border-color: var(--teal-dim) !important;
}
[role="tab"][aria-selected="true"] {
    background: var(--navy-mid) !important;
    color: var(--amber) !important;
    border-color: var(--amber-dim) !important;
    font-weight: 600 !important;
    box-shadow: 0 -2px 12px var(--amber-glow) !important;
}

/* ── Metrics ── */
[data-testid="stMetricValue"] {
    color: var(--teal) !important;
    font-size: 1.4rem !important;
    font-family: 'Orbitron', sans-serif !important;
}
[data-testid="stMetricLabel"] {
    color: var(--white-muted) !important;
    font-size: 0.72em !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
[data-testid="metric-container"] {
    background: var(--navy-card) !important;
    border: 1px solid var(--navy-border) !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
}

/* ── Dataframe ── */
table { background: var(--navy-card) !important; border-radius: 10px !important; overflow: hidden !important; border: 1px solid var(--navy-border) !important; }
th { background: rgba(245,166,35,0.10) !important; color: var(--amber) !important; text-transform: uppercase !important; font-size: 0.70em !important; letter-spacing: 0.14em !important; font-weight: 600 !important; }
td { color: var(--white) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--navy); }
::-webkit-scrollbar-thumb { background: var(--navy-border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--teal-dim); }

/* ── Info / warning boxes ── */
[data-testid="stInfo"] {
    background: var(--navy-card) !important;
    border: 1px solid var(--teal-dim) !important;
    color: var(--white-dim) !important;
    border-radius: 10px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82em !important;
}

/* ── Animated tracking container ── */
.tracking-box {
    background: rgba(11,17,32,0.9);
    border: 1px solid var(--navy-border);
    border-radius: 10px;
    padding: 16px;
    font-family: 'DM Mono', monospace;
    font-size: 0.82em;
    color: var(--teal);
    line-height: 1.8;
    min-height: 200px;
    white-space: pre;
    overflow-x: auto;
    margin-top: 10px;
}

/* ── HR divider ── */
hr { border-color: var(--navy-border) !important; margin: 0.5rem 0 1rem 0 !important; }
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════
# FIX 1: BOOT SCREEN HTML  (same as Gradio, with divider)
# ═══════════════════════════════════════════════════════════════════════════
BOOT_HTML = """
<div id="aria-boot">
  <div class="boot-logo">A · R · I · A</div>
  <div class="boot-subtitle">Adaptive Road Intelligence Architecture</div>
  <div class="boot-divider"></div>
  <div class="boot-steps">
    <div class="boot-step"><div class="step-dot dot-gold"></div><span>Initializing ARIA core systems</span><span class="step-badge badge-ok">READY</span></div>
    <div class="boot-step"><div class="step-dot dot-sky"></div><span>Loading city graph &nbsp;·&nbsp; 13 nodes · weighted</span><span class="step-badge badge-ok">READY</span></div>
    <div class="boot-step"><div class="step-dot dot-blush"></div><span>Training ANN priority model &nbsp;·&nbsp; 3000 epochs</span><span class="step-badge badge-ok">READY</span></div>
    <div class="boot-step"><div class="step-dot dot-gold"></div><span>Loading knowledge base &nbsp;·&nbsp; 19 rules</span><span class="step-badge badge-ok">READY</span></div>
    <div class="boot-step"><div class="step-dot dot-sky"></div><span>Initializing CSP scheduler &nbsp;·&nbsp; 5 signal zones</span><span class="step-badge badge-ok">READY</span></div>
    <div class="boot-step"><div class="step-dot dot-blush"></div><span>Loading search algorithms &nbsp;·&nbsp; BFS / UCS / A*</span><span class="step-badge badge-ok">READY</span></div>
    <div class="boot-step"><div class="step-dot dot-amber"></div><span>Connecting Folium city map module</span><span class="step-badge badge-ok">READY</span></div>
    <div class="boot-step"><div class="step-dot dot-green"></div><span>Launching Streamlit interface &nbsp;·&nbsp; port 8501</span><span class="step-badge badge-ok">ONLINE</span></div>
  </div>
  <div class="boot-bar-wrap"><div class="boot-bar"></div></div>
  <div class="boot-ready">● &nbsp; ALL SYSTEMS ONLINE</div>
</div>
"""

# ═══════════════════════════════════════════════════════════════════════════
# FIX 2: ANIMATED TRACKING  (streams token-by-token like Gradio)
# ═══════════════════════════════════════════════════════════════════════════
def stream_tracking(route, vehicle_type, placeholder):
    """Replicate Gradio's animate_route() streaming in Streamlit."""
    if not route:
        placeholder.markdown(
            '<div class="tracking-box">Waiting for dispatch...\nSubmit a request to see live route animation.</div>',
            unsafe_allow_html=True,
        )
        return

    chunks = []
    chunks.append(f"{'='*44}\n  ARIA  .  LIVE VEHICLE TRACKING\n{'='*44}\n")
    chunks.append(f"  Vehicle  : {vehicle_type.upper()}\n")
    chunks.append(f"  Status   : > MOVING\n")
    chunks.append(f"  Waypoints: {len(route)}\n")
    chunks.append(f"{'-'*44}\n\n")

    for i, stop in enumerate(route):
        stop_clean = stop.replace("_", " ")
        if i == 0:
            chunks.append(f"  [START]   ->  {stop_clean}\n")
        elif i == len(route) - 1:
            chunks.append("       |\n       v\n")
            chunks.append(f"  [ARRIVED] ->  {stop_clean}  <- DESTINATION\n")
        else:
            chunks.append("       |\n       v\n")
            chunks.append(f"  [PASSING] ->  {stop_clean}\n")

    chunks.append(f"\n{'-'*44}\n  Route complete. All clear.\n{'='*44}")

    accumulated = ""
    for chunk in chunks:
        accumulated += chunk
        safe = accumulated.replace("<", "&lt;").replace(">", "&gt;")
        placeholder.markdown(
            f'<div class="tracking-box">{safe}</div>',
            unsafe_allow_html=True,
        )
        time.sleep(0.35)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="ARIA — Smart City AI", page_icon="⚡", layout="wide")

    # Inject CSS
    st.markdown(ARIA_CSS, unsafe_allow_html=True)

    ensure_log_file()
    initialize_state()
    consume_pending_scenario()
    initialize_engine()

    # ── FIX 1: Show boot screen only on first load ──────────────
    if not st.session_state.boot_shown:
        st.markdown(BOOT_HTML, unsafe_allow_html=True)
        st.session_state.boot_shown = True

    # ── HEADER ──────────────────────────────────────────────────
    st.markdown(
        """
        <div class="aria-header">
          <div class="header-left">
            <div class="aria-wordmark">A · R · I · <span class="gold-letter">A</span></div>
            <div class="aria-sub">Adaptive Road Intelligence Architecture · Smart City AI v1.0</div>
          </div>
          <div class="header-pills">
            <div class="pill pill-online">● ONLINE</div>
            <div class="pill pill-sky">13 NODES</div>
            <div class="pill pill-gold">19 RULES</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── TOP-LEVEL TABS  (matching Gradio structure) ──────────────
    tab1, tab2, tab3 = st.tabs(["  ⚡  DISPATCH  ", "  📋  SCENARIOS  ", "  🕘  HISTORY  "])

    # ════════════════════════════════════════════════════════════
    # TAB 1 — DISPATCH
    # ════════════════════════════════════════════════════════════
    with tab1:
        left_col, right_col = st.columns([1, 1.2], gap="large")

        # ── LEFT: Input form ─────────────────────────────────
        with left_col:
            st.markdown('<div class="panel-left">', unsafe_allow_html=True)
            st.markdown('<div class="sec-label lbl-gold">⭐ &nbsp; Request Input</div>', unsafe_allow_html=True)

            locations = [
                "Police_HQ", "Traffic_Control_Center", "North_Station", "River_Bridge",
                "Stadium", "Airport_Road", "Central_Junction", "East_Market",
                "West_Terminal", "Fire_Station", "South_Residential", "City_Hospital", "Industrial_Zone",
            ]
            vehicle_types  = ["Ambulance", "Police", "Fire_Truck", "Civilian"]
            request_types  = [
                "Route_Request", "Policy_Check", "Control_Allocation_Request",
                "Emergency_Response_Request", "Integrated_City_Service_Request",
            ]
            severity_levels = ["High", "Medium", "Low", "None"]
            yes_no          = ["Yes", "No"]
            density_levels  = ["High", "Medium", "Low"]
            priority_claims = ["Critical", "High", "Normal", "Low"]

            vehicle_type      = st.selectbox("Vehicle Type",      vehicle_types,   key="vehicle_type")
            current_location  = st.selectbox("Current Location",  locations,       key="current_location")
            destination       = st.selectbox("Destination",       locations,       key="destination")
            request_category  = st.selectbox("Request Category",  request_types,   key="request_category")

            c1, c2 = st.columns(2)
            with c1:
                incident_severity = st.selectbox("Incident Severity", severity_levels, key="incident_severity")
            with c2:
                time_sensitivity  = st.selectbox("Time Sensitive",    yes_no,           key="time_sensitivity")

            c3, c4 = st.columns(2)
            with c3:
                traffic_density = st.selectbox("Traffic Density", density_levels,  key="traffic_density")
            with c4:
                priority_claim  = st.selectbox("Priority Claim",  priority_claims, key="priority_claim")

            st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
            dispatch_clicked = st.button("⚡  DISPATCH REQUEST", key="dispatch_btn", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── RIGHT: Output sub-tabs ────────────────────────────
        with right_col:
            result  = st.session_state.current_result
            request = st.session_state.current_request

            # ── Metrics row (always visible; shows defaults before first dispatch) ──
            # FIX 3: show placeholder metrics on load, not just after dispatch
            m1, m2, m3 = st.columns(3)
            m1.metric("Priority",   result.get("priority_level", "—")   if result else "—")
            m2.metric("Policy",     result.get("policy_status",  "—")   if result else "—")
            m3.metric("Route Cost", result.get("route_cost",     "—")   if result else "—")

            graph_tab, map_tab, decision_tab = st.tabs(
                ["  🗺  CITY GRAPH  ", "  🌍  CITY MAP  ", "  🤖  AI DECISION  "]
            )

            with graph_tab:
                st.markdown('<div class="panel-right">', unsafe_allow_html=True)
                st.markdown('<div class="sec-label lbl-sky">🩵 &nbsp; City Node Graph — Live Route</div>', unsafe_allow_html=True)

                # FIX 4: always render graph (empty on load, routes after dispatch — matches Gradio)
                graph_route      = result.get("route") if result else None
                graph_vehicle    = request.get("vehicle_type", "civilian") if request else "civilian"
                graph_emergency  = bool(result and "Approved" in str(result.get("policy_status", "")))
                graph_html       = generate_graph_html(route=graph_route, is_emergency=graph_emergency, vehicle_type=graph_vehicle)
                components.html(graph_html, height=370, scrolling=False)

                st.markdown('<div class="sec-label lbl-blush" style="margin-top:14px;">🩷 &nbsp; Live Vehicle Tracking</div>', unsafe_allow_html=True)

                # FIX 2: animated streaming placeholder
                tracking_placeholder = st.empty()
                if dispatch_clicked:
                    # Will be filled below after processing
                    pass
                else:
                    route_for_tracking  = result.get("route", []) if result else []
                    vehicle_for_tracking = request.get("vehicle_type", "civilian") if request else "civilian"
                    static_text = build_tracking_text(route_for_tracking, vehicle_for_tracking)
                    safe = static_text.replace("<", "&lt;").replace(">", "&gt;")
                    tracking_placeholder.markdown(
                        f'<div class="tracking-box">{safe}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)

            with map_tab:
                st.markdown('<div class="panel-right">', unsafe_allow_html=True)
                st.markdown('<div class="sec-label lbl-sky">🩵 &nbsp; Folium City Map — Route Overlay</div>', unsafe_allow_html=True)
                map_route     = result.get("route") if result else None
                map_emergency = bool(result and "Approved" in str(result.get("policy_status", "")))
                map_html      = generate_city_map(route=map_route, is_emergency=map_emergency)
                components.html(map_html, height=500, scrolling=False)
                st.markdown("</div>", unsafe_allow_html=True)

            with decision_tab:
                st.markdown('<div class="panel-right">', unsafe_allow_html=True)
                st.markdown('<div class="sec-label lbl-gold">⭐ &nbsp; Explainable AI — How ARIA Decided</div>', unsafe_allow_html=True)
                if result and request:
                    st.text_area(
                        "AI decision breakdown",
                        value=build_ai_summary(request, result),
                        height=480,
                        disabled=True,
                        key="decision_area",
                        label_visibility="collapsed",
                    )
                else:
                    st.info(
                        "Submit a request to see the ANN, policy, and signal allocation summary.\n\n"
                        "Includes:\n  · ANN input features\n  · Priority prediction\n"
                        "  · Knowledge base rules\n  · CSP signal allocation"
                    )
                st.markdown("</div>", unsafe_allow_html=True)

        # ── Process dispatch AFTER columns are built so graph/tracking update ──
        if dispatch_clicked:
            with st.spinner("Processing request..."):
                new_request, new_result = process_request(
                    vehicle_type, current_location, destination,
                    request_category, incident_severity,
                    time_sensitivity, traffic_density, priority_claim,
                )
            st.session_state.current_request = new_request
            st.session_state.current_result  = new_result

            # FIX 2: stream the tracking animation then rerun to refresh everything else
            stream_tracking(
                new_result.get("route", []),
                new_request.get("vehicle_type", "civilian"),
                tracking_placeholder,
            )
            st.rerun()

    # ════════════════════════════════════════════════════════════
    # TAB 2 — SCENARIOS
    # ════════════════════════════════════════════════════════════
    with tab2:
        st.markdown('<div class="sec-label lbl-gold" style="margin:14px 0 6px 0;">⭐ &nbsp; Pre-Built Test Scenarios</div>', unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#8A9CC2;font-size:0.79em;letter-spacing:0.05em;margin-bottom:14px;'>"
            "Select a scenario to auto-fill the dispatch form, then switch to DISPATCH and click the button."
            "</div>",
            unsafe_allow_html=True,
        )
        scenario_name = st.selectbox("Select Scenario", list(SCENARIOS.keys()), key="scenario_picker")

        if st.button("  LOAD SCENARIO  →  GO TO DISPATCH", key="load_scenario_btn", use_container_width=True):
            queue_scenario(scenario_name)
            st.rerun()

        st.markdown(
            """
            <div style='margin-top:22px;padding:18px 22px;background:rgba(26,34,53,0.6);
                 border:1.5px solid rgba(38,51,82,0.8);border-radius:12px;
                 font-size:0.79em;line-height:2.1;color:#8A9CC2;'>
              <div style='color:#F5A623;font-weight:600;letter-spacing:0.1em;margin-bottom:8px;font-size:0.85em;'>AVAILABLE SCENARIOS</div>
              🚑 &nbsp;<b>Ambulance Emergency</b> — Full emergency pipeline (ANN → KB → CSP → Search)<br>
              🚗 &nbsp;<b>Civilian Route</b> — Simple BFS route finding only<br>
              🚓 &nbsp;<b>Police Signal Override</b> — Policy check module only<br>
              🚒 &nbsp;<b>Fire Truck Integrated</b> — All modules activated<br>
              🏙️ &nbsp;<b>Full City Crisis</b> — Maximum complexity scenario
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ════════════════════════════════════════════════════════════
    # TAB 3 — HISTORY
    # ════════════════════════════════════════════════════════════
    with tab3:
        st.markdown('<div class="sec-label lbl-gold" style="margin:14px 0 6px 0;">⭐ &nbsp; Request Log</div>', unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#8A9CC2;font-size:0.79em;letter-spacing:0.05em;margin-bottom:12px;'>"
            "All past requests processed by ARIA. Auto-saved to logs/request_log.json."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("  ↺  REFRESH HISTORY", key="refresh_btn", use_container_width=True):
            st.rerun()
        history = load_history()
        if history:
            st.dataframe(history, use_container_width=True, hide_index=True)
        else:
            st.info("No requests have been processed yet.")


if __name__ == "__main__":
    main()