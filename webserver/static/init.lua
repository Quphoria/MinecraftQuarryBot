local url = "http://mc.quphoria.co.uk:7777/static/"

print("Starting program, hold Ctrl+T to cancel")
os.sleep(2)

-- os.sleep(5)

-- wipe computer label
-- os.setComputerLabel()

while true do
    if turtle then
        shell.run("wget "..url.."main.lua main.lua")
    else
        shell.run("wget "..url.."waypoint.lua main.lua")
    end
    shell.run("main.lua")
    shell.run("rm main.lua")
    -- break
    os.sleep(10) -- 10 seconds wait to prevent spamming
end
