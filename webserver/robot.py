from dataclasses import dataclass, field
from enum import Enum, auto
import math, re, sys, os, secrets, time, json

from mc import Pos, mod
from waypoint import Waypoint, get_waypoint, update_waypoint, \
    get_waypoints_by_label, load_waypoints, waypoint_status, waypoint_info
from mine import get_mine, new_mine, get_free_mine, \
    load_mines, mines_status, mine_info

robots = {}

low_energy = 10000
refuel_energy = 15000

move_height = 3
move_dist = 30
home_on_init = True

# waypoint are actually the block with the particals, not the actual waypoint
# waypoint format XYZ: x, y, z

words = []
# Load wordlist from https://raw.githubusercontent.com/sapbmw/The-Oxford-3000/master/The_Oxford_3000.txt
# With some words removed, approx 3181 words left
with open(os.path.join(sys.path[0], "words.txt"), "r") as f:
    words = [l.strip() for l in f.readlines()]

def gen_uuid(length=2):
    uuid = ""
    assert length > 0, "Why do you want a 0 word uuid??" # assertion to prevent accidentally security flaws
    for i in range(length):
        uuid += secrets.choice(words) + "-"
    if length > 0:
        uuid = uuid[:-1] # remove trailing -
    return uuid

class Program(Enum):
    Idle = auto()
    Mine = auto()
    Dump = auto()
    Find = auto()
    Refuel = auto()
    Home = auto()
    Initialise = auto()
    Error = auto()
    BreakBlock = auto()

@dataclass
class Robot:
    bot_id: str
    pos: Pos = None
    from_save: bool = False
    energy: int = 0
    current_program: Program = Program.Idle
    next_program: Program = Program.Idle
    find_program: Program = Program.Home
    resume_program: Program = Program.Idle
    steps: list[str] = field(default_factory=lambda: [])
    connected: bool = False
    empty_slots: bool = False
    mine_id: str = None
    last_move_mine: bool = False
    paused_at_home: bool = False
    errors: list[str] = field(default_factory=lambda: [])
    
    def __post_init__(self):
        if not self.from_save:
            self.save()

    def save(self):
        data = {
            "bot_id": self.bot_id,
            "mine_id": self.mine_id,
            "errors": self.errors,
            "mod": mod
        }
        filename = f"bot-{self.bot_id}.json"
        with open(os.path.join(sys.path[0], "bots", filename), "w") as f: 
            json.dump(data, f)

    @staticmethod
    def load(filename) -> 'Robot':
        try:
            with open(os.path.join(sys.path[0], "bots", filename), "r") as f: 
                data = json.load(f)
            
            if data.get("mod", None) != mod:
                # this bot is from a diffent mod
                return None

            bot = Robot(data["bot_id"], mine_id=data["mine_id"],
                errors=data["errors"], from_save=True)
            return bot
        except:
            print("Failed to load bot:", filename)
            return None

    def get_program_name(self):
        if self.current_program == Program.Find:
            return f"{Program.Find.name} [{self.find_program.name}]"
        return self.current_program.name

    def is_idle(self):
        return self.current_program == Program.Idle

    def status(self):
        data = {
            "id": self.bot_id,
            "connected": self.connected,
            "paused": self.paused_at_home,
            "energy": self.energy,
            "program": self.get_program_name(),
            "error_num": len(self.errors),
            "errors": self.errors
        }
        if self.pos:
            data["pos"] = self.pos.to_str()
        if self.mine_id:
            data["mine_id"] = self.mine_id
        return data

    def loaded(self):
        self.current_program = Program.Idle
        self.next_program = Program.Initialise # home robot on load
        self.pos = None # dont assume position
        self.connected = True

    def set_position(self, s):
        pos = Pos.from_str(s)
        if self.pos is None:
            print(f"[{self.bot_id}] is at {pos}")
        self.pos = pos

    def new_mine(self) -> bool:
        # returns True if a mine was loaded
        mine = get_free_mine(self.pos)
        if mine:
            mine.assigned = True
            self.mine_id = mine.mine_id
            self.save()
            return True
        return False

    def get_mine(self):
        if self.mine_id is None:
            return None
        mine = get_mine(self.mine_id)
        if mine is None or mine.stopped:
            self.mine_id = None
            self.save()
            return None
        return mine
     
    def set_energy(self, s):
        self.energy = int(s)
        if self.energy < low_energy and self.current_program != Program.Refuel:
            self.next_program = Program.Find
            self.find_program = Program.Refuel
            self.resume_program = self.current_program

    def set_empty_slots(self, s):
        self.empty_slots = s == "available"

    def split_move(self, move, distance, max_size=move_dist):
        full_moves = distance // max_size
        remaining_move = distance % max_size
        moves = []
        for i in range(full_moves):
            moves.append(move + str(max_size))
        if remaining_move:
            moves.append(move + str(remaining_move))
        return moves

    def move_relative(self, move: Pos, clearance_height=move_height, load_position=True, do_refuel=True):
        steps = []

        # this is a very simple path
        # it goes up by move height
        # goes north/south, then east/west
        # then down to the charger

        # only use clearance height if x + z change by more than 1 block
        if abs(move.x) + abs(move.z) <= 1:
            clearance_height = 0

        if move.y > 0:
            clearance_height += move.y
        steps += self.split_move("mu", clearance_height)

        if move.z > 0:
            steps += self.split_move("ms", abs(move.z))
        else:
            steps += self.split_move("mn", abs(move.z))  # north is negative z
        
        if move.x > 0:
            steps += self.split_move("me", abs(move.x))
        else:
            steps += self.split_move("mw", abs(move.x))  # west is negative x

        steps += self.split_move("md", clearance_height - move.y)
        
        if do_refuel:
            steps.append("r") # refuel after move
        steps.append("s") # get status after move
        if load_position:
            steps.append("p") # get position after move complete
        else:
            self.pos += move # position not updated from move
        self.last_move_mine = False
        return steps

    def move_to_pos(self, pos: Pos, clearance_height=move_height, load_position=True):
        if self.pos is None:
            print(f"[{self.bot_id}] Position unknown")
            self.next_program = Program.Error
            return []
        
        move = pos - self.pos
        return self.move_relative(move, clearance_height=clearance_height, load_position=load_position)

    def get_waypoint(self, label, show_error=True):
        if self.pos is None:
            print(f"[{self.bot_id}] Position unknown")
            return None
        try:
            w = min(get_waypoints_by_label(label), key=lambda w: abs(w.pos - self.pos))
        except ValueError: # empty list
            if show_error:
                print(f"[{self.bot_id}] Unable to find {label} nearby!!!")
            return None
        return w

    def move_to_waypoint(self, label, height_offset=0):
        w = self.get_waypoint(label)
        if w:
            return self.move_to_pos(w.pos + Pos(0, height_offset, 0))
        return None

    def mine_status(self, msg):
        if self.get_mine() is None:
            return
        success, status = msg.split(": ", 1)
        resp = self.get_mine().mine_response(success == "ok", status)
        if resp:
            print(f"[{self.bot_id}] {resp}")

    def mine_block(self):
        if self.pos is None:
            return
        if self.get_mine() is None:
            return
        # robot mines from block above
        next_pos = self.get_mine().next_block() + Pos(0, 1, 0)
        rel_move = next_pos - self.pos
        if self.last_move_mine:
            # no need to use clearance if we are mining
            steps = self.move_relative(rel_move, clearance_height=0, load_position=False, do_refuel=False)
            if self.energy < refuel_energy:
                # do a refuel if we are starting to get low on energy
                steps.append("r") 
        else:
            steps = self.move_relative(rel_move, load_position=False)
        self.last_move_mine = True
        steps.append("b") # break block below robot
        # print(steps)
        return steps

    def home_wp_name(self):
        return "Home: " + self.bot_id

    def load_program_steps(self):
        steps = []
        p = self.current_program
        if p == Program.Refuel:
            steps = self.move_to_waypoint("Fuel", height_offset=2)
            if steps:
                steps.append("f") # start fueling
        elif p == Program.Find:
            # if we are in the middle of a move
            # we need to update the position
            steps = ["p"]
        elif p == Program.Home:
            # attempt to move to personal home
            # resort to shared home if not found
            steps = self.move_to_waypoint(self.home_wp_name(), height_offset=1)
            if steps is None:
                steps = self.move_to_waypoint("Home", height_offset=1)
            if not steps: # home not found or already at home
                p == Program.Idle
        elif p == Program.Dump:
            steps = self.move_to_waypoint("Dump", height_offset=2)
            if steps:
                steps.append("d") # start dumping
                steps.append("e") # update empty slots
        elif p == Program.BreakBlock:
            steps = self.move_to_waypoint("BreakBlock", height_offset=2)
            if steps:
                steps.append("b") # break block below
        elif p == Program.Mine:
            steps = self.mine_block()
        elif p == Program.Error:
            steps = ["halt"] # halt if error
        elif p == Program.Initialise:
            steps = ["r", "s", "p", "e"] # refuel, get status, position and empty slots
        self.steps = steps

    def error(self, e):
        print(f"[{self.bot_id}] Had an error {e}")
        self.errors.append(e)
        self.save()
        self.next_program = Program.Error

    def clear_errors(self):
        self.errors = []
        self.save()

    def get_work(self):
        if self.get_mine() or self.new_mine():
            if self.empty_slots:
                self.next_program = Program.Mine
            else:
                # dump items if no empty slots
                self.next_program = Program.Dump
            return True
        return False

    def next_step(self, retry=False, renew=False):
        if not self.connected:
            # robot asked for step before loading
            return 'halt'
        if self.current_program != self.next_program:
            self.current_program = self.next_program
            print(f"[{self.bot_id}] Changed program to {self.current_program}")
            self.load_program_steps()
        elif renew:
            self.load_program_steps()
        if self.steps:
            step = self.steps.pop(0)
            return step
        
        # calculate next program if not already changed
        p = self.current_program
        if p == self.next_program:
            if p == Program.Mine:
                if self.get_mine() is None or not self.empty_slots:
                    # dump if mine stopped or no more slots
                    self.next_program = Program.Find
                    self.find_program = Program.Dump
                else:
                    # keep mining until interruption
                    # get next block to mine by renewing instructions
                    return self.next_step(retry=True, renew=True)
            elif p == Program.Find:
                self.next_program = self.find_program
            elif p == Program.Refuel:
                # crash as we are not refueling properly
                if self.energy < low_energy:
                    print(f"[{self.bot_id}] failed to refuel!")
                    self.next_program = Program.Error
                else:
                    self.next_program = self.resume_program
            elif p == Program.Initialise:
                self.next_program = Program.Error
                if home_on_init:
                    self.next_program = Program.Home
                else:
                    self.next_program = Program.Dump
            elif p == Program.Home:
                self.next_program = Program.Idle
            elif p == Program.Dump:
                if not self.get_work():
                    # go home if no more work
                    self.next_program = Program.Home
            elif p == Program.Idle:
                if self.pos is None:
                    print(f"[{self.bot_id}] idle, no position")
                    return "z" # sleep
                else:
                    wp = self.get_waypoint(self.home_wp_name(), show_error=False)
                    if wp is None: # fallback to Home if personal home missing
                        wp = self.get_waypoint("Home", show_error=False) 
                    if wp is None: # no home, do nothing
                        return "z" # sleep
                    # home position is 1 block above
                    home_position = wp.pos + Pos(0,1,0)
                    at_home = home_position == self.pos
                    self.paused_at_home = wp and at_home and wp.powered and wp.is_connected()
                    if self.paused_at_home:
                        # if is at home waypoint and wp is powered
                        # stay at home
                        # print(f"[{self.bot_id}] at home")
                        return "z" # sleep
                    elif self.get_work():
                        # next program already set
                        pass
                    elif not at_home: # not at home
                        self.next_program = Program.Home
                    else:
                        return "z" # sleep
            else:
                self.next_program = Program.Idle
        if not retry and self.current_program != self.next_program:
            # get next step if program changed but without creating inf loop
            return self.next_step(retry=True)
        return "" # do nothing

def get_robot(bot_id, create=True) -> Robot:
    if not bot_id in robots and create:
        robots[bot_id] = Robot(bot_id)
    return robots.get(bot_id, None)

def load_bots():
    # load mines before bots
    load_mines()
    bot_dir = os.path.join(sys.path[0], "bots")
    for filename in os.listdir(bot_dir):
        if filename.startswith("bot-") and filename.endswith(".json"):
            bot = Robot.load(filename)
            if not bot:
                continue
            if not bot.bot_id in robots:
                if bot.mine_id:
                    mine = get_mine(bot.mine_id)
                    if mine:
                        mine.assigned = True
                    print(f"Bot {bot.bot_id} loaded, Mine {bot.mine_id}")
                else:
                    print(f"Bot {bot.bot_id} loaded")
                robots[bot.bot_id] = bot

def robot_status():
    data = []
    for bot in robots.values():
        data.append(bot.status())
    return data

def robot_info():
    total = len(robots)
    online = len(list(bot.bot_id for bot in robots.values() if bot.connected))
    active = len(list(bot.bot_id for bot in robots.values() if bot.connected and not  bot.is_idle()))
    paused = len(list(bot.bot_id for bot in robots.values() if bot.connected and bot.paused_at_home))
    errors = len(list(bot.bot_id for bot in robots.values() if len(bot.errors)))
    return {
        "total": total,
        "online": online,
        "active": active,
        "paused": paused,
        "errors": errors
    }

# commands
# m - move 
# - n,e,s,w,u,d (direction)
# - ## number of spaces to move
# s - status [energy]
# r - refuel
# f - get fuel
# d - dump (automatically sends empty slots on finish)
# b - break block below (automatically sends empty slots on block break)
# e - empty slots
# p - get position
# z - sleep
