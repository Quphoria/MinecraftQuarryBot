from dataclasses import dataclass, field
import os, sys, json

from mc import Pos

waypoints = {}

@dataclass
class Waypoint:
    waypoint_id: str
    pos: Pos = field(default_factory=lambda: Pos(0,0,0))
    label: str = field(default_factory=lambda: "NewWaypoint")
    powered: bool = False

    def save(self):
        data = {
            "waypoint_id": self.waypoint_id,
            "pos": self.pos.to_list(),
            "label": self.label,
            "powered": self.powered
        }
        filename = f"waypoint-{self.waypoint_id}.json"
        with open(os.path.join(sys.path[0], "waypoints", filename), "w") as f: 
            json.dump(data, f)

    @staticmethod
    def load(filename) -> 'Waypoint':
        try:
            with open(os.path.join(sys.path[0], "waypoints", filename), "r") as f: 
                data = json.load(f)
            pos = Pos.from_list(data["pos"])
            w = Waypoint(data["waypoint_id"], pos=pos, label=data["label"], powered=data["powered"])
            return w
        except:
            print("Failed to load waypoint:", filename)
            return None

    def update(self, data):
        pos, powered, label = data.split(";", 2)
        self.pos = Pos.from_str(pos)
        self.powered = powered == "true"
        self.label = label
        self.save()

def create_mines():
    # add mines
    for waypoint in waypoints.values():
        if not waypoint.label.startswith("Mine: "):
            continue
        mine_id = waypoint.label.split("Mine: ", 1)[1]
        mine = get_mine(mine_id)
        # we need a global offset to calculate mine coords
        if mine is None:
            mine_points = list(wp.pos for wp in waypoints.values() if wp.label == waypoint.label)
            if len(mine_points) == 2:
                new_mine(mine_id, mine_points[0], mine_points[1])
    

def get_waypoints_by_label(label):
    return list(wp for wp in waypoints.values() if wp.label == label)

def get_waypoint(waypoint_id):
    return waypoints.get(waypoint_id, None)

def update_waypoint(waypoint_id, data):
    w = get_waypoint(waypoint_id)
    new = False
    if w is None:
        w = Waypoint(waypoint_id)
        new = True
    w.update(data)
    if new:
        # add it after updating in case update fails
        waypoints[waypoint_id] = w

    create_mines()
    
def load_waypoints():
    waypoints_dir = os.path.join(sys.path[0], "waypoints")
    for filename in os.listdir(waypoints_dir):
        if filename.startswith("waypoint-") and filename.endswith(".json"):
            waypoint = Waypoint.load(filename)
            if not waypoint:
                continue
            if not waypoint.waypoint_id in waypoints:
                print(f"Waypoint {waypoint.waypoint_id} loaded: {waypoint.label}")
                waypoints[waypoint.waypoint_id] = waypoint


load_waypoints()