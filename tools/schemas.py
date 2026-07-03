"""
OpenAI tool schemas — describes each tool so the LLM knows when and how to call it.
Follows the OpenAI function-calling format.
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory_status",
            "description": "Check current stock levels and reorder alerts for a Massy location. Call before reorder or routing recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_id": {"type": "string", "description": "Location ID e.g. WH-POS-001, STR-CHG-001"},
                    "sku_id": {"type": "string", "description": "Optional specific SKU to check"}
                },
                "required": ["location_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_demand_forecast",
            "description": "Run market basket analysis and demand forecasting for a location. Returns forecast, frequently-bought-together rules, and reorder priorities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_id": {"type": "string", "description": "Location ID"},
                    "sku_id": {"type": "string", "description": "Optional SKU for chain prediction"},
                    "days_ahead": {"type": "integer", "description": "Days to forecast ahead, default 7"}
                },
                "required": ["location_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_warehouse",
            "description": "Optimise crane pick sequence using 0-1 knapsack to maximise throughput within weight capacity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "warehouse_id": {"type": "string", "description": "Warehouse ID e.g. WH-POS-001"},
                    "max_weight_kg": {"type": "number", "description": "Crane capacity in kg, default 2000"},
                    "priority_filter": {"type": "string", "description": "high, medium, low, or all"}
                },
                "required": ["warehouse_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_routes",
            "description": "Plan optimal delivery routes across the Caribbean network using VRP. Handles road and inter-island sea freight legs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_location_id": {"type": "string", "description": "Dispatch origin ID"},
                    "destination_ids": {"type": "array", "items": {"type": "string"}, "description": "Delivery destination IDs"},
                    "num_vehicles": {"type": "integer", "description": "Number of vehicles, default 3"}
                },
                "required": ["origin_location_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_sustainability",
            "description": "Calculate carbon emissions and fuel cost in TTD for an operation. Provides sea vs road counterfactual for long distances.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation_type": {"type": "string", "description": "warehouse, road_delivery, or sea_freight"},
                    "distance_km": {"type": "number", "description": "Distance in km"},
                    "weight_kg": {"type": "number", "description": "Cargo weight in kg"},
                    "num_vehicles": {"type": "integer", "description": "Number of vehicles"},
                    "vehicle_type": {"type": "string", "description": "truck, van, cargo_vessel, forklift, or crane"}
                },
                "required": ["operation_type", "weight_kg"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_supply_network",
            "description": "Graph analysis: betweenness centrality to find the single point of failure in the logistics network, and product co-purchase community detection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string", "description": "logistics, copurchase, or both"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_shipping_compliance",
            "description": "Generate a customs declaration: HS code classification, CARICOM duty eligibility, landed cost with VAT and fees, and compliance flags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_island": {"type": "string", "description": "Origin territory e.g. Trinidad"},
                    "destination_island": {"type": "string", "description": "Destination territory e.g. Barbados"},
                    "distance_km": {"type": "number", "description": "Shipment distance in km"},
                    "line_items": {
                        "type": "array",
                        "description": "Items to ship, each with sku_id, quantity, unit_value_ttd",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku_id": {"type": "string"},
                                "quantity": {"type": "integer"},
                                "unit_value_ttd": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    }
]
