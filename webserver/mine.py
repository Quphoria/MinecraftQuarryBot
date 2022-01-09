from dataclasses import dataclass, InitVar, field
import os, sys, json

from mc import Pos, mod

mines = {}

@dataclass
class Mine:
    mine_id: str
    p1: InitVar[Pos]
    p2: InitVar[Pos]
    from_save: bool = False
    corner1: Pos = field(init=False) # smaller xz coords
    corner2: Pos = field(init=False) # larger xz coords
    mined: bool = False
    current: Pos = None
    assigned: bool = False
    stopped: bool = False
    complete: bool = False
    pos_x: bool = True
    valid: bool = True

    def __post_init__(self, p1, p2):
        y = max(p1.y, p2.y)
        self.corner1 = Pos(min(p1.x, p2.x), y, min(p1.z, p2.z))
        self.corner2 = Pos(max(p1.x, p2.x), y, max(p1.z, p2.z))
        if not self.from_save:
            # reduce mine size to prevent breaking computers
            self.corner1 += Pos(1, 0, 1)
            self.corner2 -= Pos(1, 0, 1)
        self.valid = self.corner1.x <= self.corner2.x and self.corner1.z <= self.corner2.z

        self.current = Pos(0, y+1, 0) # only y coord matters
        self.next_layer()
        if self.valid and not self.from_save:
            self.save()

    def save(self):
        data = {
            "mine_id": self.mine_id,
            "corner1": self.corner1.to_list(),
            "corner2": self.corner2.to_list(),
            "current": self.current.to_list(),
            "stopped": self.stopped,
            "complete": self.complete,
            "pos_x": self.pos_x,
            "mod": mod
        }
        filename = f"mine-{self.mine_id}.json"
        with open(os.path.join(sys.path[0], "mines", filename), "w") as f: 
            json.dump(data, f)

    @staticmethod
    def load(filename) -> 'Mine':
        try:
            with open(os.path.join(sys.path[0], "mines", filename), "r") as f: 
                data = json.load(f)
            if data.get("mod", None) != mod:
                # this mine is from a diffent mod
                return None

            p1 = Pos.from_list(data["corner1"])
            p2 = Pos.from_list(data["corner2"])
            mine = Mine(data["mine_id"], p1, p2, from_save=True)
            mine.current = Pos.from_list(data["current"])
            mine.stopped = data["stopped"]
            mine.complete = data["complete"]
            mine.pos_x = data["pos_x"]
            return mine
        except:
            print("Failed to load mine:", filename)
            return None

    def status(self):
        data = {
            "id": self.mine_id,
            "complete": self.complete,
            "assigned": self.assigned,
            "stopped": self.stopped,
            "corner1": self.corner1.to_str(),
            "corner2": self.corner2.to_str(),
            "current": self.current.to_str()
        }
        return data
    
    def next_layer(self):
        next_y = self.current.y - 1
        if next_y == 0:
            self.stopped = True # stop when reached 0
        self.current = self.corner1.copy()
        self.current.y = next_y
        self.pos_x = True

    def next_block(self) -> Pos:
        if self.stopped or self.current is None:
            return False, None
        if not self.mined:
            return self.current
        self.mined = False
        if self.pos_x and self.current.x < self.corner2.x:
            self.current.x += 1
        elif not self.pos_x and self.current.x > self.corner1.x:
            self.current.x -= 1
        elif self.current.z < self.corner2.z:
            self.current.z += 1
            self.pos_x = not self.pos_x
        else:
            self.next_layer()
        # work out if move is a big move by its magnitude being more than 1
        self.save()
        return self.current

    def stop(self):
        self.stopped = True
        self.save()

    def mine_response(self, success, status):
        if not success:
            if status == "air":
                self.mined = True
                return
            elif status == "block":
                self.stop()
                return f"Mining stopped as unable to break block at {self.current}"
            elif status == "no tool":
                return status # make robot get new tool
            else:
                self.stop()
                return f"Mining stopped unknown status: {status} at {self.current}"
        else:
            self.mined = True
def get_mine(mine_id) -> Mine:
    return mines.get(mine_id, None)

def new_mine(mine_id, w1, w2):
    if not mine_id in mines:
        mine = Mine(mine_id, w1, w2)
        if mine.valid:
            mines[mine_id] = mine
            print(f"Mine {mine_id} created: {mines[mine_id].corner1} {mines[mine_id].corner2}")
        else:
            print(f"Mine {mine_id} invalid")

def load_mines():
    mine_dir = os.path.join(sys.path[0], "mines")
    for filename in os.listdir(mine_dir):
        if filename.startswith("mine-") and filename.endswith(".json"):
            mine = Mine.load(filename)
            if not mine:
                continue
            if not mine.mine_id in mines:
                print(f"Mine {mine.mine_id} loaded: {mine.corner1} {mine.corner2}")
                mines[mine.mine_id] = mine

def get_free_mine(pos: Pos) -> Mine:
    # bot global position is needed to mine
    if pos is None:
        return None
    try:
        return min((mine for mine in mines.values() if not (mine.assigned or mine.stopped or mine.complete)),
            key=lambda mine: abs(mine.corner1 - pos))
    except (ValueError, StopIteration): # no free mines
        return None

def mines_status():
    data = []
    for mine in mines.values():
        data.append(mine.status())
    return data

def mine_info():
    total = len(mines)
    complete = len(list(mine.mine_id for mine in mines.values() if mine.complete))
    stopped = len(list(mine.mine_id for mine in mines.values() if mine.stopped))
    assigned = len(list(mine.mine_id for mine in mines.values() if mine.assigned))
    return {
        "total": total,
        "complete": complete,
         # I want the stopped count to be only incomplete
        "stopped": stopped-complete,
        "assigned": assigned
    }
    