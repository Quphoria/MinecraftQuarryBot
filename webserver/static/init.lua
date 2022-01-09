local shell = require("shell")
local os = require("os")

-- Put the following in .shrc
-- rm -rf /tmp/init.lua
-- wget http://uni.quphoria.co.uk:7777/init.lua /tmp/init.lua
-- /tmp/init.lua
-- echo "Rebooting in 10 seconds"
-- echo "Press Ctrl+Alt+C to cancel"
-- sleep 10s && reboot

print("Starting program, press Ctrl+Alt+C to cancel")

-- os.sleep(5)

shell.setWorkingDirectory("/tmp")

-- shell.execute("rm /home/bot_id")
-- shell.execute("rm /home/.shrc")

while true do
    os.sleep(2)
    shell.execute("wget http://uni.quphoria.co.uk:7777/static/main.lua main.lua")
    shell.execute("main.lua")
    shell.execute("rm main.lua")
end

-- while true do
--     shell.execute("wget http://uni.quphoria.co.uk:7777/static/level.lua level.lua")
--     shell.execute("level.lua")
--     shell.execute("rm level.lua")
--     os.sleep(2)
-- end