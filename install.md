## Installation

Use an Advanced Mining Turtle  
(Diamond Pickaxe and Ender Modem)

Run the following command (Replace {URL} with the flask server)  
```sh
wget http://{URL}/boot.lua boot.lua
boot.lua
```

Make sure the Pickaxe is on the left and the Ender Modem is on the right
You can use the following in `lua` to change the equipped item
```lua
turtle.equipLeft()
turtle.equipRight()
```

### GPS Server

Layout 4 advanced computers with ender modems on the bottom according to the following diagram:  

Enter the following into the computers startup file:  
```lua
shell.run("gps","host",x,y,z)
```
Replace x,y,z with the coordinates of the computer (NOT the modem) no quotes are needed  