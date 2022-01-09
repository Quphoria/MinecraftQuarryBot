
Url = "http://uni.quphoria.co.uk:7777/api/"

Bot_id = "UnknownBotID"
Halt = false
First_empty_slot = 1
Direction = 0 -- assume facing north
VerifiedDirection = false

function Send_data(data, path)
    if path == nil then
        path = "test"
    end
    local h = http.post(Url..path, data, {RobotID = Bot_id})
    if not h then
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

function New_bot_id()
    Bot_id = Send_data("", "uuid")
    if Bot_id == "error" then
        error("Unable to get bot id")
    end

    os.setComputerLabel(Bot_id)
end

function Load_bot_id()
    Bot_id = os.getComputerLabel()
    if Bot_id == "" or not Bot_id then
        New_bot_id()
    end
end

function Save_direction()
    local f = io.open("direction", "w")
    if f then
        f:write(tostring(Direction))
        f:close()
    else
        Send_data("error saving direction", "error")
    end
end

function Load_direction()
    Direction = 0
    local f = io.open("direction", "r")
    if f then
        Direction = tonumber(f:read("*l"))
        f:close()
    else
        print("Unable to find direction file")
    end
    if not Direction then
        Direction = 0 -- default to north if null
    end
    print("Loaded direction: "..Direction)
end

function Get_position()
    local x, y, z = gps.locate()
    if not x then
        Send_data("no gps location", "error")
        return "no gps location"
    end
    return x, y, z
end

function Pos_string()
    local x, y, z = Get_position()
    if x == "no gps location" then return x end
    return x..", "..y..", "..z
end

function Refuel()
    local last_slot = turtle.getSelectedSlot()
    -- select last slot for fuel
    turtle.select(16)
    local last_level = turtle.getFuelLevel()
    while last_level < turtle.getFuelLimit() do
        -- refuel 1 item at a time to prevent wasting fuel
        if not turtle.refuel(1) then
            break
        end
        local level = turtle.getFuelLevel()
        print(level)
        -- fuel level didn't increase stop refueling
        if level <= last_level then break end
        last_level = level
    end
    turtle.select(last_slot)
end

function GetFuel()
    local last_slot = turtle.getSelectedSlot()
    -- select last slot for fuel
    turtle.select(16)
    while turtle.getFuelLevel() < turtle.getFuelLimit() do
        Refuel()
        if turtle.getItemSpace() > 0 then
            if not turtle.suckDown() then
                Send_data("No fuel available", "error")
                break
            end
        end
    end
    turtle.select(last_slot)
end

function Get_energy()
    local energy = math.floor(turtle.getFuelLevel())
    Send_data(tostring(energy), "energy")
end

function Mine_below()
    local block = turtle.inspectDown()
    if not block then
        Send_data("fail: air", "swing")
        return
    end

    local success, status = turtle.digDown("left")
    if success then
        Send_data("ok: "..tostring(status), "swing")
        Has_empty_slots()
    else
        Send_data("fail: "..tostring(status), "swing")
    end
end

function Has_empty_slots()
    for robot_slot=First_empty_slot,15 do -- don't check fuel slot
        local robot_stack = turtle.getItemCount(robot_slot)
        if robot_stack == 0 then
            First_empty_slot = robot_slot
            Send_data("available", "slots")
            return
        end
    end
    Send_data("full", "slots")
end

function Dump_items()
    local last_slot = turtle.getSelectedSlot() -- preserve previous slot
    for robot_slot=1,15 do -- don't transfer fuel slot
        local robot_stack = turtle.getItemCount(robot_slot)
        if robot_stack > 0 then
            turtle.select(robot_slot)
            local success = turtle.dropDown()
            if not success then
                Send_data("dump chest full", "error")
            end
        end
    end
    turtle.select(last_slot)
    First_empty_slot = 1
    Has_empty_slots()
end

function Get_char(s, i)
    return s:sub(i, i)
end

-- rotation codes
-- 0 - north
-- 1 - east
-- 2 - south
-- 3 - west

Rot_table = { -- use [] to eval table key expression
    -- Rot_table [desired direction] [current direction]
    n = {"", "l", "a", "r"},
    e = {"r", "", "l", "a"},
    s = {"a", "r", "", "l"},
    w = {"l", "a", "r", ""}
}

Rot_codes = {
    n = 0,
    e = 1,
    s = 2,
    w = 3
}

function Rotate_to_direction(d)
    local rot_dir = Rot_table[d]
    if not rot_dir then
        Send_data("Unknown direction: "..d, "log")
        return false
    end
    local rotation = rot_dir[Direction+1] -- lua table start at 1
    if rotation == "l" then
        if not turtle.turnLeft() then -- vscode plugin is wrong, method is turnLeft
            Send_data("turning left", "error")
            return false
        end
    elseif rotation == "a" then
        for i=1,2 do
            if not turtle.turnLeft() then
                Send_data("turning around", "error")
                return false
            end
        end
    elseif rotation == "r" then
        if not turtle.turnRight() then -- vscode plugin is wrong, method is turnRight
            Send_data("turning right", "error")
            return false
        end
    end
    Direction = Rot_codes[d]
    Save_direction()
    return true
end

function DetermineDirection(old_x, old_z, x, z)
    local moved_dir = 0
    local dx = x - old_x
    local dz = z - old_z
    if dx > 0 then -- east
        moved_dir = 1
    elseif dz > 0 then -- south
        moved_dir = 2
    elseif dx < 0 then -- west
        moved_dir = 3
    elseif dz < 0 then -- north
        moved_dir = 0
    else
        Send_data("Unable to match direction moved ["..dx..","..dz.."]", "error")
    end
    return moved_dir
end

function Process_step()
    local instruction = Send_data("", "step")
    if instruction ~= "" then
        print("INSTRUCTION: "..instruction)
        -- send_data("INSTRUCTION: "..instruction, "log")
    end
    
    if instruction == "error" or instruction == "halt" then
        Halt = true
        return
    end

    if instruction == "" then return end -- waut for instruction

    local c = Get_char(instruction, 1)
    if c == "m" then -- move
        local d = Get_char(instruction, 2)
        local distance = tonumber(instruction:sub(3)) -- parse remaining as string
        if distance == nil then
            Send_data("invalid distance: "..instruction:sub(3), "error")
        elseif d == "u" then
            for i=1,distance do
                if not turtle.up() then
                    Send_data("moving up "..tostring(i).." ["..instruction.."]", "error")
                    break
                end
            end
        elseif d == "d" then
            for i=1,distance do
                if not turtle.down() then
                    Send_data("moving down "..tostring(i).." ["..instruction.."]", "error")
                    break
                end
            end
        else
            -- check that it was a valid direction before moving
            if Rotate_to_direction(d) then 
                local good = true
                local s_x, s_y, s_z = 0, 0, 0
                -- only verify direction on the first move
                if VerifiedDirection == false then
                    s_x, s_y, s_z = Get_position()
                    if s_x == "no gps location" then good = false end
                end

                if good then
                    if not turtle.forward() then
                        Send_data("moving forward 1 ["..instruction.."]", "error")
                        good = false
                    end
                end

                if good and VerifiedDirection == false then 
                    local x, y, z = Get_position()
                    if x ~= "no gps location" then 
                        -- check new position is correct
                        local moved_dir = DetermineDirection(s_x, s_z, x, z)
                        if moved_dir ~= Direction then
                            Send_data("Turtle moved in an unexpected direction", "error")
                            -- update direction
                            Direction = moved_dir
                            Save_direction()
                            good = false
                        end
                        VerifiedDirection = true
                    end
                end

                if distance > 1 and good then
                    -- continue from i = 2
                    for i=2,distance do
                        if not turtle.forward() then
                            Send_data("moving forward "..tostring(i).." ["..instruction.."]", "error")
                            break
                        end
                    end
                end
            end
        end
    elseif c == "s" then -- status
        Get_energy()
    elseif c == "r" then -- refuel
        Refuel()
    elseif c == "f" then -- get fuel
        GetFuel()
    elseif c == "d" then -- dump
        Dump_items()
    elseif c == "b" then -- break block below
        Mine_below()
    elseif c == "e" then -- empty slots
        Has_empty_slots()
    elseif c == "p" then -- get position
        local pos = Pos_string()
        if pos ~= "no gps location" then
            Send_data(pos, "position")
        end
    elseif c == "z" then -- sleep
        os.sleep(30)
    else
        Send_data("Unknown Instruction: "..c, "log")
    end
end

turtle.select(1) -- select first slot on load

Load_bot_id()
Load_direction()

print("Hello, my name is: "..Bot_id)

Send_data("", "load") -- notify server that we just turned on

Refuel() -- refuel ASAP to get power

while not Halt do
    Process_step()
end

Send_data("", "halt") -- notify server that we just halted

-- send_data(pos_string(), "position")
-- robot.up()
-- send_data(pos_string(), "position")
-- robot.down()
-- send_data(pos_string(), "position")

-- mine_below()
