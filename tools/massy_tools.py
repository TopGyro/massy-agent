"""
Massy Agent Tools
-----------------
The 7 supply chain tools, adapted from the Lambda handlers to run locally.
Reads from the same AWS DynamoDB tables via boto3.
"""

import os
import math
import json
import logging
from collections import defaultdict
from itertools import combinations
from decimal import Decimal
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

try:
    import networkx as nx
    from networkx.algorithms.community import greedy_modularity_communities
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

logger = logging.getLogger("massy.tools")

# ─── AWS Setup ────────────────────────────────────────────────────────────────

AWS_REGION      = os.getenv("AWS_REGION", "us-east-1")
PROJECT         = os.getenv("PROJECT_NAME", "massy-agent")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
INVENTORY_TABLE  = f"{PROJECT}-inventory"
ORDERS_TABLE     = f"{PROJECT}-orders"
LOCATIONS_TABLE  = f"{PROJECT}-locations"

# ─── Location Network ─────────────────────────────────────────────────────────

LOCATIONS = {
    "WH-POS-001":  {"name": "Port of Spain Warehouse",    "lat": 10.6549, "lon": -61.5019, "island": "Trinidad"},
    "STR-POS-001": {"name": "Massy Stores Long Circular", "lat": 10.6572, "lon": -61.5209, "island": "Trinidad"},
    "STR-POS-002": {"name": "Massy Stores South Mall",    "lat": 10.2676, "lon": -61.4619, "island": "Trinidad"},
    "STR-SFD-001": {"name": "Massy Stores San Fernando",  "lat": 10.2756, "lon": -61.4637, "island": "Trinidad"},
    "STR-CHG-001": {"name": "Massy Stores Chaguanas",     "lat": 10.5167, "lon": -61.4000, "island": "Trinidad"},
    "STR-SCR-001": {"name": "Massy Stores Scarborough",   "lat": 11.1839, "lon": -60.7329, "island": "Tobago"},
    "WH-BGI-001":  {"name": "Bridgetown Distribution Hub","lat": 13.0969, "lon": -59.6145, "island": "Barbados"},
    "STR-BGI-001": {"name": "Massy Stores Wildey",        "lat": 13.0940, "lon": -59.5960, "island": "Barbados"},
    "STR-GEO-001": {"name": "Massy Stores Georgetown",    "lat": 6.8013,  "lon": -58.1551, "island": "Guyana"},
    "STR-CAS-001": {"name": "Massy Stores Castries",      "lat": 14.0101, "lon": -60.9875, "island": "St. Lucia"},
}

SEA_ROUTES = {
    ("Trinidad", "Tobago"):    {"distance_km": 35,  "hours": 2.5},
    ("Trinidad", "Barbados"):  {"distance_km": 440, "hours": 24},
    ("Trinidad", "Guyana"):    {"distance_km": 560, "hours": 30},
    ("Trinidad", "St. Lucia"): {"distance_km": 480, "hours": 26},
    ("Barbados", "St. Lucia"): {"distance_km": 160, "hours": 9},
}

ROUTE_EDGES = [
    ("WH-POS-001", "STR-POS-001", 8.2, "road"), ("WH-POS-001", "STR-POS-002", 42.1, "road"),
    ("WH-POS-001", "STR-SFD-001", 41.8, "road"), ("WH-POS-001", "STR-CHG-001", 22.4, "road"),
    ("STR-CHG-001", "STR-SFD-001", 30.1, "road"), ("WH-POS-001", "STR-SCR-001", 35.0, "sea"),
    ("WH-POS-001", "WH-BGI-001", 440.0, "sea"), ("WH-BGI-001", "STR-BGI-001", 6.5, "road"),
    ("WH-POS-001", "STR-GEO-001", 560.0, "sea"), ("WH-POS-001", "STR-CAS-001", 480.0, "sea"),
    ("WH-BGI-001", "STR-CAS-001", 160.0, "sea"),
]

EMISSION_FACTORS = {"truck": 0.162, "van": 0.208, "cargo_vessel": 0.016, "forklift": 0.074, "crane": 0.095}
FUEL_CONSUMPTION = {"truck": 0.35, "van": 0.12, "cargo_vessel": 1.80, "forklift": 0.0, "crane": 0.80}
FUEL_COST_TTD = 5.75
CARBON_PRICE_TTD = 120.0

HS_CODES = {
    "RICE-5KG": {"hs_code": "1006.30", "description": "Rice, milled", "duty_pct": 0, "caricom_eligible": True, "flags": []},
    "COOKING-OIL-1L": {"hs_code": "1507.90", "description": "Vegetable oil", "duty_pct": 0, "caricom_eligible": True, "flags": []},
    "FLOUR-2KG": {"hs_code": "1101.00", "description": "Wheat flour", "duty_pct": 5, "caricom_eligible": True, "flags": []},
    "SUGAR-1KG": {"hs_code": "1701.99", "description": "Refined sugar", "duty_pct": 0, "caricom_eligible": True, "flags": []},
    "CHICKEN-WHOLE": {"hs_code": "0207.12", "description": "Frozen whole fowl", "duty_pct": 5, "caricom_eligible": False, "flags": ["phytosanitary_required", "cold_chain"]},
    "BEEF-MINCE": {"hs_code": "0202.30", "description": "Frozen beef", "duty_pct": 5, "caricom_eligible": False, "flags": ["phytosanitary_required", "cold_chain"]},
    "MILK-1L": {"hs_code": "0401.20", "description": "Milk", "duty_pct": 0, "caricom_eligible": False, "flags": ["cold_chain", "food_safety_declaration"]},
    "BEER-6PK": {"hs_code": "2203.00", "description": "Beer from malt", "duty_pct": 60, "caricom_eligible": False, "flags": ["excise_tax_applies"]},
    "COLA-2L": {"hs_code": "2202.10", "description": "Sweetened waters", "duty_pct": 20, "caricom_eligible": True, "flags": []},
    "BREAD-WHITE": {"hs_code": "1905.90", "description": "Bread", "duty_pct": 0, "caricom_eligible": True, "flags": ["short_shelf_life"]},
    "PEAS-TIN": {"hs_code": "2005.40", "description": "Preserved peas", "duty_pct": 5, "caricom_eligible": True, "flags": []},
    "DETERGENT-1L": {"hs_code": "3402.20", "description": "Washing prep", "duty_pct": 20, "caricom_eligible": False, "flags": []},
    "BUTTER-250G": {"hs_code": "0405.10", "description": "Butter", "duty_pct": 20, "caricom_eligible": False, "flags": ["cold_chain"]},
    "WATER-6PK": {"hs_code": "2201.10", "description": "Water", "duty_pct": 5, "caricom_eligible": True, "flags": []},
}
CARICOM = {"Trinidad", "Tobago", "Barbados", "Guyana", "St. Lucia", "Jamaica"}
VAT = {"Trinidad": 12.5, "Barbados": 17.5, "Guyana": 14.0, "St. Lucia": 12.5}

REORDER = {
    "RICE-5KG": 100, "FLOUR-2KG": 80, "COOKING-OIL-1L": 120,
    "CHICKEN-WHOLE": 50, "BREAD-WHITE": 60, "default": 50,
}


def _f(obj):
    return float(obj) if isinstance(obj, Decimal) else obj


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


# ─── Tool 1: Inventory Status ─────────────────────────────────────────────────

def get_inventory_status(location_id="WH-POS-001", sku_id=None):
    table = dynamodb.Table(INVENTORY_TABLE)
    try:
        if sku_id:
            r = table.get_item(Key={"sku_id": sku_id, "location_id": location_id})
            items = [r["Item"]] if "Item" in r else []
        else:
            r = table.query(IndexName="LocationIndex", KeyConditionExpression=Key("location_id").eq(location_id))
            items = r.get("Items", [])
    except Exception as e:
        logger.warning("Inventory query failed: %s", e)
        items = []

    enriched = []
    for item in items:
        units = _f(item.get("units_on_hand", 0))
        daily = _f(item.get("avg_daily_sales", 10))
        threshold = REORDER.get(item.get("sku_id"), REORDER["default"])
        days = units / daily if daily > 0 else 999
        status = "OUT_OF_STOCK" if units <= 0 else "LOW_STOCK" if units < threshold else "CRITICAL" if days < 3 else "OK"
        enriched.append({
            "sku_id": item.get("sku_id"), "name": item.get("name"),
            "units_on_hand": int(units), "days_of_supply": round(days, 1),
            "status": status, "reorder_required": status in ("LOW_STOCK", "OUT_OF_STOCK", "CRITICAL")
        })
    enriched.sort(key=lambda x: (x["status"] != "OUT_OF_STOCK", x["days_of_supply"]))
    alerts = [i for i in enriched if i["reorder_required"]]
    return {
        "location_id": location_id, "total_skus": len(enriched),
        "reorder_list": alerts, "healthy_stock": [i for i in enriched if not i["reorder_required"]][:5]
    }


# ─── Tool 2: Demand Forecast ──────────────────────────────────────────────────

def get_demand_forecast(location_id="WH-POS-001", sku_id=None, days_ahead=7):
    table = dynamodb.Table(ORDERS_TABLE)
    try:
        r = table.query(IndexName="LocationDateIndex", KeyConditionExpression=Key("location_id").eq(location_id),
                        Limit=500, ScanIndexForward=False)
        orders = r.get("Items", [])
    except Exception as e:
        logger.warning("Orders query failed: %s", e)
        orders = []

    transactions = [set(o.get("items", [])) for o in orders if len(o.get("items", [])) > 1]
    sku_counts = defaultdict(int)
    for o in orders:
        for item in o.get("items", []):
            sku_counts[item] += 1

    forecast = sorted([
        {"sku_id": s, "avg_daily_demand": round(c/30, 2), "forecasted_units": round((c/30)*days_ahead),
         "reorder_flag": (c/30)*days_ahead > 50}
        for s, c in sku_counts.items()
    ], key=lambda x: x["avg_daily_demand"], reverse=True)[:10]

    # basket rules
    item_counts = defaultdict(int)
    for t in transactions:
        for i in t:
            item_counts[i] += 1
    frequent = {i for i, c in item_counts.items() if c/max(len(transactions),1) >= 0.05}
    rules = []
    pairs = set()
    for t in transactions:
        pairs.update(combinations(frequent & t, 2))
    for a, b in pairs:
        sab = sum(1 for t in transactions if {a,b} <= t) / max(len(transactions),1)
        sa = sum(1 for t in transactions if a in t) / max(len(transactions),1)
        if sa and sab/sa >= 0.4:
            rules.append({"antecedent": a, "consequent": b, "confidence": round(sab/sa, 3)})
    rules.sort(key=lambda x: x["confidence"], reverse=True)

    return {"location_id": location_id, "days_ahead": days_ahead,
            "demand_forecast": forecast, "basket_rules": rules[:5], "orders_analyzed": len(orders)}


# ─── Tool 3: Warehouse Optimizer (Knapsack) ──────────────────────────────────

def optimize_warehouse(warehouse_id="WH-POS-001", max_weight_kg=2000, priority_filter="all"):
    jobs = [
        {"sku_id": "RICE-5KG", "weight_kg": 450, "priority_value": 95, "units": 90, "position": 1, "priority": "high"},
        {"sku_id": "FLOUR-2KG", "weight_kg": 300, "priority_value": 80, "units": 150, "position": 3, "priority": "high"},
        {"sku_id": "COOKING-OIL-1L", "weight_kg": 220, "priority_value": 75, "units": 220, "position": 5, "priority": "high"},
        {"sku_id": "CHICKEN-WHOLE", "weight_kg": 400, "priority_value": 90, "units": 80, "position": 12, "priority": "high"},
        {"sku_id": "SUGAR-1KG", "weight_kg": 180, "priority_value": 70, "units": 180, "position": 7, "priority": "medium"},
        {"sku_id": "MILK-1L", "weight_kg": 280, "priority_value": 72, "units": 280, "position": 20, "priority": "medium"},
        {"sku_id": "COLA-2L", "weight_kg": 480, "priority_value": 65, "units": 240, "position": 25, "priority": "medium"},
        {"sku_id": "BREAD-WHITE", "weight_kg": 80, "priority_value": 88, "units": 160, "position": 2, "priority": "high"},
        {"sku_id": "BEER-6PK", "weight_kg": 360, "priority_value": 60, "units": 60, "position": 28, "priority": "low"},
        {"sku_id": "DETERGENT-1L", "weight_kg": 150, "priority_value": 55, "units": 150, "position": 35, "priority": "low"},
    ]
    if priority_filter != "all":
        jobs = [j for j in jobs if j["priority"] == priority_filter]

    n = len(jobs)
    W = int(max_weight_kg * 10)
    dp = [[0]*(W+1) for _ in range(n+1)]
    for i in range(1, n+1):
        w_i = int(jobs[i-1]["weight_kg"]*10)
        v_i = jobs[i-1]["priority_value"]
        for w in range(W+1):
            dp[i][w] = dp[i-1][w]
            if w_i <= w:
                dp[i][w] = max(dp[i][w], dp[i-1][w-w_i] + v_i)
    selected, w = [], W
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i-1][w]:
            selected.append(jobs[i-1])
            w -= int(jobs[i-1]["weight_kg"]*10)
    selected.sort(key=lambda x: x["position"])
    total_weight = sum(j["weight_kg"] for j in selected)
    util = round((total_weight/max_weight_kg)*100, 1)
    return {
        "warehouse_id": warehouse_id, "max_crane_capacity_kg": max_weight_kg,
        "jobs_selected": len(selected), "jobs_available": n,
        "total_weight_kg": round(total_weight, 2), "crane_utilization_pct": util,
        "efficiency_rating": "Excellent" if util >= 90 else "Good" if util >= 75 else "Fair",
        "pick_sequence": [{"step": i+1, "sku_id": j["sku_id"], "position": j["position"],
                           "units": j["units"], "weight_kg": j["weight_kg"]} for i, j in enumerate(selected)]
    }


# ─── Tool 4: Route Optimizer (VRP) ────────────────────────────────────────────

def optimize_routes(origin_location_id="WH-POS-001", destination_ids=None, num_vehicles=3, vehicle_capacity_kg=5000):
    dests = destination_ids or ["STR-POS-001", "STR-SFD-001", "STR-CHG-001", "STR-SCR-001"]
    dests = [d for d in dests if d in LOCATIONS] or ["STR-POS-001", "STR-SFD-001", "STR-CHG-001"]

    def route_dist(route):
        return sum(haversine(LOCATIONS.get(route[i], {"lat":10.65,"lon":-61.5})["lat"],
                             LOCATIONS.get(route[i], {"lat":10.65,"lon":-61.5})["lon"],
                             LOCATIONS.get(route[i+1], {"lat":10.65,"lon":-61.5})["lat"],
                             LOCATIONS.get(route[i+1], {"lat":10.65,"lon":-61.5})["lon"])
                   for i in range(len(route)-1))

    unvisited = list(dests)
    route = [origin_location_id]
    current = origin_location_id
    while unvisited:
        cl = LOCATIONS.get(current, {"lat":10.65,"lon":-61.5})
        nxt = min(unvisited, key=lambda d: haversine(cl["lat"], cl["lon"],
                  LOCATIONS.get(d, {"lat":10.65,"lon":-61.5})["lat"], LOCATIONS.get(d, {"lat":10.65,"lon":-61.5})["lon"]))
        route.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    route.append(origin_location_id)

    # 2-opt
    improved = True
    while improved:
        improved = False
        for i in range(1, len(route)-2):
            for j in range(i+1, len(route)-1):
                new = route[:i] + route[i:j+1][::-1] + route[j+1:]
                if route_dist(new) < route_dist(route):
                    route = new
                    improved = True

    legs = []
    total_dist, total_hours, has_sea = 0.0, 0.0, False
    for i in range(len(route)-1):
        a = LOCATIONS.get(route[i], {"lat":10.65,"lon":-61.5,"island":"Trinidad","name":route[i]})
        b = LOCATIONS.get(route[i+1], {"lat":10.65,"lon":-61.5,"island":"Trinidad","name":route[i+1]})
        if a["island"] == b["island"]:
            d = haversine(a["lat"], a["lon"], b["lat"], b["lon"])
            leg = {"type": "road", "distance_km": round(d, 1), "hours": round(d/40, 2)}
        else:
            key = tuple(sorted([a["island"], b["island"]]))
            if key in SEA_ROUTES:
                leg = {"type": "sea", "distance_km": SEA_ROUTES[key]["distance_km"], "hours": SEA_ROUTES[key]["hours"]}
                has_sea = True
            else:
                d = haversine(a["lat"], a["lon"], b["lat"], b["lon"])
                leg = {"type": "sea", "distance_km": round(d, 1), "hours": round(d/18, 2)}
                has_sea = True
        legs.append({"from": a["name"], "to": b["name"], **leg})
        total_dist += leg["distance_km"]
        total_hours += leg["hours"]

    return {
        "origin": LOCATIONS.get(origin_location_id, {}).get("name", origin_location_id),
        "optimized_route": [LOCATIONS.get(s, {}).get("name", s) for s in route],
        "route_legs": legs,
        "total_distance_km": round(total_dist, 1), "estimated_total_hours": round(total_hours, 1),
        "includes_sea_freight": has_sea, "num_vehicles": num_vehicles
    }


# ─── Tool 5: Sustainability ───────────────────────────────────────────────────

def calculate_sustainability(operation_type="road_delivery", distance_km=0, weight_kg=1000, num_vehicles=1, vehicle_type="truck"):
    if vehicle_type not in EMISSION_FACTORS:
        vehicle_type = "truck"
    tonne_km = (weight_kg/1000) * distance_km
    co2 = tonne_km * EMISSION_FACTORS[vehicle_type] * num_vehicles
    fuel_l = FUEL_CONSUMPTION.get(vehicle_type, 0.35) * distance_km * num_vehicles
    fuel_cost = fuel_l * FUEL_COST_TTD
    carbon_cost = (co2/1000) * CARBON_PRICE_TTD

    intensity = co2 / max(tonne_km, 0.001)
    if intensity <= 0.05: rating = "Excellent"
    elif intensity <= 0.12: rating = "Good"
    elif intensity <= 0.20: rating = "Fair"
    else: rating = "Poor"

    cf = None
    if vehicle_type in ("truck", "van") and distance_km > 100:
        cf_co2 = tonne_km * EMISSION_FACTORS["cargo_vessel"] * num_vehicles
        cf = {"alternative": "cargo_vessel", "co2_savings_kg": round(co2-cf_co2, 2),
              "reduction_pct": round(((co2-cf_co2)/co2)*100, 1) if co2 else 0}

    return {
        "operation_type": operation_type, "vehicle_type": vehicle_type,
        "total_co2_kg": round(co2, 2), "fuel_litres": round(fuel_l, 1),
        "fuel_cost_ttd": round(fuel_cost, 2), "carbon_cost_ttd": round(carbon_cost, 2),
        "total_environmental_cost_ttd": round(fuel_cost + carbon_cost, 2),
        "sustainability_rating": rating, "counterfactual_sea_freight": cf
    }


# ─── Tool 6: Graph Analysis ───────────────────────────────────────────────────

def analyze_supply_network(analysis_type="both", force_refresh=False):
    result = {}
    if not NETWORKX_AVAILABLE:
        return {"error": "networkx not available"}

    if analysis_type in ("logistics", "both"):
        G = nx.Graph()
        for a, b, dist, lt in ROUTE_EDGES:
            G.add_edge(a, b, weight=dist)
        bc = nx.betweenness_centrality(G, weight="weight", normalized=True)
        ranked = sorted(bc.items(), key=lambda x: x[1], reverse=True)
        critical = ranked[0]
        Gw = G.copy()
        Gw.remove_node(critical[0])
        comps = list(nx.connected_components(Gw))
        result["logistics_network"] = {
            "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
            "centrality_ranking": [{"location_id": l, "betweenness": round(s, 4)} for l, s in ranked[:5]],
            "critical_node": {"location_id": critical[0], "betweenness": round(critical[1], 4),
                              "interpretation": f"{critical[0]} sits on {round(critical[1]*100,1)}% of all shortest paths"},
            "vulnerability": {"node_removed": critical[0], "resulting_components": len(comps),
                              "component_sizes": [len(c) for c in comps]}
        }

    if analysis_type in ("copurchase", "both"):
        try:
            r = dynamodb.Table(ORDERS_TABLE).scan(Limit=2000)
            orders = r.get("Items", [])
        except Exception:
            orders = []
        G = nx.Graph()
        ew = defaultdict(int)
        for o in orders:
            items = o.get("items", [])
            for i in range(len(items)):
                for j in range(i+1, len(items)):
                    ew[tuple(sorted([items[i], items[j]]))] += 1
        for (a, b), w in ew.items():
            G.add_edge(a, b, weight=w)
        if G.number_of_nodes() > 0:
            communities = list(greedy_modularity_communities(G, weight="weight"))
            dc = nx.degree_centrality(G)
            top = sorted(dc.items(), key=lambda x: x[1], reverse=True)[:5]
            result["copurchase_network"] = {
                "nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "orders_analyzed": len(orders),
                "communities": [{"id": i, "products": sorted(list(c)), "size": len(c)} for i, c in enumerate(communities)],
                "most_connected": [{"sku_id": s, "centrality": round(c, 4)} for s, c in top]
            }
    return result


# ─── Tool 7: Shipping Compliance ──────────────────────────────────────────────

def check_shipping_compliance(origin_location_name="Port of Spain Warehouse", origin_island="Trinidad",
                              destination_location_name="Massy Stores Wildey", destination_island="Barbados",
                              distance_km=440, line_items=None):
    items = line_items or [
        {"sku_id": "RICE-5KG", "quantity": 500, "unit_value_ttd": 5.50},
        {"sku_id": "COOKING-OIL-1L", "quantity": 300, "unit_value_ttd": 8.75},
        {"sku_id": "CHICKEN-WHOLE", "quantity": 100, "unit_value_ttd": 42.00},
    ]
    same_bloc = origin_island in CARICOM and destination_island in CARICOM
    classified, total_value, total_duty, flags = [], 0.0, 0.0, set()
    for it in items:
        ref = HS_CODES.get(it["sku_id"])
        if not ref:
            classified.append({"sku_id": it["sku_id"], "hs_code": "UNCLASSIFIED", "error": "manual classification required"})
            continue
        caricom = ref["caricom_eligible"] and same_bloc
        duty_pct = 0 if caricom else ref["duty_pct"]
        line_val = it["quantity"] * it["unit_value_ttd"]
        duty = line_val * (duty_pct/100)
        classified.append({
            "sku_id": it["sku_id"], "hs_code": ref["hs_code"], "description": ref["description"],
            "quantity": it["quantity"], "line_value_ttd": round(line_val, 2),
            "duty_pct_applied": duty_pct, "duty_amount_ttd": round(duty, 2),
            "caricom_preferential_rate": caricom, "compliance_flags": ref["flags"]
        })
        total_value += line_val
        total_duty += duty
        flags.update(ref["flags"])

    vat_rate = VAT.get(destination_island, 15.0)
    vat_amt = (total_value + total_duty) * (vat_rate/100)
    port = 1200.0
    total_landed = total_value + total_duty + vat_amt + port

    checklist = [{"requirement": "CARICOM Certificate of Origin",
                  "status": "eligible" if same_bloc else "not_applicable"}]
    if "phytosanitary_required" in flags:
        checklist.append({"requirement": "Phytosanitary certificate", "status": "required"})
    if "cold_chain" in flags:
        checklist.append({"requirement": "Cold chain declaration", "status": "required"})
    if "excise_tax_applies" in flags:
        checklist.append({"requirement": "Excise tax filing", "status": "required"})

    return {
        "shipper": origin_location_name, "consignee": destination_location_name,
        "route": f"{origin_island} to {destination_island}", "distance_km": distance_km,
        "line_items": classified,
        "compliance_checklist": checklist,
        "cost_summary": {
            "goods_value_ttd": round(total_value, 2), "import_duty_ttd": round(total_duty, 2),
            "vat_rate_pct": vat_rate, "vat_amount_ttd": round(vat_amt, 2),
            "port_handling_ttd": port, "total_landed_cost_ttd": round(total_landed, 2)
        }
    }


# ─── Tool Registry ────────────────────────────────────────────────────────────

TOOLS = {
    "get_inventory_status": get_inventory_status,
    "get_demand_forecast": get_demand_forecast,
    "optimize_warehouse": optimize_warehouse,
    "optimize_routes": optimize_routes,
    "calculate_sustainability": calculate_sustainability,
    "analyze_supply_network": analyze_supply_network,
    "check_shipping_compliance": check_shipping_compliance,
}
