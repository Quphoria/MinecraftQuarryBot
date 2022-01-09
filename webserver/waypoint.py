from dataclasses import dataclass, field
import os, sys, json, time

from mc import Pos, mod
from mine import get_mine, new_mine

waypoints = {}

@dataclass
class Waypoint:
    waypoint_id: str
    pos: Pos = field(default_factory=lambda: Pos(0,0,0))
    label: str = field(default_factory=lambda: "NewWaypoint")
    powered: bool = False
    errors: list[str] = field(default_factory=lambda: [])
    # when a waypoint created, make it initially connected at first
    # this is because homes which are paused won't work until they are online
    last_update: int = field(default_factory=lambda: time.time())

    def save(self):
        data = {
            "waypoint_id": self.waypoint_id,
            "pos": self.pos.to_list(),
            "label": self.label,
            "powered": self.powered,
            "errors": self.errors,
            "mod": mod
        }
        filename = f"waypoint-{self.waypoint_id}.json"
        with open(os.path.join(sys.path[0], "waypoints", filename), "w") as f: 
            json.dump(data, f)

    @staticmethod
    def load(filename) -> 'Waypoint':
        try:
            with open(os.path.join(sys.path[0], "waypoints", filename), "r") as f: 
                data = json.load(f)
            if data.get("mod", None) != mod:
                # this waypoint is from a diffent mod
                return None

            pos = Pos.from_list(data["pos"])
            w = Waypoint(data["waypoint_id"], pos=pos,
                label=data["label"], powered=data["powered"],
                errors=data["errors"])
            return w
        except:
            print("Failed to load waypoint:", filename)
            return None

    def is_connected(self):
        # should get an update every 30 seconds
        return time.time() - self.last_update < 60

    def status(self):
        data = {
            "id": self.waypoint_id,
            "label": self.label,
            "connected": self.is_connected(),
            "powered": self.powered,
            "error_num": len(self.errors),
            "errors": self.errors
        }
        if self.pos:
            data["pos"] = self.pos.to_str()
        return data

    def update(self, data):
        pos, powered, label = data.split(";", 2)
        self.pos = Pos.from_str(pos)
        self.powered = powered == "true"
        self.label = label
        self.last_update = time.time()
        self.save()

    def error(self, e):
        print(f"[Waypoint {self.bot_id}] Had an error {e}")
        self.errors.append(e)
        self.save()

    def clear_errors(self):
        self.errors = []
        self.save()

def create_mines():
    # add mines
    labels = []
    for waypoint in waypoints.values():
        if not waypoint.label.startswith("Mine: "):
            continue
        mine_id = waypoint.label.split("Mine: ", 1)[1]
        mine = get_mine(mine_id)
        # we need a global offset to calculate mine coords
        if mine is None:
            if mine_id in labels: # only call this on the 2nd waypoint
                mine_points = list(wp.pos for wp in waypoints.values() if wp.label == waypoint.label)
                if len(mine_points) == 2:
                    new_mine(mine_id, mine_points[0], mine_points[1])
            else:
                labels.append(mine_id)
    

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

def waypoint_status():
    data = []
    for waypoint in waypoints.values():
        data.append(waypoint.status())
    return data

def waypoint_info():
    total = len(waypoints)
    online = len(list(wp.waypoint_id for wp in waypoints.values() if wp.is_connected()))
    errors = len(list(wp.waypoint_id for wp in waypoints.values() if len(wp.errors)))
    return {
        "total": total,
        "online": online,
        "errors": errors
    }