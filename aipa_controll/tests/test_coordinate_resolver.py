from aipa_controll.utils.coordinate_resolver import CoordinateResolver


resolver = CoordinateResolver(
    rows=8,
    cols=8,
    screen_width=1920,
    screen_height=1080,
)

tests = [
    "a1",
    "b3",
    "h8",
]

for coord in tests:
    pixel = resolver.resolve(coord)
    print(coord, "->", pixel)