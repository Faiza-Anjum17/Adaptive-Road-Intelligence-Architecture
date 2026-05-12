# ============================================================
# File: main.py
# Description: Simulation of the Smart City AI.
#              This triggers the entire workflow described 
#              in the project manual.
# ============================================================

from modules.preprocessing import validate_and_preprocess
from modules.request_router import route_request
from modules.final_response import display_final_response
from modules.ann_priority import train_priority_models

def main():
    # 0. Initialize the "Brains" (Training the ANN)
    print("Initializing Smart City AI Systems...")
    train_priority_models()

    # 1. The Scenario according to the Ambulance from Central_Junction to City_Hospital
    ambulance_request = {
        "request_id": "EMERGENCY-911",
        "vehicle_type": "ambulance",
        "current_location": "Central_Junction",
        "destination": "City_Hospital",
        "request_category": "Emergency_Response_Request",
        "incident_severity": "High",
        "time_sensitivity": "Yes",
        "traffic_density": "High",
        "priority_claim": "Critical"
    }

    # 2. Input & Preprocessing
    processed_req = validate_and_preprocess(ambulance_request)

    if processed_req:
        # 3. Request Router + ANN + KB + CSP + Search
        final_req = route_request(processed_req)

        # 4. Final Response Layer
        display_final_response(final_req)
    else:
        print("Initial validation failed. Request dropped.")

if __name__ == "__main__":
    main()