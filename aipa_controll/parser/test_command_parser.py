from command_parser import CommandParser


parser = CommandParser()

commands = [
    "click a5",
    "right click b3",
    "drag a1 h8",
    "scroll up",
    "scroll down",
    "type hello",
    "press ctrl c",
    "grid on",
    "grid off",
    "grid 6 6",
    "zoom a5"
]

for cmd in commands:
    action = parser.parse(cmd)
    print(action)