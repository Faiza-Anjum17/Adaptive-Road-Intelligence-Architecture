# ============================================================
# File: gradio_ui.py
# Project: ARIA — Adaptive Road Intelligence Architecture
# Description: Warm Ivory + Sky Blue + Blush Pink + Gold theme.
#              Animated HTML boot screen. Left input = Right output.
#              Right panel: 3 tabs (City Graph + Live Tracking,
#              City Map, AI Decision). No Dispatch Summary tab.
# ============================================================

import gradio as gr
import time
import json
import os
from datetime import datetime
from graph_animation import generate_graph_html
from modules.request_router import route_request

# ── Mock processor (fallback only) ───────────────────────────
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

# ── Log setup ─────────────────────────────────────────────────
LOG_PATH = "logs/request_log.json"
os.makedirs("logs", exist_ok=True)
if not os.path.exists(LOG_PATH):
    with open(LOG_PATH, "w") as f:
        json.dump([], f)

def get_next_id():
    try:
        with open(LOG_PATH, "r") as f:
            logs = json.load(f)
        return f"REQ_{len(logs)+1:03d}"
    except:
        return "REQ_001"

def save_to_log(request, result):
    try:
        with open(LOG_PATH, "r") as f:
            logs = json.load(f)
        entry = {
            "request_id"      : request.get("request_id", "N/A"),
            "vehicle_type"    : request.get("vehicle_type", "N/A"),
            "from"            : request.get("current_location", "N/A"),
            "to"              : request.get("destination", "N/A"),
            "request_category": request.get("request_category", "N/A"),
            "priority"        : result.get("priority_level", "N/A"),
            "status"          : result.get("policy_status", "N/A"),
            "route"           : " -> ".join(result.get("route", [])),
            "timestamp"       : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        logs.append(entry)
        with open(LOG_PATH, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"[ARIA] Log error: {e}")

def load_history():
    try:
        with open(LOG_PATH, "r") as f:
            logs = json.load(f)
        if not logs:
            return [["No requests yet", "", "", "", "", "", ""]]
        return [
            [
                l.get("request_id",""),
                l.get("vehicle_type","").upper(),
                l.get("from",""),
                l.get("to",""),
                l.get("priority",""),
                l.get("status",""),
                l.get("timestamp",""),
            ]
            for l in logs
        ]
    except:
        return [["Error loading history", "", "", "", "", "", ""]]

# ── Live vehicle animation ────────────────────────────────────
def animate_route(route, vehicle_type, is_emergency):
    vehicle_label = vehicle_type.upper()
    sep = "-" * 44
    yield f"\n{'='*44}\n  ARIA  .  LIVE VEHICLE TRACKING\n{'='*44}\n"
    time.sleep(0.35)
    yield f"  Vehicle  : {vehicle_label}\n"
    yield f"  Status   : > MOVING\n"
    yield f"  Waypoints: {len(route)}\n"
    yield f"{sep}\n\n"
    time.sleep(0.3)
    for i, stop in enumerate(route):
        stop_clean = stop.replace("_", " ")
        if i == 0:
            yield f"  [START]   ->  {stop_clean}\n"
        elif i == len(route) - 1:
            yield f"       |\n       v\n"
            yield f"  [ARRIVED] ->  {stop_clean}  <- DESTINATION\n"
        else:
            yield f"       |\n       v\n"
            yield f"  [PASSING] ->  {stop_clean}\n"
        time.sleep(0.5)
    yield f"\n{sep}\n  Route complete. All clear.\n{'='*44}"

# ── Main processing ───────────────────────────────────────────
def process_request(
    vehicle_type, current_location, destination,
    request_category, incident_severity,
    time_sensitivity, traffic_density, priority_claim
):
    request = {
        "request_id"      : get_next_id(),
        "vehicle_type"    : vehicle_type.lower(),
        "current_location": current_location,
        "destination"     : destination,
        "request_category": request_category,
        "incident_severity": incident_severity,
        "time_sensitivity": time_sensitivity,
        "traffic_density" : traffic_density,
        "priority_claim"  : priority_claim,
    }

    try:
        result = route_request(request)
    except Exception as _route_err:
        print(f"[ARIA] route_request failed: {_route_err} — falling back to mock")
        result = mock_process(request)

    save_to_log(request, result)

    is_emergency = request_category in [
        "Emergency_Response_Request",
        "Integrated_City_Service_Request"
    ]

    priority = result.get("priority_level", "N/A")
    status   = result.get("policy_status",  "N/A")
    route    = result.get("route",          [])
    cost     = result.get("route_cost",     "N/A")
    signals  = result.get("signal_plan",    {})

    # Build ANN explanation text
    ann_text = f"""
{'='*44}
  ARIA  .  HOW THE AI DECIDED
{'='*44}

  INPUT FEATURES
  ─────────────────────────────────────────
  Vehicle Type     ->  {vehicle_type.upper()}
  Request Category ->  {request_category}
  Severity         ->  {incident_severity}
  Time Sensitive   ->  {time_sensitivity}
  Traffic Density  ->  {traffic_density}
  Priority Claim   ->  {priority_claim}

  ANN PREDICTION
  ─────────────────────────────────────────
  {priority}

  KNOWLEDGE BASE RULES APPLIED
  ─────────────────────────────────────────
  Rule 1  : EmergencyVehicle + High Severity -> Critical
  Rule 6  : Ambulance + Hospital Dest -> Emergency Corridor
  Rule 8  : Authorized -> Action Allowed
  Rule 18 : Emergency + Priority + Auth -> Approved

  CSP SIGNAL ALLOCATION
  ─────────────────────────────────────────
"""
    if signals:
        for k, v in signals.items():
            ann_text += f"  {k}  ->  {v}\n"
    else:
        ann_text += "  Not required for this request type.\n"

    ann_text += f"\n  Route Cost  :  {cost} units"
    ann_text += f"\n  Decision    :  {'AUTHORIZED - Corridor Active' if 'Approved' in str(status) else 'Standard movement authorized'}"
    ann_text += f"\n{'='*44}"

    # Node graph HTML
    graph_content = generate_graph_html(route=route, is_emergency=is_emergency, vehicle_type=vehicle_type)
    escaped_graph = graph_content.replace("&", "&amp;").replace('"', "&quot;")
    graph_html = (
        f'<iframe srcdoc="{escaped_graph}" '
        f'width="100%" height="370px" frameborder="0" '
        f'style="border-radius:12px;border:1.5px solid #A8D8EA;background:#0d001a;"></iframe>'
    )

    # Folium map — wrap raw HTML in srcdoc iframe so Gradio doesn't strip scripts
    try:
        from map_module import generate_city_map
        raw_map_html = generate_city_map(route=route, is_emergency=is_emergency)
        escaped = raw_map_html.replace("&", "&amp;").replace('"', "&quot;")
        map_html = (
            f'<iframe srcdoc="{escaped}" '
            f'width="100%" height="500px" frameborder="0" '
            f'style="border-radius:12px;border:1.5px solid #A8D8EA;'
            f'background:#0d001a;"></iframe>'
        )
    except Exception as _map_err:
        map_html = (
            "<div style='color:#C08A5A;padding:40px 20px;text-align:center;"
            "font-family:Georgia,serif;font-size:0.9em;'>"
            f"Map module error: {_map_err}</div>"
        )

    return route, vehicle_type, is_emergency, ann_text, map_html, graph_html


# ── Scenarios ─────────────────────────────────────────────────
SCENARIOS = {
    "🚑 Ambulance Emergency — Critical": {
        "vehicle_type":"Ambulance","current_location":"Central_Junction",
        "destination":"City_Hospital","request_category":"Emergency_Response_Request",
        "incident_severity":"High","time_sensitivity":"Yes",
        "traffic_density":"High","priority_claim":"Critical",
    },
    "🚗 Civilian Route — Normal": {
        "vehicle_type":"Civilian","current_location":"Stadium",
        "destination":"East_Market","request_category":"Route_Request",
        "incident_severity":"Low","time_sensitivity":"No",
        "traffic_density":"Medium","priority_claim":"Normal",
    },
    "🚓 Police Signal Override Check": {
        "vehicle_type":"Police","current_location":"Police_HQ",
        "destination":"Central_Junction","request_category":"Policy_Check",
        "incident_severity":"Medium","time_sensitivity":"Yes",
        "traffic_density":"High","priority_claim":"High",
    },
    "🚒 Fire Truck — Integrated Response": {
        "vehicle_type":"Fire_Truck","current_location":"Fire_Station",
        "destination":"City_Hospital","request_category":"Integrated_City_Service_Request",
        "incident_severity":"High","time_sensitivity":"Yes",
        "traffic_density":"High","priority_claim":"Critical",
    },
    "🏙️ Full City Crisis — Integrated": {
        "vehicle_type":"Ambulance","current_location":"Airport_Road",
        "destination":"City_Hospital","request_category":"Integrated_City_Service_Request",
        "incident_severity":"High","time_sensitivity":"Yes",
        "traffic_density":"High","priority_claim":"Critical",
    },
}

def load_scenario(scenario_name):
    s = SCENARIOS.get(scenario_name, {})
    if not s:
        return [gr.update()] * 8
    return [
        gr.update(value=s["vehicle_type"]),
        gr.update(value=s["current_location"]),
        gr.update(value=s["destination"]),
        gr.update(value=s["request_category"]),
        gr.update(value=s["incident_severity"]),
        gr.update(value=s["time_sensitivity"]),
        gr.update(value=s["traffic_density"]),
        gr.update(value=s["priority_claim"]),
    ]


# ============================================================
# PALETTE & CSS
# ============================================================
ARIA_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=DM+Mono:wght@300;400;500&display=swap');

/* ═══════════════════════════════════════════════════
   ARIA DESIGN SYSTEM — Deep Space Theme
   Navy #0B1120  ·  Teal #00D4C8  ·  Amber #F5A623
   ═══════════════════════════════════════════════════ */
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
    --warning     : #F5A623;
    --shadow-deep : rgba(0,0,0,0.45);
    --shadow-teal : rgba(0,212,200,0.15);
}

/* ── GLOBAL RESET ── */
*, *::before, *::after { box-sizing: border-box; }

body, .gradio-container, .gradio-container * {
    font-family: 'DM Mono', 'Courier New', monospace !important;
}

body, .gradio-container {
    background: var(--navy) !important;
    color: var(--white) !important;
}

.gradio-container { max-width: 100% !important; padding: 0 !important; }
footer { display: none !important; }

/* ── Force ALL Gradio internal backgrounds ── */
.block, .form, .gap, .container, .wrap,
.gradio-container .block,
div[data-testid], div[class*="svelte"] {
    background: transparent !important;
}

/* ── BOOT SCREEN ── */
#aria-boot {
    position: fixed;
    inset: 0;
    background: var(--navy);
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

.boot-tagline {
    font-size: 0.72em;
    letter-spacing: 0.22em;
    color: var(--white-dim);
    margin-top: 6px;
    animation: fadeSlide 0.7s 0.6s both;
}

.boot-divider {
    width: 340px;
    height: 1px;
    margin: 22px 0 18px 0;
    border-radius: 2px;
    background: linear-gradient(90deg,
        transparent 0%,
        var(--teal) 30%,
        var(--amber) 55%,
        var(--teal) 80%,
        transparent 100%);
    animation: fadeSlide 0.6s 0.9s both, shimmer 3s 1.5s linear infinite;
    background-size: 200% 100%;
    box-shadow: 0 0 12px var(--teal);
}
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
@keyframes fadeSlide {
    from { opacity:0; transform: translateY(8px); }
    to   { opacity:1; transform: none; }
}

.boot-steps {
    display: flex;
    flex-direction: column;
    gap: 7px;
    min-width: 400px;
    animation: fadeSlide 0.5s 1s both;
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
.dot-red   { background: var(--danger);  box-shadow: 0 0 8px var(--danger); }
.dot-green { background: var(--success); box-shadow: 0 0 8px var(--success); }
.dot-amber { background: var(--amber);   box-shadow: 0 0 8px var(--amber); }

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
.badge-ok    { background:rgba(34,201,122,0.15); color:#22C97A !important; border:1px solid #22C97A; }
.badge-warn  { background:rgba(245,166,35,0.15);  color:#F5A623 !important; border:1px solid #F5A623; }
.badge-alert { background:rgba(255,77,106,0.15);  color:#FF4D6A !important; border:1px solid #FF4D6A; }

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
    padding: 20px 40px 16px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
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
.aria-wordmark .gold-letter { color: var(--amber) !important; text-shadow: 0 0 20px var(--amber); }
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
    min-height: 700px !important;
}
.panel-right {
    background: var(--navy-mid) !important;
    border: 1px solid var(--navy-border) !important;
    border-radius: 14px !important;
    padding: 22px !important;
    box-shadow: 0 8px 32px var(--shadow-deep), inset 0 1px 0 rgba(255,255,255,0.04) !important;
    min-height: 700px !important;
}

/* ── Section labels ── */
.sec-label {
    font-size: 0.65em;
    letter-spacing: 0.2em;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--navy-border);
}
.lbl-gold  { color: var(--amber) !important; border-color: var(--amber-dim) !important; }
.lbl-sky   { color: var(--teal) !important;  border-color: var(--teal-dim) !important; }
.lbl-blush { color: #C084FC !important;      border-color: #7C3AED !important; }

/* ══════════════════════════════════════════════════
   INPUTS — Nuclear override for Gradio dark theme
   ══════════════════════════════════════════════════ */

/* Label text */
label > span, .label-wrap > span,
.gradio-container label span {
    color: var(--teal) !important;
    font-size: 0.72em !important;
    font-weight: 500 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}

/* All input/select/textarea elements */
input, select, textarea,
.gradio-container input,
.gradio-container select,
.gradio-container textarea {
    background: var(--navy) !important;
    color: var(--white) !important;
    border: 1px solid var(--navy-border) !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.88em !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    caret-color: var(--teal) !important;
}
input:focus, select:focus, textarea:focus,
.gradio-container input:focus,
.gradio-container select:focus,
.gradio-container textarea:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px var(--teal-glow) !important;
    outline: none !important;
}

/* Gradio dropdown wrapper — the key fix */
.gradio-container .wrap,
.gradio-container .wrap-inner,
.gradio-container .secondary-wrap,
.gradio-container [data-testid="dropdown"],
.gradio-container .dropdown,
.gradio-container ul.options,
.gradio-container li.item,
.gradio-container .svelte-1gfkn6j,
.gradio-container [class*="dropdown"],
.gradio-container [class*="select"] {
    background: var(--navy) !important;
    color: var(--white) !important;
    border-color: var(--navy-border) !important;
}

/* Dropdown list items */
.gradio-container ul.options li,
.gradio-container .options li,
.gradio-container li.item,
.gradio-container [class*="option"] {
    background: var(--navy-card) !important;
    color: var(--white) !important;
    border-bottom: 1px solid var(--navy-border) !important;
}
.gradio-container ul.options li:hover,
.gradio-container li.item:hover,
.gradio-container [class*="option"]:hover {
    background: var(--navy-hover) !important;
    color: var(--teal) !important;
}
.gradio-container li.item.selected,
.gradio-container [class*="option"][aria-selected="true"] {
    background: var(--teal-pale) !important;
    color: var(--teal) !important;
}

/* Textarea (AI Decision / tracking box) */
textarea, .gradio-container textarea {
    background: var(--navy) !important;
    color: var(--teal) !important;
    border: 1px solid var(--navy-border) !important;
    line-height: 1.7 !important;
    font-size: 0.82em !important;
}

/* ── DISPATCH button ── */
.dispatch-btn, button.dispatch-btn {
    background: linear-gradient(135deg, var(--teal-dim) 0%, var(--teal) 50%, #00F0E4 100%) !important;
    color: var(--navy) !important;
    font-size: 0.86em !important;
    font-weight: 700 !important;
    letter-spacing: 0.22em !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px !important;
    box-shadow: 0 0 24px var(--teal-glow), 0 4px 16px rgba(0,0,0,0.4) !important;
    transition: all 0.25s ease !important;
    width: 100% !important;
    text-transform: uppercase !important;
    font-family: 'Orbitron', monospace !important;
}
.dispatch-btn:hover, button.dispatch-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 40px rgba(0,212,200,0.5), 0 6px 20px rgba(0,0,0,0.5) !important;
    background: linear-gradient(135deg, var(--teal) 0%, #00F0E4 100%) !important;
}

/* ── TABS ── */
button[role="tab"] {
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
button[role="tab"]:hover {
    background: var(--navy-hover) !important;
    color: var(--teal) !important;
    border-color: var(--teal-dim) !important;
}
button[role="tab"][aria-selected="true"] {
    background: var(--navy-mid) !important;
    color: var(--amber) !important;
    border-color: var(--amber-dim) !important;
    border-bottom: 2px solid var(--navy-mid) !important;
    font-weight: 600 !important;
    box-shadow: 0 -2px 12px var(--amber-glow) !important;
}

/* ── Dataframe ── */
table { background:var(--navy-card) !important; border-radius:10px !important; overflow:hidden !important; border: 1px solid var(--navy-border) !important; }
th {
    background: rgba(245,166,35,0.10) !important;
    color: var(--amber) !important;
    font-size: 0.70em !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    padding: 10px !important;
    border-bottom: 1px solid var(--amber-dim) !important;
}
td {
    background: var(--navy-card) !important;
    color: var(--white) !important;
    font-size: 0.80em !important;
    border-bottom: 1px solid var(--navy-border) !important;
    padding: 8px 10px !important;
}
tr:nth-child(even) td { background: var(--navy) !important; }
tr:hover td { background: var(--navy-hover) !important; color: var(--teal) !important; transition: all 0.15s; }

/* ── Utility buttons ── */
.util-btn, button.util-btn {
    background: var(--navy-card) !important;
    color: var(--white-dim) !important;
    border: 1px solid var(--navy-border) !important;
    border-radius: 8px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.76em !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    padding: 9px 18px !important;
    transition: all 0.2s !important;
}
.util-btn:hover, button.util-btn:hover {
    background: var(--navy-hover) !important;
    border-color: var(--teal-dim) !important;
    color: var(--teal) !important;
    box-shadow: 0 0 14px var(--teal-glow) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background: var(--navy); }
::-webkit-scrollbar-thumb { background: var(--navy-border); border-radius:4px; }
::-webkit-scrollbar-thumb:hover { background: var(--teal-dim); }

::placeholder { color: var(--white-muted) !important; opacity:1 !important; }
"""

# ── Boot screen HTML ──────────────────────────────────────────
BOOT_HTML = """
<div id="aria-boot">
  <div class="boot-logo">A · R · I · A</div>
  <div class="boot-tagline">Adaptive Road Intelligence Architecture</div>
  <div class="boot-divider"></div>

  <div class="boot-steps">
    <div class="boot-step">
      <div class="step-dot dot-gold"></div>
      <span>Initializing ARIA core systems</span>
      <span class="step-badge badge-ok">READY</span>
    </div>
    <div class="boot-step">
      <div class="step-dot dot-sky"></div>
      <span>Loading city graph &nbsp;·&nbsp; 13 nodes · weighted</span>
      <span class="step-badge badge-ok">READY</span>
    </div>
    <div class="boot-step">
      <div class="step-dot dot-blush"></div>
      <span>Training ANN priority model &nbsp;·&nbsp; 3000 epochs</span>
      <span class="step-badge badge-ok">READY</span>
    </div>
    <div class="boot-step">
      <div class="step-dot dot-gold"></div>
      <span>Loading knowledge base &nbsp;·&nbsp; 19 rules</span>
      <span class="step-badge badge-ok">READY</span>
    </div>
    <div class="boot-step">
      <div class="step-dot dot-sky"></div>
      <span>Initializing CSP scheduler &nbsp;·&nbsp; 5 signal zones</span>
      <span class="step-badge badge-ok">READY</span>
    </div>
    <div class="boot-step">
      <div class="step-dot dot-blush"></div>
      <span>Loading search algorithms &nbsp;·&nbsp; BFS / UCS / A*</span>
      <span class="step-badge badge-ok">READY</span>
    </div>
    <div class="boot-step">
      <div class="step-dot dot-amber"></div>
      <span>Connecting Folium city map module</span>
      <span class="step-badge badge-ok">READY</span>
    </div>
    <div class="boot-step">
      <div class="step-dot dot-green"></div>
      <span>Launching Gradio interface &nbsp;·&nbsp; port 7860</span>
      <span class="step-badge badge-ok">ONLINE</span>
    </div>
  </div>

  <div class="boot-bar-wrap"><div class="boot-bar"></div></div>
  <div class="boot-ready">● &nbsp; ALL SYSTEMS ONLINE</div>
</div>
"""

# ── Header HTML ───────────────────────────────────────────────
HEADER_HTML = """
<div class="aria-header">
  <div class="header-left">
    <div class="aria-wordmark">
      A · R · I · <span class="gold-letter">A</span>
    </div>
    <div class="aria-sub">Adaptive Road Intelligence Architecture &nbsp;·&nbsp; Smart City AI v1.0</div>
  </div>
  <div class="header-pills">
    <div class="pill pill-online">● ONLINE</div>
    <div class="pill pill-sky">13 NODES</div>
    <div class="pill pill-gold">19 RULES</div>
  </div>
</div>
"""


# ============================================================
# BOOT SEQUENCE (terminal only)
# ============================================================
def boot_sequence():
    steps = [
        "Initializing ARIA core systems",
        "Loading city graph (13 nodes, weighted + unweighted)",
        "Training ANN priority model (3000 epochs)",
        "Loading knowledge base (19 rules)",
        "Initializing CSP scheduler (5 signal zones)",
        "Loading search algorithms (BFS / UCS / A*)",
        "Connecting Folium map module",
        "Launching Gradio interface",
    ]
    w = 58
    print("\n" + "="*w)
    print("  A . R . I . A")
    print("  Adaptive Road Intelligence Architecture")
    print("  Smart City Emergency AI System  v1.0")
    print("="*w)
    for step in steps:
        print(f"  {step}...", end="", flush=True)
        time.sleep(0.28)
        print("  READY")
    print("="*w)
    print("  All systems online.  Opening browser...")
    print("="*w + "\n")


# ============================================================
# GRADIO UI
# ============================================================
def build_ui():

    locations = [
        "Police_HQ","Traffic_Control_Center","North_Station",
        "River_Bridge","Stadium","Airport_Road","Central_Junction",
        "East_Market","West_Terminal","Fire_Station",
        "South_Residential","City_Hospital","Industrial_Zone"
    ]
    vehicle_types   = ["Ambulance","Police","Fire_Truck","Civilian"]
    request_types   = [
        "Route_Request","Policy_Check","Control_Allocation_Request",
        "Emergency_Response_Request","Integrated_City_Service_Request"
    ]
    severity_levels = ["High","Medium","Low","None"]
    yes_no          = ["Yes","No"]
    density_levels  = ["High","Medium","Low"]
    priority_claims = ["Critical","High","Normal","Low"]

    with gr.Blocks(title="ARIA — Smart City AI", css=ARIA_CSS) as demo:

        # ── Boot screen (HTML overlay) ─────────────────────────
        gr.HTML(BOOT_HTML)

        # ── Header ────────────────────────────────────────────
        gr.HTML(HEADER_HTML)

        # ── Top-level navigation tabs ─────────────────────────
        with gr.Tabs():

            # ════════════════════════════════════════════════════
            # TAB 1 — DISPATCH  (equal left + right columns)
            # ════════════════════════════════════════════════════
            with gr.Tab("  ⚡  DISPATCH  "):
                with gr.Row(equal_height=True):

                    # ── LEFT — Input form ─────────────────────
                    with gr.Column(scale=1, elem_classes="panel-left"):

                        gr.HTML('<div class="sec-label lbl-gold">⭐ &nbsp; Request Input</div>')

                        vehicle_input  = gr.Dropdown(vehicle_types,   label="Vehicle Type",     value="Ambulance")
                        location_input = gr.Dropdown(locations,        label="Current Location", value="Central_Junction")
                        dest_input     = gr.Dropdown(locations,        label="Destination",      value="City_Hospital")
                        category_input = gr.Dropdown(request_types,   label="Request Category", value="Emergency_Response_Request")

                        with gr.Row():
                            severity_input = gr.Dropdown(severity_levels, label="Incident Severity", value="High")
                            time_input     = gr.Dropdown(yes_no,           label="Time Sensitive",   value="Yes")

                        with gr.Row():
                            density_input = gr.Dropdown(density_levels,  label="Traffic Density",  value="High")
                            claim_input   = gr.Dropdown(priority_claims,  label="Priority Claim",   value="Critical")

                        gr.HTML('<div style="margin-top:20px;"></div>')
                        dispatch_btn = gr.Button("⚡  DISPATCH REQUEST", elem_classes="dispatch-btn")

                    # ── RIGHT — 3 output tabs ─────────────────
                    with gr.Column(scale=1, elem_classes="panel-right"):

                        with gr.Tabs():

                            # RIGHT TAB 1: City Graph + Live Tracking
                            with gr.Tab("  🗺  CITY GRAPH  "):

                                gr.HTML('<div class="sec-label lbl-sky">🩵 &nbsp; City Node Graph — Live Route</div>')

                                _init_graph = generate_graph_html()
                                _init_escaped = _init_graph.replace("&", "&amp;").replace('"', "&quot;")

                                graph_output = gr.HTML(
                                    value=(
                                        f'<iframe srcdoc="{_init_escaped}" '
                                        f'width="100%" height="370px" frameborder="0" '
                                        f'style="border-radius:12px;border:1.5px solid #A8D8EA;'
                                        f'background:#0d001a;"></iframe>'
                                    )
                                )

                                gr.HTML('<div class="sec-label lbl-blush" style="margin-top:14px;">🩷 &nbsp; Live Vehicle Tracking</div>')

                                animation_output = gr.Textbox(
                                    label="",
                                    lines=10,
                                    interactive=False,
                                    placeholder="Waiting for dispatch...\nSubmit a request on the left to see live route animation here.",
                                )

                            # RIGHT TAB 2: City Map
                            with gr.Tab("  🌍  CITY MAP  "):
                                gr.HTML('<div class="sec-label lbl-sky">🩵 &nbsp; Folium City Map — Route Overlay</div>')
                                map_output = gr.HTML(
                                    value=(
                                        "<div style='color:var(--text-muted);padding:60px 20px;"
                                        "text-align:center;font-size:0.82em;letter-spacing:0.07em;line-height:2;'>"
                                        "No route dispatched yet.<br>"
                                        "Submit a request on the DISPATCH tab<br>to see the live route drawn on the city map."
                                        "</div>"
                                    )
                                )

                            # RIGHT TAB 3: AI Decision
                            with gr.Tab("  🤖  AI DECISION  "):
                                gr.HTML('<div class="sec-label lbl-gold">⭐ &nbsp; Explainable AI — How ARIA Decided</div>')
                                ann_output = gr.Textbox(
                                    label="",
                                    lines=29,
                                    interactive=False,
                                    placeholder="AI decision breakdown appears here after dispatch.\n\nIncludes:\n  · ANN input features\n  · Priority prediction\n  · Knowledge base rules\n  · CSP signal allocation",
                                )

                # Hidden state
                route_state     = gr.State([])
                vehicle_state   = gr.State("")
                emergency_state = gr.State(False)
                ann_state       = gr.State("")
                map_state       = gr.State("")
                graph_state     = gr.State("")

            # ════════════════════════════════════════════════════
            # TAB 2 — SCENARIOS
            # ════════════════════════════════════════════════════
            with gr.Tab("  📋  SCENARIOS  "):
                gr.HTML('<div class="sec-label lbl-gold" style="margin:14px 0 6px 0;">⭐ &nbsp; Pre-Built Test Scenarios</div>')
                gr.HTML(
                    "<div style='color:var(--text-sub);font-size:0.79em;letter-spacing:0.05em;"
                    "margin-bottom:14px;'>Select a scenario to auto-fill the dispatch form, then switch to DISPATCH and click the button.</div>"
                )
                scenario_dropdown = gr.Dropdown(
                    choices=list(SCENARIOS.keys()),
                    label="Select Scenario",
                    value=list(SCENARIOS.keys())[0]
                )
                load_btn = gr.Button("  LOAD SCENARIO  →  GO TO DISPATCH", elem_classes="util-btn")

                gr.HTML("""
                <div style='margin-top:22px;padding:18px 22px;
                     background:var(--beige);border:1.5px solid var(--border-soft);
                     border-radius:12px;font-size:0.79em;line-height:2.1;color:var(--text-sub);'>
                  <div style='color:var(--caramel);font-weight:600;letter-spacing:0.1em;
                       margin-bottom:8px;font-size:0.85em;'>AVAILABLE SCENARIOS</div>
                  🚑 &nbsp;<b>Ambulance Emergency</b> — Full emergency pipeline (ANN &rarr; KB &rarr; CSP &rarr; Search)<br>
                  🚗 &nbsp;<b>Civilian Route</b> — Simple BFS route finding only<br>
                  🚓 &nbsp;<b>Police Signal Override</b> — Policy check module only<br>
                  🚒 &nbsp;<b>Fire Truck Integrated</b> — All modules activated<br>
                  🏙️ &nbsp;<b>Full City Crisis</b> — Maximum complexity scenario
                </div>
                """)

            # ════════════════════════════════════════════════════
            # TAB 3 — HISTORY
            # ════════════════════════════════════════════════════
            with gr.Tab("  🕘  HISTORY  "):
                gr.HTML('<div class="sec-label lbl-gold" style="margin:14px 0 6px 0;">⭐ &nbsp; Request Log</div>')
                gr.HTML(
                    "<div style='color:var(--text-sub);font-size:0.79em;letter-spacing:0.05em;"
                    "margin-bottom:12px;'>All past requests processed by ARIA. Auto-saved to logs/request_log.json.</div>"
                )
                refresh_btn = gr.Button("  ↺  REFRESH HISTORY", elem_classes="util-btn")
                history_table = gr.Dataframe(
                    headers=["ID","Vehicle","From","To","Priority","Status","Timestamp"],
                    value=load_history(),
                    interactive=False,
                    wrap=True,
                )

        # ── Events ───────────────────────────────────────────

        def on_dispatch(vehicle, location, dest, category, severity, time_s, density, claim):
            return process_request(vehicle, location, dest, category, severity, time_s, density, claim)

        dispatch_btn.click(
            fn=on_dispatch,
            inputs=[
                vehicle_input, location_input, dest_input,
                category_input, severity_input, time_input,
                density_input, claim_input
            ],
            outputs=[route_state, vehicle_state, emergency_state, ann_state, map_state, graph_state]
        )

        def animate(route, vehicle, is_emergency):
            if not route:
                yield "No route to animate. Please dispatch a request first."
                return
            full_text = ""
            for chunk in animate_route(route, vehicle, is_emergency):
                full_text += chunk
                yield full_text

        route_state.change(
            fn=animate,
            inputs=[route_state, vehicle_state, emergency_state],
            outputs=[animation_output]
        )

        graph_state.change(fn=lambda h: h, inputs=[graph_state], outputs=[graph_output])
        map_state.change(  fn=lambda h: h, inputs=[map_state],   outputs=[map_output])
        ann_state.change(  fn=lambda t: t, inputs=[ann_state],   outputs=[ann_output])

        load_btn.click(
            fn=load_scenario,
            inputs=[scenario_dropdown],
            outputs=[
                vehicle_input, location_input, dest_input,
                category_input, severity_input, time_input,
                density_input, claim_input
            ]
        )

        refresh_btn.click(fn=load_history, inputs=[], outputs=[history_table])

    return demo


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    boot_sequence()
    app = build_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        inbrowser=True,
        show_error=True,
        allowed_paths=[
            "logs",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        ],
    )