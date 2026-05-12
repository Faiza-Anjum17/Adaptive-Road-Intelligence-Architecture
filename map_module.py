# ============================================================
# File: map_module.py
# Project: ARIA — Adaptive Road Intelligence Architecture
# Description: Generates interactive Folium city map with
#              route visualization. Blue = normal, Red = emergency.
# ============================================================

import folium
import os

# ── Fake GPS coordinates for each city location ──────────────
# Centered around a fictional city grid
LOCATION_COORDS = {
    "Police_HQ"             : [31.5600, 74.3200],
    "Traffic_Control_Center": [31.5650, 74.3600],
    "North_Station"         : [31.5550, 74.3500],
    "River_Bridge"          : [31.5500, 74.3300],
    "Stadium"               : [31.5400, 74.3100],
    "Airport_Road"          : [31.5250, 74.3050],
    "Central_Junction"      : [31.5450, 74.3450],
    "East_Market"           : [31.5420, 74.3350],
    "West_Terminal"         : [31.5430, 74.3550],
    "Fire_Station"          : [31.5480, 74.3650],
    "South_Residential"     : [31.5300, 74.3400],
    "City_Hospital"         : [31.5350, 74.3300],
    "Industrial_Zone"       : [31.5380, 74.3700],
}

# ── Location type icons and colors ───────────────────────────
LOCATION_STYLE = {
    "Police_HQ"             : ("blue",   "shield"),
    "Traffic_Control_Center": ("gray",   "signal"),
    "North_Station"         : ("gray",   "train"),
    "River_Bridge"          : ("cadetblue", "road"),
    "Stadium"               : ("purple", "star"),
    "Airport_Road"          : ("darkblue", "plane"),
    "Central_Junction"      : ("orange", "random"),
    "East_Market"           : ("green",  "shopping-cart"),
    "West_Terminal"         : ("gray",   "bus"),
    "Fire_Station"          : ("red",    "fire"),
    "South_Residential"     : ("lightgreen", "home"),
    "City_Hospital"         : ("red",    "plus-sign"),
    "Industrial_Zone"       : ("darkred",  "wrench"),
}


def generate_city_map(route=None, is_emergency=False):
    """
    Generates an interactive Folium map of the city.
    If a route is provided, draws it as a colored line.

    Args:
        route (list): List of location name strings
        is_emergency (bool): True = red route, False = blue route

    Returns:
        str: HTML string of the map to embed in Gradio
    """
    # Center map on Central_Junction
    city_map = folium.Map(
        location=[31.5450, 74.3450],
        zoom_start=14,
        tiles="CartoDB dark_matter"  # dark map tiles — matches purple theme
    )

    # ── Plot all 13 locations as markers ─────────────────────
    for name, coords in LOCATION_COORDS.items():
        color, icon = LOCATION_STYLE.get(name, ("gray", "info-sign"))
        folium.Marker(
            location=coords,
            popup=folium.Popup(f"<b>{name.replace('_', ' ')}</b>", max_width=200),
            tooltip=name.replace("_", " "),
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon")
        ).add_to(city_map)

    # ── Draw route if provided ────────────────────────────────
    if route and len(route) >= 2:
        route_coords = []
        for location in route:
            if location in LOCATION_COORDS:
                route_coords.append(LOCATION_COORDS[location])

        if route_coords:
            # Route line color
            line_color  = "#ff2255" if is_emergency else "#bf00ff"
            line_weight = 6 if is_emergency else 4

            folium.PolyLine(
                locations=route_coords,
                color=line_color,
                weight=line_weight,
                opacity=0.9,
                tooltip="Active Route"
            ).add_to(city_map)

            # Start marker (larger circle)
            folium.CircleMarker(
                location=route_coords[0],
                radius=10,
                color="#00ffaa",
                fill=True,
                fill_color="#00ffaa",
                fill_opacity=0.9,
                tooltip="START"
            ).add_to(city_map)

            # End marker (larger circle)
            folium.CircleMarker(
                location=route_coords[-1],
                radius=10,
                color="#ff2255" if is_emergency else "#bf00ff",
                fill=True,
                fill_color="#ff2255" if is_emergency else "#bf00ff",
                fill_opacity=0.9,
                tooltip="DESTINATION"
            ).add_to(city_map)

    # Save and return as HTML string
    # Use OS-independent path so it works on both Windows and Linux
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    map_path = os.path.join(logs_dir, "aria_map.html")
    city_map.save(map_path)
    with open(map_path, "r", encoding="utf-8") as f:
        return f.read()