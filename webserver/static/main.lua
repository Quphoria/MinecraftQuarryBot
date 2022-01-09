local internet = require("internet")
local shell = require("shell")
local os = require("os")
local robot = require("robot")
local component = require("component")
local sides = require("sides")
local computer = require("computer")
local io = require("io")

bot_id = "UnknownBotID"
halt = false
fueling = false
has_generator = true
first_empty_slot = 1

function send_data(data, path)
    if path == nil then
        path = "test"
    end
    local h = http.request("http://uni.quphoria.co.uk:7777/api/"..path, data, {RobotID = bot_id})
    local result = h.readAll()
    local code = h.getResponseCode()
    if code ~= 200 then -- != in lua is ~=
        print("response: "..tostring(code))
        print(result)
        return "error"
    end
    return result
end

function new_bot_id()
    bot_id = send_data("", "uuid")
    if bot_id == "error" then
        print("Unable to get bot id")
        exit()
    end

    os.setComputerLabel(bot_id)
end

function load_bot_id()
    bot_id = os.getComputerLabel()
    if bot_id == "" then
        new_bot_id()
    end
end

function pos_string()
    local x, y, z = component.navigation.getPosition()
    if not x then
        send_data("no gps location", "error")
        return "no gps location"
    end
    return x..", "..y..", "..z
end

function refuel()
    local last_slot = turtle.getSelectedSlot()
    -- select last slot for fuel
    turtle.select(16)
    turtle.refuel()
    turtle.select(last_slot)
end

function get_energy()
    local energy = math.floor(turtle.getFuelLevel())
    send_data(tostring(energy), "energy")
end

function mine_below()
    local block = turle.inspectDown()
    if not block then
        send_data("fail: air", "swing")
        return
    end

    local success, status = robot.swingDown(sides.bottom)
    if success then
        send_data("ok: "..tostring(status), "swing")
        has_empty_slots()
    else
        send_data("fail: "..tostring(status), "swing")
    end
end

function has_empty_slots()
    for robot_slot=first_empty_slot,15 do -- don't check fuel slot
        local robot_stack = turtle.getItemCount(robot_slot)
        if robot_stack == 0 then
            first_empty_slot = robot_slot
            send_data("available", "slots")
            return
        end
    end
    send_data("full", "slots")
end

function dump_items()
    local last_slot = turtle.getSelectedSlot() -- preserve previous slot
    for robot_slot=1,15 do -- don't transfer fuel slot
        local robot_stack = turtle.getItemCount(robot_slot)
        if robot_stack > 0 then
            turtle.select(robot_slot)
            success = turtle.dropDown()
            if not success then
                send_data("dump chest full", "error")
            end
        end
    end
    turtle.select(last_slot)
    first_empty_slot = 1
    has_empty_slots()
end

function get_char(s, i)
    return s:sub(i, i)
end

rot_table = { -- use [] to eval table key expression
    n = {
        [sides.east] = "l",
        [sides.south] = "a",
        [sides.west] = "r",
        [sides.north] = ""
    },
    e = {
        [sides.south] = "l",
        [sides.west] = "a",
        [sides.north] = "r",
        [sides.east] = ""
    },
    s = {
        [sides.west] = "l",
        [sides.north] = "a",
        [sides.east] = "r",
        [sides.south] = ""
    },
    w = {
        [sides.north] = "l",
        [sides.east] = "a",
        [sides.south] = "r",
        [sides.west] = ""
    }
}

function rotate_to_direction(d)
    local facing = component.navigation.getFacing()

    rot_dir = rot_table[d]
    if not rot_dir then
        send_data("Unknown direction: "..d, "log")
        return false
    end
    rotation = rot_dir[facing]
    if rotation == "l" then
        if not robot.turnLeft() then -- vscode plugin is wrong, method is turnLeft
            send_data("turning left", "error")
        end
    elseif rotation == "a" then
        if not robot.turnAround() then
            send_data("turning around", "error")
        end
    elseif rotation == "r" then
        if not robot.turnRight() then -- vscode plugin is wrong, method is turnRight
            send_data("turning right", "error")
        end
    end
    return true
end

function process_step()
    local instruction = send_data("", "step")
    if instruction ~= "" then
        print("INSTRUCTION: "..instruction)
        -- send_data("INSTRUCTION: "..instruction, "log")
    end
    
    if instruction == "error" or instruction == "halt" then
        halt = true
        return
    end

    if instruction == "" then return end -- waut for instruction

    charging = false

    c = get_char(instruction, 1)
    if c == "m" then -- move
        d = get_char(instruction, 2)
        distance = tonumber(instruction:sub(3)) -- parse remaining as string
        if distance == nil then
            send_data("invalid distance: "..s:sub(3), "error")
        elseif d == "u" then
            for i=1,distance do
                if not robot.up() then
                    send_data("moving up "..tostring(i).." ["..instruction.."]", "error")
                    break
                end
            end
        elseif d == "d" then
            for i=1,distance do
                if not robot.down() then
                    send_data("moving down "..tostring(i).." ["..instruction.."]", "error")
                    break
                end
            end
        else
            -- check that it was a valid direction before moving
            if rotate_to_direction(d) then 
                for i=1,distance do
                    if not robot.forward() then
                        send_data("moving forward "..tostring(i).." ["..instruction.."]", "error")
                        break
                    end
                end
            end
        end
    elseif c == "s" then -- status
        get_energy()
    elseif c == "w" then -- waypoints
        find_waypoints()
    elseif c == "r" then -- refuel
        refuel()
    elseif c == "c" then -- charging
        charging = true
    elseif c == "d" then -- dump
        dump_items()
    elseif c == "b" then -- break block below
        mine_below()
    elseif c == "e" then -- empty slots
        has_empty_slots()
    elseif c == "t" then -- get tool
        get_tool()
    else
        send_data("Unknown Instruction: "..c, "log")
    end
end

robot.select(1) -- select first slot on load

load_bot_id()

print("Hello, my name is: "..bot_id)

send_data("", "load") -- notify server that we just turned on

refuel() -- refuel ASAP to get power

while not halt do
    process_step()
    if charging then
        os.sleep(1)
        get_energy()
    end
end

send_data("", "halt") -- notify server that we just halted

-- send_data(pos_string(), "position")
-- robot.up()
-- send_data(pos_string(), "position")
-- robot.down()
-- send_data(pos_string(), "position")

-- mine_below()
