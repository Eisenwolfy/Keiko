import math
import tkinter as tk

from PIL import Image

PIX = 3
GRID = 40
FRAMES = 8
DURATION = 90
GIF_PATH = "bat_ref.gif"


PALETTE = {
    ".": (255, 255, 255),
    "#": (33, 33, 33),
    "g": (96, 103, 116),
    "p": (115, 84, 101),
    "d": (61, 66, 70),
    "l": (150, 128, 143),
    "r": (244, 144, 164),
}
KEYS = list(PALETTE)

ART = [
    "........................................",
    ".................................#######",
    "...............................##gggddd#",
    "..............#........#......#ggdddpp#.",
    "..####.......#d#......#d#....#gddppppp#.",
    ".#gggg####...#rd#....#dr#....#gddpppp#..",
    ".#ddddgggg#..#rrd####drr#....#gdpdppp#..",
    "..##ppdddg#..#rrggggggrr#...#gdpppddp#..",
    "...#ppppdg#..##ggggggggg#...#gddppppd#..",
    "....#ppdpdd#.#ggggggggg#....#gdpppppd#..",
    "....#pdpppd##ggggggggggg#..#gdpdpppp#...",
    "....#dppppdd#gg#ggg#gggg###gddppdpp#....",
    "....#pppppdd#gg#ggg#gggg#ggddpppdp#.....",
    ".....##pppddd#rgggggrggg#dddppppp#......",
    ".......##pdddd#gggggggdgg#ddpp###.......",
    "........#pddddd#ddddddgggg#dp#..........",
    ".........#d###d#pppppggggggd#...........",
    "..........#...##pplllllgggg#............",
    "...............##pllllllgggg#...........",
    "................#pllllllggggg#..........",
    ".................#pplllg###gg#..........",
    "..................##ppp#...##...........",
    "....................#gg#................",
    ".....................##.................",
    "........................................",
]
ART_H = len(ART)
BODY_L, BODY_R = 13, 26


def make_frame(f, bob):
    grid = [[0] * GRID for _ in range(GRID)]
    top = (GRID - ART_H) // 2
    for r, line in enumerate(ART):
        for c, ch in enumerate(line):
            if ch == ".":
                continue
            if c < BODY_L:
                dist = (BODY_L - c) / BODY_L
            elif c > BODY_R:
                dist = (c - BODY_R) / (GRID - 1 - BODY_R)
            else:
                dist = 0
            dy = bob + round(-3 * f * dist)
            y = r + top + dy
            if 0 <= y < GRID:
                grid[y][c] = KEYS.index(ch)

    img = Image.new("P", (GRID, GRID), 0)
    flat = []
    for k in KEYS:
        flat += PALETTE[k]
    img.putpalette(flat)
    img.putdata([v for row in grid for v in row])
    return img.resize((GRID * PIX, GRID * PIX), Image.NEAREST)


def make_gif(path=GIF_PATH):
    frames = []
    for i in range(FRAMES):
        t = 2 * math.pi * i / FRAMES
        frames.append(make_frame(math.sin(t), round(math.sin(t))))
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=DURATION, loop=0, disposal=2)


def show_gif(path=GIF_PATH):
    size = GRID * PIX

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    # Белый цвет окна становится прозрачным
    root.wm_attributes("-transparentcolor", "white")

    # Само окно делаем белым, чтобы этот цвет был chroma key
    root.configure(bg="white")

    x = (root.winfo_screenwidth() - size) // 2
    y = (root.winfo_screenheight() - size) // 2
    root.geometry(f"{size}x{size}+{x}+{y}")

    frames = []

    while True:
        try:
            frames.append(
                tk.PhotoImage(
                    file=path,
                    format=f"gif -index {len(frames)}"
                )
            )
        except tk.TclError:
            break

    label = tk.Label(
        root,
        bd=0,
        bg="white"
    )
    label.pack()

    def animate(i=0):
        label.config(image=frames[i])
        root.after(
            DURATION,
            animate,
            (i + 1) % len(frames)
        )

    drag = {}

    def start(e):
        drag["x"] = e.x
        drag["y"] = e.y

    def move(e):
        root.geometry(
            f"+{root.winfo_x() + e.x - drag['x']}"
            f"+{root.winfo_y() + e.y - drag['y']}"
        )

    label.bind("<Button-1>", start)
    label.bind("<B1-Motion>", move)
    label.bind("<Button-3>", lambda e: root.destroy())
    label.bind("<Double-Button-1>", lambda e: root.destroy())

    animate()
    root.mainloop()

if __name__ == "__main__":
    make_gif()
    show_gif()
