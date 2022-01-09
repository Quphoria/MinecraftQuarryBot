local io = require("io")

-- run this with wget http://{URL}/boot.lua /tmp/boot.lua && /tmp/boot.lua

local url = "http://mc.quphoria.co.uk:7777/static/"

local f = io.open("/home/.shrc", "w")
if f then
    f:write("rm -rf /tmp/init.lua\n")
    f:write("wget "..url.."init.lua /tmp/init.lua && /tmp/init.lua\n")
    f:write("echo 'Rebooting in 10 seconds\\nPress Ctrl+Alt+C to cancel'\n")
    f:write("sleep 10s && reboot\n")
    f:close()
    print("Bootloader successfully programmed")
    print("Please reboot the computer")
end
