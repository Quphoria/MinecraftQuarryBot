from flask import Flask, request, render_template
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import json

from robot import load_bots, load_mines, load_waypoints, get_robot, \
    gen_uuid, robot_status, mines_status, get_mine, robot_info, \
    mine_info, update_waypoint, get_waypoint, waypoint_status, waypoint_info

filtered_paths = ["/api/position","/api/waypoint","/api/swing",
    "/api/refuel","/api/energy","/api/log","/api/step", "/api/load",
    "/api/halt", "/api/slots", "/api/error",
    "/status", "/favicon.ico", "/api/robots_status.json",
    "/api/mines_status.json", "/api/waypoints_status.json",
    "/api/mine_complete", "/api/mine_continue", "/api/clear_errors"]

class LogFilter(logging.Filter):
    def filter(self, record):  
        # only filter successful requests
        if "/favicon.ico" in record.getMessage():
            # nuke favicon.ico from orbit
            return False
        if "200" in record.getMessage() or "401" in record.getMessage():
            for p in filtered_paths:
                if p in record.getMessage():
                    return False
        return True

log = logging.getLogger('werkzeug')
log.addFilter(LogFilter())

debug = True

app = Flask(__name__, static_folder='static')

auth = HTTPBasicAuth()

users = {}
with open("users.secret", "r") as f:
    for line in f.readlines():
        line = line.strip()
        if line:
            user, pw = line.split("|", 1)
            users[user] = generate_password_hash(pw)

@auth.verify_password
def verify_password(username, password):
    if username in users:
        return check_password_hash(users.get(username), password)
    return False

def gen_resp(status, data):
    response = app.response_class(
        response=data,
        status=status
    )
    return response

def bot_id():
    robot_id = request.headers.get("RobotID", None)
    assert robot_id, "No Bot ID!"
    return robot_id

def waypoint_id():
    wp_id = request.headers.get("WaypointID", None)
    assert wp_id, "No Waypoint ID!"
    return wp_id

def error_sender_id():
    if "RobotID" in request.headers:
        return "bot", bot_id()
    elif "WaypointID" in request.headers:
        return "waypoint", waypoint_id()
    assert False, "No ID!"

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route('/status')
@auth.login_required
def status_page():
    return render_template('status.html',
        robots=robot_info(), mines=mine_info(), waypoints=waypoint_info())

@app.route("/boot.lua")
def boot_lua():
    return app.send_static_file("boot.lua")

@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")

@app.route("/api/test", methods=['POST', 'OPTIONS'])
def test_api():
    print(request.get_data())
    return gen_resp(200, "hello!")

@app.route("/api/load", methods=['POST', 'OPTIONS'])
def load_api():
    try:
        r = get_robot(bot_id())
        r.loaded()
        print(f"[{bot_id()}] Loaded")
        return gen_resp(200, "")
    except Exception as ex:
        raise ex
        return gen_resp(500, "error")

@app.route("/api/halt", methods=['POST', 'OPTIONS'])
def halt_api():
    try:
        r = get_robot(bot_id())
        r.connected = False
        print(f"[{bot_id()}] Halted")
        return gen_resp(200, "")
    except:
        return gen_resp(500, "error")

@app.route("/api/position", methods=['POST', 'OPTIONS'])
def position_api():
    try:
        r = get_robot(bot_id())
        d = request.get_data().decode()
        r.set_position(d)
        # print(f"[{bot_id()}] Position: {d}")
        return gen_resp(200, "")
    except:
        return gen_resp(500, "error")

@app.route("/api/waypoint", methods=['POST', 'OPTIONS'])
def waypoint_api():
    try:
        d = request.get_data().decode()
        if d.startswith("no gps location"):
            print(f"[Waypoint {waypoint_id()}] No GPS Location")
            return gen_resp(400, "") 
        update_waypoint(waypoint_id(), d)
        # print(f"[Waypoint {waypoint_id()}] Waypoint: {d}")
        return gen_resp(200, "")
    except Exception as ex:
        return gen_resp(500, "error")

@app.route("/api/swing", methods=['POST', 'OPTIONS'])
def swing_api():
    try:
        r = get_robot(bot_id())
        d = request.get_data().decode()
        r.mine_status(d)
        # print(f"[{bot_id()}] Swing: {d}")
        return gen_resp(200, "")
    except Exception as ex:
        raise ex
        return gen_resp(500, "error")

@app.route("/api/energy", methods=['POST', 'OPTIONS'])
def energy_api():
    try:
        r = get_robot(bot_id())
        d = request.get_data().decode()
        r.set_energy(d)
        # print(f"[{bot_id()}] Energy: {d}")
        return gen_resp(200, "")
    except:
        return gen_resp(500, "error")

@app.route("/api/slots", methods=['POST', 'OPTIONS'])
def slots_api():
    try:
        r = get_robot(bot_id())
        d = request.get_data().decode()
        r.set_empty_slots(d)
        # print(f"[{bot_id()}] Slots: {d}")
        return gen_resp(200, "")
    except:
        return gen_resp(500, "error")

@app.route("/api/step", methods=['POST', 'OPTIONS'])
def step_api():
    try:
        r = get_robot(bot_id())
        s = r.next_step()
        return gen_resp(200, s)
    except Exception as ex:
        raise ex
        return gen_resp(500, "error")

@app.route("/api/error", methods=['POST', 'OPTIONS'])
def error_api():
    try:
        sender, sender_id = error_sender_id()
        d = request.get_data().decode()
        if sender == "bot":
            r = get_robot(sender_id)
            r.error(d)
            return gen_resp(200, "")
        elif sender == "waypoint":
            w = get_waypoint(sender_id)
            w.error(d)
            return gen_resp(200, "")
        return gen_resp(500, "")
    except Exception as ex:
        raise ex
        return gen_resp(500, "error")

@app.route("/api/log", methods=['POST', 'OPTIONS'])
def log_api():
    print(f"[{bot_id()}]", request.get_data().decode())
    return gen_resp(200, "")

@app.route("/api/uuid", methods=['POST', 'OPTIONS'])
def uuid_api():
    return gen_resp(200, gen_uuid())

@app.route("/api/robots_status.json", methods=['GET'])
@auth.login_required
def robots_status_json_api():
    data = robot_status()

    response = app.response_class(
        response=json.dumps(data),
        status=200,
        mimetype='application/json'
    )
    return response

@app.route("/api/mines_status.json", methods=['GET'])
@auth.login_required
def mines_status_json_api():
    data = mines_status()

    response = app.response_class(
        response=json.dumps(data),
        status=200,
        mimetype='application/json'
    )
    return response

@app.route("/api/waypoints_status.json", methods=['GET'])
@auth.login_required
def waypoints_status_json_api():
    data = waypoint_status()

    response = app.response_class(
        response=json.dumps(data),
        status=200,
        mimetype='application/json'
    )
    return response

@app.route("/api/mine_complete", methods=['POST', 'OPTIONS'])
@auth.login_required
def mine_complete_api():
    if request and request.form:
        mine_id = request.form.get('mine_id')
        m = get_mine(mine_id)
        if m:
            if not m.stopped:
                return gen_resp(500, "mine not stopped")
            m.complete = True
            m.save()
            return gen_resp(200, "")
    return gen_resp(400, "")

@app.route("/api/mine_continue", methods=['POST', 'OPTIONS'])
@auth.login_required
def mine_complete_api():
    if request and request.form:
        mine_id = request.form.get('mine_id')
        m = get_mine(mine_id)
        if m:
            if m.complete:
                return gen_resp(500, "mine complete")
            m.stopped = False
            m.save()
            return gen_resp(200, "")
    return gen_resp(400, "")

@app.route("/api/clear_errors", methods=['POST', 'OPTIONS'])
@auth.login_required
def clear_errors_api():
    if request and request.form:
        target_id = request.form.get('id')
        target_type = request.form.get('type')
        if target_type == "robot":
            r = get_robot(target_id, create=False)
            if r:
                r.clear_errors()
                return gen_resp(200, "")
        elif target_type == "waypoint":
            w = get_waypoint(target_id)
            if w:
                w.clear_errors()
                return gen_resp(200, "")
    return gen_resp(400, "")

load_waypoints()
load_mines()
load_bots()

def main():
    print("Status page at: http://localhost:7777/status")
    app.run(host="0.0.0.0", port=7777, debug=debug, use_reloader=False)

if __name__ == "__main__":
    main()