## Installation

## Robot

Prepare OS disk with OpenOS

Put the following into /home/.shrc
```sh
rm -rf /tmp/*
wget http://uni.quphoria.co.uk:7777/init.lua /tmp/init.lua
/tmp/init.lua
echo "Rebooting in 10 seconds"
echo "Press Ctrl+Alt+C to cancel"
sleep 10s && reboot
```