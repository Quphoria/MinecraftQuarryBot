## Installation

## Robot

Prepare OS disk with OpenOS

Put the following into /home/.shrc (Replace {URL} with the flask server)  
```sh
rm -rf /tmp/*
wget http://{URL}/init.lua /tmp/init.lua
/tmp/init.lua
echo "Rebooting in 10 seconds"
echo "Press Ctrl+Alt+C to cancel"
sleep 10s && reboot
```