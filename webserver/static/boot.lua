
-- run this with:
--     wget http://{URL}/boot.lua boot.lua
--     boot.lua


local url = "http://mc.quphoria.co.uk:7777/static/"

local f = io.open("startup.lua", "w")
if f then
    f:write('shell.run("rm init.lua")\n')
    f:write('shell.run("wget '..url..'init.lua init.lua")\n')
    f:write('shell.run("init.lua")\n')
    f:write("print('Rebooting in 10 seconds\\nHold Ctrl+T to cancel')\n")
    f:write("os.sleep(10)\n")
    f:write('shell.run("reboot")\n')
    f:close()
    print("Bootloader successfully programmed")
    print("Please reboot the computer")
end
