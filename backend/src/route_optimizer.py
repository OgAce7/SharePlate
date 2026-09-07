from __future__ import annotations
import math
from dataclasses import dataclass, field
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

KG_TO_MEAL_EQUIVALENT = 1.5  
AVG_SPEED_KMPH = 25.0  
SERVICE_TIME_MIN = 8  

@dataclass
class Truck:
    vehicle_id: str
    capacity_units: float = 250.0
    shift_start_min: int = 0
    shift_end_min: int = 600  

@dataclass
class RouteStop:
    node_type: str  
    donation_id: str | None
    ngo_id: str | None
    name: str
    latitude: float
    longitude: float
    arrival_min: int
    load_after_stop: float

@dataclass
class VehicleRoute:
    vehicle_id: str
    stops: list[RouteStop] = field(default_factory=list)
    total_distance_km: float = 0.0
    total_load: float = 0.0

def default_fleet(num_trucks: int = 6, capacity_units: float = 250.0, shift_minutes: int = 600) -> list[Truck]:
    return [
        Truck(vehicle_id=f"TRUCK{i+1:02d}", capacity_units=capacity_units,
              shift_start_min=0, shift_end_min=shift_minutes)
        for i in range(num_trucks)
    ]

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def build_distance_time_matrix(nodes: list[dict]) -> tuple[list[list[float]], list[list[int]]]:
    n = len(nodes)
    dist = [[0.0] * n for _ in range(n)]
    time = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = haversine_km(
                nodes[i]["latitude"], nodes[i]["longitude"],
                nodes[j]["latitude"], nodes[j]["longitude"],
            )
            dist[i][j] = d
            time[i][j] = int(round((d / AVG_SPEED_KMPH) * 60)) + SERVICE_TIME_MIN

    return dist, time

def _load_units(quantity: float, unit: str) -> float:
    if unit == "kg":
        return quantity * KG_TO_MEAL_EQUIVALENT
    return quantity

def optimize_routes(
    matches: pd.DataFrame,
    fleet: list[Truck] | None = None,
    depot_lat: float | None = None,
    depot_lon: float | None = None,
    time_limit_seconds: int = 10,
) -> dict:
    if matches.empty:
        return {"routes": [], "unassigned": []}

    fleet = fleet or default_fleet()

    if depot_lat is None or depot_lon is None:
        all_lats = pd.concat([matches["latitude"], matches["ngo_latitude"]])
        all_lons = pd.concat([matches["longitude"], matches["ngo_longitude"]])
        depot_lat, depot_lon = float(all_lats.mean()), float(all_lons.mean())

    nodes: list[dict] = [{
        "node_type": "depot", "donation_id": None, "ngo_id": None,
        "name": "Depot", "latitude": depot_lat, "longitude": depot_lon,
    }]

    pickup_delivery_pairs: list[tuple[int, int]] = []
    demands: list[float] = [0.0]  
    pickup_deadline_min: dict[int, int] = {}

    for _, row in matches.iterrows():
        load = _load_units(row["quantity"], row["unit"])
        pickup_idx = len(nodes)
        nodes.append({
            "node_type": "pickup", "donation_id": row["donation_id"], "ngo_id": row["ngo_id"],
            "name": f"Pickup {row['donation_id']}", "latitude": row["latitude"], "longitude": row["longitude"],
        })
        demands.append(load)

        delivery_idx = len(nodes)
        nodes.append({
            "node_type": "delivery", "donation_id": row["donation_id"], "ngo_id": row["ngo_id"],
            "name": f"Deliver to {row.get('ngo_name', row['ngo_id'])}",
            "latitude": row["ngo_latitude"], "longitude": row["ngo_longitude"],
        })
        demands.append(-load)

        pickup_delivery_pairs.append((pickup_idx, delivery_idx))

        deadline = int(round(float(row["hours_until_expiry"]) * 60))
        pickup_deadline_min[pickup_idx] = max(deadline, SERVICE_TIME_MIN)

    dist_matrix, time_matrix = build_distance_time_matrix(nodes)

    num_vehicles = len(fleet)
    depot_index = 0

    manager = pywrapcp.RoutingIndexManager(len(nodes), num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        i, j = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        return int(dist_matrix[i][j] * 1000)  # meters, integer

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def time_callback(from_index, to_index):
        i, j = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        return time_matrix[i][j]

    time_callback_index = routing.RegisterTransitCallback(time_callback)

    horizon = max(t.shift_end_min for t in fleet)
    routing.AddDimension(
        time_callback_index,
        60,       
        horizon,  
        False,    
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")

    for v_idx, truck in enumerate(fleet):
        start_index = routing.Start(v_idx)
        end_index = routing.End(v_idx)
        time_dimension.CumulVar(start_index).SetRange(truck.shift_start_min, truck.shift_start_min)
        time_dimension.CumulVar(end_index).SetRange(truck.shift_start_min, truck.shift_end_min)

    # Apply urgency deadlines
    for node_idx, deadline in pickup_deadline_min.items():
        index = manager.NodeToIndex(node_idx)
        time_dimension.CumulVar(index).SetRange(0, min(deadline, horizon))

    # Capacity dimension
    def demand_callback(from_index):
        return int(demands[manager.IndexToNode(from_index)])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [int(t.capacity_units) for t in fleet],
        True,  # start cumul to zero
        "Capacity",
    )

    # Pickup and delivery constraints
    for pickup_idx, delivery_idx in pickup_delivery_pairs:
        p_index = manager.NodeToIndex(pickup_idx)
        d_index = manager.NodeToIndex(delivery_idx)
        routing.AddPickupAndDelivery(p_index, d_index)
        routing.solver().Add(routing.VehicleVar(p_index) == routing.VehicleVar(d_index))
        routing.solver().Add(time_dimension.CumulVar(p_index) <= time_dimension.CumulVar(d_index))

    penalty = 100_000
    for pickup_idx, delivery_idx in pickup_delivery_pairs:
        routing.AddDisjunction(
            [manager.NodeToIndex(pickup_idx), manager.NodeToIndex(delivery_idx)],
            penalty,
            2,
        )

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.FromSeconds(time_limit_seconds)

    solution = routing.SolveWithParameters(search_params)

    routes: list[VehicleRoute] = []
    unassigned: list[str] = []

    if solution is None:
        return {"routes": [], "unassigned": list(matches["donation_id"])}

    for v_idx, truck in enumerate(fleet):
        index = routing.Start(v_idx)
        route = VehicleRoute(vehicle_id=truck.vehicle_id)
        prev_node = None
        cumulative_dist = 0.0

        while not routing.IsEnd(index):
            node_idx = manager.IndexToNode(index)
            node = nodes[node_idx]
            arrival_min = solution.Value(time_dimension.CumulVar(index))
            load = solution.Value(routing.GetDimensionOrDie("Capacity").CumulVar(index))

            if node_idx != 0:  
                route.stops.append(RouteStop(
                    node_type=node["node_type"],
                    donation_id=node["donation_id"],
                    ngo_id=node["ngo_id"],
                    name=node["name"],
                    latitude=node["latitude"],
                    longitude=node["longitude"],
                    arrival_min=arrival_min,
                    load_after_stop=load,
                ))

            if prev_node is not None:
                cumulative_dist += dist_matrix[prev_node][node_idx]
            prev_node = node_idx

            index = solution.Value(routing.NextVar(index))

        if route.stops:
            route.total_distance_km = round(cumulative_dist, 2)
            route.total_load = route.stops[-1].load_after_stop if route.stops else 0
            routes.append(route)

    assigned_donation_ids = {s.donation_id for r in routes for s in r.stops if s.donation_id}
    all_donation_ids = set(matches["donation_id"])
    unassigned = sorted(all_donation_ids - assigned_donation_ids)

    return {"routes": routes, "unassigned": unassigned}

def routes_to_dict(result: dict) -> dict:
    return {
        "routes": [
            {
                "vehicle_id": r.vehicle_id,
                "total_distance_km": r.total_distance_km,
                "total_load": r.total_load,
                "stops": [
                    {
                        "node_type": s.node_type,
                        "donation_id": s.donation_id,
                        "ngo_id": s.ngo_id,
                        "name": s.name,
                        "latitude": s.latitude,
                        "longitude": s.longitude,
                        "arrival_min": s.arrival_min,
                        "load_after_stop": s.load_after_stop,
                    }
                    for s in r.stops
                ],
            }
            for r in result["routes"]
        ],
        "unassigned_donation_ids": result["unassigned"],
    }