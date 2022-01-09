local internet = require("internet")
local shell = require("shell")
local os = require("os")
local robot = require("robot")
local component = require("component")
local sides = require("sides")
local computer = require("computer")
local io = require("io")

first_empty_slot = 1

inv_size = component.inventory_controller.getInventorySize(sides.bottom)

function has_empty_slots()
    for robot_slot=first_empty_slot,15 do -- don't check fuel slot
        local robot_stack = component.inventory_controller.getStackInInternalSlot(robot_slot)
        if robot_stack == nil then
            first_empty_slot = robot_slot
            return
        end
    end
end

function has_tool()
    local durability, error = robot.durability()
    -- tool exists as it has a durability
    if durability ~= nil then return true end
    -- no tool
    if error == "no tool equipped" then return false end
    -- tool cannot be damaged
    return true
end

function get_tool_above()
    -- get temporary empty slot
    has_empty_slots()
    local temp_slot = first_empty_slot
    robot.select(temp_slot)
    if not component.inventory_controller.suckFromSlot(sides.top, 1, 1) then
        return
    end
    if not component.inventory_controller.equip() then
        return
    end
end

function mine_front()
    local success, status = robot.swing(sides.front)
    if not success then
        if not has_tool() then
            get_tool_above()
        end
    end
end

function dump_items()
    local last_slot = robot.select() -- preserve previous slot
    local done = false
    for robot_slot=1,15 do -- don't transfer fuel slot
        if done then break end
        robot.select(robot_slot)
        for slot=1,inv_size do
            local robot_stack = component.inventory_controller.getStackInInternalSlot()
            -- check items are in robot slot
            if robot_stack == nil then
                -- slots fill up sequentially so we stop when a stack is empty
                -- check that slot was empty before we transfer
                if slot == 1 then 
                    done = true
                end
                break
            end
            local other_stack = component.inventory_controller.getStackInSlot(sides.bottom, slot)
            if other_stack == nil then
                s, msg = component.inventory_controller.dropIntoSlot(sides.bottom, slot)
            end
        end
    end
    robot.select(last_slot)
    first_empty_slot = 1
    has_empty_slots()
end

while true do
    for i=1,5 do
        mine_front()
        dump_items()
    end
    print("Level: "..component.experience.level())
end