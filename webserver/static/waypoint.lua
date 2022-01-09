
Url = "http://uni.quphoria.co.uk:7777/api/"

Name = "UnknownWaypoint"
WaypointID = "UnknownWaypoint"

function Send_data(data, path)
    if path == nil then
        path = "test"
    end
    local h = http.post(Url..path, data, {WaypointID = WaypointID})
    if not h then
        print("HTTP request failed to "..Url..path)
        os.sleep(30)
        error("HTTP request failed to "..Url..path)
    end
    local result = h.readAll()
    local code = h.getResponseCode()
    if code ~= 200 then -- != in lua is ~=
        print("response: "..tostring(code))
        print(result)
        return "error"
    end
    return result
end

function New_name()
    Name = ""
    while Name == "" do
        print("Input waypoint name:")
        Name = read()
    end
    local f = io.open("waypoint", "w")
    if f then
        f:write(Name)
        f:close()
    else
        Send_data("error saving waypoint name", "error")
    end
    error("restarting program")
end

function Load_name()
    Name = ""
    local f = io.open("waypoint", "r")
    if f then
        Name = f:read("*l")
        f:close()
    else
        print("Unable to find waypoint file")
    end
    if not Name or Name == "" then
        New_name()
    end
end

function New_waypoint_id()
    WaypointID = Send_data("", "uuid")
    if WaypointID == "error" then
        error("Unable to get waypoint id")
    end

    os.setComputerLabel(WaypointID)
end

function Load_waypoint_id()
    WaypointID = os.getComputerLabel()
    if Bot_id == "" or not WaypointID then
        New_waypoint_id()
    end
end

function Pos_string()
    local x, y, z = gps.locate()
    if not x then
        Send_data("no gps location", "error")
        return "no gps location"
    end
    return x..", "..y..", "..z
end

function Is_Redstone_Powered()
    local powered = false
    for k,side in pairs(redstone.getSides()) do
        local strength = redstone.getAnalogInput(side)
        if strength >= 15 then -- only powered on max level
            powered = true
            break
        end
    end

    return powered
end

term.clear()
term.setCursorPos(1,1)
print("Hold Ctrl+T to exit")

Load_name()
Load_waypoint_id()
print("Hello, my name is: "..WaypointID)

print("\nWaypoint: "..Name.."\n\n")

local last_status = ""
local i = 0
local pos = Pos_string()
while true do
    if pos == "no gps location" then
        print("No GPS location")
        os.sleep(30)
        error("No GPS location")
    end
    local powered = tostring(Is_Redstone_Powered())
    local s = pos..";"..powered..";"..Name
    -- send status if status changed or 30 seconds have elapsed
    if s ~= last_status or i >= 30 then
        -- update position now
        pos = Pos_string()
        s = pos..";"..powered..";"..Name
        Send_data(s, "waypoint")
        last_status = s
        i = 0
    end
    local x, y = term.getCursorPos()
    term.clearLine()
    print(pos)
    term.clearLine()
    print("Redstone: "..powered)
    term.setCursorPos(x,y)
    os.sleep(1)
    i = i + 1
end