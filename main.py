import json
import math
import os.path
import re
import sys
import time
import tkinter as tk
from idlelib.tooltip import Hovertip
from tkinter import filedialog, messagebox
from tkinter import simpledialog
from PIL import Image, ImageDraw

from shapely.affinity import translate
from shapely.geometry import Polygon, Point, mapping

VERSION = 1.6 #  internal version number, not currently used for anything just wanted to keep track.
#  On release versions this number will be a whole number referring to the amount of updates since release. Minor updates will still use decimal places.

print("Splatographer version: " + str(VERSION))

autosave_time = time.time() #  "last autosave" timestamp

path = "" #  level file path

levelTemplate = { #  base keyset for a level.
    "spawn": [],  # A coordinate pair for where the spawnpoint should be.
    "floors": [],
    "symmetryPoint": [],  # The point at which symmetry occurs, empty if not defined.
    "rotated": "rotated",  # is this level rotated or flipped? valid values: rotated, x, y
    "towerStart": True,
    # the "start" of the tower path is either index 0 or -1 if this value is True or False respectively
    "objectives": {
        "zones": [],  # list of splatzones, each zone is a list of points
        "tower": [],  # list of points which lay out the path, a third entry can make the point a checkpoint.
        "rain": [],
        # list of coordinates for podiums be them checkpoints or goals, third entry in a datapoint can be the rainmaker itself if needed.
        "clams": []  # basket coordinates
    },
    "rails": [],  # 2d array of coordinate lists ( all -> rail -> coordinate pair, 3d list)
    "sponges": []  # 2d array of coordinate pairs listing all existing sponges
}

level = levelTemplate.copy()

## Coded by Seamus Donahue, feel free to mod/redistribute but I just ask that you leave alone the credit to me :)
# I know some of this code can be replaced with match for pattern matching but the version of python I used for this didn't have it :\

tempPoints = [] #  point to be turned into a floor
copiedFloor = {} #  floor copied with ctrl+c

grid = 32
camera = [0, 0]
zoom = 1
drawGrid = True
snapping = True
autosave_interval = 300
heightIncrement = 10
currentLayer = 0
layerKey = ["all", "turf", "zones", "tower", "rain", "clams"]  # which layer is what

askSave = False
previousHash = hash(str(level))
preferences = {
    "grid": 32,
    "height_increment": 10,
    "snap": True,
    "autosave_interval_seconds": 300
}
showSymmetry = True

"""
compile with pyInstaller:
pyinstaller --noconfirm --onefile --windowed --add-data "./images;images/" --icon "images/mappericon.ico"  "./main.py"
"""

# place modes: (in order)
# 0 floor
# 1 spawnpoint
# 2 misc (sponge/rails)
# 3 objective primary
# 4 objective secondary
placing = False
placemode = 0
placeStrings = ["floor", "spawn point", "sponges/rails", "primary objective", "secondary objective"]

def validateLevel():  # this will make sure that the level file is fully valid
    global level
    level = levelTemplate | level

    save()


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def toggleGrid():
    global drawGrid
    drawGrid = not drawGrid


def toggleSnap():
    global snapping
    snapping = not snapping


def toggleShowSymmetry(*args):
    global showSymmetry
    showSymmetry = not showSymmetry


def resetCamera():
    global camera
    camera = [16, 16]


YELLOW = "#F9C622"
DARK_BLUE = "#0F2129"
LIGHT_BLUE = "#1E8798"
PURPLE = "#6342f5"
LIGHT_PURPLE = "#fc05f0"
GREEN = "#006805"
LIGHT_GREEN = "#00EA0F"
RED = "#ff3f14"
TOMATO = "#E46F3B"
LIGHT_GREY = "#8D8D8D"


def gridinc(*args):
    global grid
    grid *= 2


def griddec(*args):
    global grid
    if (grid // 2 > 0):
        grid //= 2


def save(*args):
    global askSave
    if path == "":
        messagebox.showerror(title="No file open", message="No file is currently open to be saved!")
        return
    with open(path, "w") as f:
        f.write(json.dumps(level))
    askSave = False


def newFile(*args):
    global path
    global level
    clear = len(path) != 0
    potentialPath = filedialog.asksaveasfilename(title="Make new map", filetypes=[("Splat map files", ".splat")])
    if "Control_L" in keys: keys.remove("Control_L")  # fix control counting as being pressed when it's not.

    if len(potentialPath) == 0:
        return
    path = potentialPath
    if not re.search("(?:\.splat)$", path):  # add .splat if it isn't the end of the filename already
        path += ".splat"

    if clear:
        level = {
            "floors": []
        }
    save()


def openFile(*args):  # *args so the hotkey can be used lol
    global path
    global level
    global camera
    global askSave
    global previousHash
    newPath = filedialog.askopenfilename(title="Open existing map", filetypes=[("Splat map files", ".splat")])
    if "Control_L" in keys: keys.remove("Control_L")  # fix control counting as being pressed when it's not.

    if len(newPath) > 0:
        if re.search("(?:\.splat)$", newPath):
            path = newPath
            with open(path, "r") as f:
                level = json.loads(f.read())
                validateLevel()
            camera = [-grid, -grid]
            askSave = False
            level["floors"] = list(map(lambda floor : {"points": [], "type": 0, "height": 100, "layer": 0} | floor, level["floors"]))
            for floor in level["floors"]:
                if len(floor["points"]) < 3:
                    print(f"[WARNING] Removed {floor}! No points! Corrupted file?")
                    level["floors"].remove(floor)

            for rail in level["rails"]:
                for index, point in enumerate(rail):
                    while len(point) < 2:
                        point.append(0)
                        print(f"[WARNING] Fixed point in rail {rail}! Outdated file?")

                    if (index == 0 and len(point) < 3):
                        point.append(0)

            for sponge in level["sponges"]:
                while len(sponge) < 3:
                    sponge.append(0)
                    print(f"[WARNING] Fixed sponge data in sponge {sponge}! Outdated file?")

            previousHash = hash(str(level))
            # add some loading code now...
        else:
            messagebox.showerror(title="Invalid file type",
                                 message="Invalid file type! This program only reads .splat files made by this program.")


def about():
    messagebox.showinfo(title="About this program", message="""
    This program was created to make map concepts easier to create!
    The idea is too have good looking maps created very easily in a similar style to how Splatoon 3 displays the map when you press X.
    This program was created by Seamus Donahue, you can find more info at https://error418.carrd.co/ or email me at seamus-donahue@proton.me
    """)


def floorUp():
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["height"] = min(level["floors"][selectedIndex]["height"] + heightIncrement, 100)


def floorDown():
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["height"] = max(level["floors"][selectedIndex]["height"] - heightIncrement, 0)


def askHeightIncrement():
    newIncrement = simpledialog.askinteger("New height increment",
                                           "How many units should the raise and lower command modify a floors height by?")

def updateFloorTypeKeybind(event):
    newType = {"i":0, "u": 1, "g": 2}[event.char]
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["type"] = newType
        floortype.set(str(newType))

def deleteFloor(*args):
    global selectedIndex
    if selectedIndex in range(len(level["floors"])):
        level["floors"].remove(level["floors"][selectedIndex])
        selectedIndex = -1


def changeLayer(event):
    global currentLayer
    currentLayer = int(event.keysym)
    layerVar.set(event.keysym)


def xflip():
    level["rotated"] = "x"


def yflip():
    level["rotated"] = "y"


def rotatenotflip():
    level["rotated"] = "rotated"

settingsPath = os.path.expanduser("~\\Splatographer\\settings.json")

def applySettings():
    global grid
    global heightIncrement
    global snapping
    global preferences
    global autosave_interval
    if not os.path.exists(os.path.expanduser("~\\Splatographer")):
        os.mkdir(os.path.expanduser("~\\Splatographer"))
    if not os.path.exists(settingsPath):
        with open(settingsPath, "w") as f:
            f.write(json.dumps(preferences))
    with open(settingsPath, "r") as f:
        preferences = preferences | json.loads(f.read())

    grid = int(preferences["grid"])
    heightIncrement = preferences["height_increment"]
    snapping = preferences["snap"]
    autosave_interval = preferences["autosave_interval_seconds"]


def settingsWindow():
    Settings()


def toPoints(shape):
    points = mapping(shape)["coordinates"][0]
    return [[point[0], point[1]] for point in points]


def flipTowerPath():
    level["towerStart"] = not level["towerStart"]


def setSymmetry(*args):
    level["symmetryPoint"] = snappedMouse()


def resetSymmetry():
    if (messagebox.askyesno(title="Reset symmetry settings",
                            message="Do you want to reset symmetry settings for this map?")):
        level["symmetryPoint"] = []
        level["rotated"] = "rotated"


def copy(*args):
    global copiedFloor
    if selectedIndex != -1:
        copiedFloor = level["floors"][selectedIndex].copy()
        initPoly = Polygon(level["floors"][selectedIndex]["points"])
        initPoly = translate(initPoly, xoff=initPoly.bounds[0] * -1, yoff=initPoly.bounds[1] * -1)
        copiedFloor["points"] = toPoints(initPoly)


def paste(*args):
    global tempPoints
    if copiedFloor == {}: return
    pasted = copiedFloor.copy()
    pastedPoly = Polygon(pasted["points"])
    pastedPoly = translate(pastedPoly, snappedMouse()[0], snappedMouse()[1])
    pasted["points"] = toPoints(pastedPoly)
    level["floors"].append(pasted)


# this is very complex because it auto-generates the window based on how the preferences object is structured lol
class Settings:
    def __init__(self):
        self.font = "Sans-Serif 10 bold"

        self.window = tk.Toplevel(padx=10, pady=10, bg=DARK_BLUE)
        self.window.wm_title("Preferences")
        self.window.resizable(False, False)

        row = 0

        topLabel = tk.Label(self.window, text="Change persistent settings: ", bg=DARK_BLUE, fg=YELLOW, font=self.font)
        topLabel.grid(column=0, row=row)

        self.settings = {}
        for k, v in preferences.items():
            row += 1

            key = tk.Label(self.window, text=k, bg=DARK_BLUE, fg=YELLOW, font=self.font)
            key.grid(column=0, row=row)

            inp = tk.Entry(self.window, bg=LIGHT_BLUE, fg=YELLOW, font=self.font)
            inp.insert(0, v)

            if type(v) is int or type(v) is float:
                self.settings[k] = tk.DoubleVar(self.window, v)
                inp.config(validatecommand=(self.window.register(self.validDigit), "%P", k), validate="all")
            elif type(v) is str:
                self.settings[k] = tk.StringVar(self.window, v)
                inp.config(textvariable=self.settings[k])
            elif type(v) is bool:
                self.settings[k] = tk.BooleanVar(self.window, v)
                inp = tk.Checkbutton(self.window, bg=DARK_BLUE, variable=self.settings[k], fg=YELLOW,
                                     selectcolor=LIGHT_BLUE, activebackground=DARK_BLUE)
            else:
                print("UNACCOUNTED FOR TYPE " + k + " WITH VALUE OF " + str(v))

            inp.grid(column=1, row=row)

        cancel = tk.Button(self.window, text="cancel", bg=LIGHT_BLUE, fg=YELLOW, font=self.font, command=self.quit)
        cancel.grid(column=0, row=row + 1)

        done = tk.Button(self.window, text="save", bg=LIGHT_BLUE, fg=YELLOW, font=self.font, command=self.save)
        done.grid(column=1, row=row + 1)

        bottomLabel = tk.Label(self.window,
                               text="These settings will be saved to a file and used on save and when starting splatographer again.",
                               bg=DARK_BLUE, fg=TOMATO, font="Sans-sarif 8 bold")
        bottomLabel.grid(column=0, row=row + 2, columnspan=2)

    def quit(self):
        self.window.destroy()

    def save(self):
        for k, v in self.settings.items():
            preferences[k] = v.get()

        with open(settingsPath, "w") as f:
            f.write(json.dumps(preferences))

        applySettings()

        self.window.destroy()

    def validDigit(self, inp, set):
        valid = inp == ""
        if not valid:
            try:
                float(inp)
                valid = True
            except:
                valid = False

        if valid:
            self.settings[set].set(inp)
        return valid


def export(showSuccess=True,*args):
    root.title("Splatographer | {} exporting {}.".format(path, layerKey[currentLayer]))
    allX = []
    allY = []
    for floor in level["floors"]:
        for point in floor["points"]:
            allX.append(point[0])
            allY.append(point[1])

    if len(level["floors"]) == 0:
        print("[Export] Failed! Level has no floors!")
        messagebox.showerror("Export", "Level cannot be exported with no floors!")
        return False

    allX.sort()
    allY.sort()

    symmetry = level["symmetryPoint"]

    offset = 25
    bounds = [allX[0] - offset, allY[0] - offset, allX[-1] + offset,
              allY[-1] + offset]  # format: [x, y, x, y] min first then max
    size = [round(abs(bounds[0] - bounds[2])), round(abs(bounds[1] - bounds[3]))]

    if symmetry:
        size[0] *= 2
        size[1] *= 2

    exported = Image.new("RGB", size)
    draw = ImageDraw.Draw(exported, mode="RGBA")

    draw.rectangle([0, 0, *size], fill=DARK_BLUE)

    # floor drawing code
    for floor in level["floors"]:
        if not (floor["layer"] == 0 or floor["layer"] == currentLayer):
            continue
        points = [(point[0] - bounds[0], point[1] - bounds[1]) for point in
                  floor["points"]]  # convert to tuples in the list because PIL is stupid.
        reflected = [(symmetrical(point)[0] - bounds[0], symmetrical(point)[1] - bounds[1]) for point in
                     floor["points"]]
        fill = "#" + (
            hex(int(
                255 * (floor["height"] / 100)))
            .removeprefix("0x")) * 3

        if floor["type"] == 1: fill = "#7f7f7f"

        if floor["type"] < 2:
            draw.polygon(points, fill=fill, width=0)
            if symmetry:
                draw.polygon(reflected, fill=fill, width=0)
        else:
            draw.polygon(points, fill=(0, 0, 0, 0), width=1, outline=fill)
            if symmetry:
                draw.polygon(reflected, fill=(0, 0, 0, 0), width=1, outline=fill)

        if floor["type"] > 0:  # draw the patterns for the floor types.
            grate = Image.open(resource_path("images\\grate.xbm"))
            unink = Image.open(resource_path("images\\uninkable.xbm"))

            sortedx = points.copy()
            sortedx.sort(key=lambda x: x[0])
            sortedy = points.copy()
            sortedy.sort(key=lambda x: x[1])

            bbox = [math.floor(sortedx[0][0]), math.floor(sortedy[0][1]), math.ceil(sortedx[-1][0]),
                    math.ceil(sortedy[-1][1])]

            shape = Polygon(points)

            for x in range(bbox[0], bbox[2]):
                for y in range(bbox[1], bbox[3]):
                    if Point(x, y).within(shape):
                        if floor["type"] == 2 and grate.getpixel((x % grate.width, y % grate.height)) > 0:
                            draw.point([x, y], fill=fill)
                        elif floor["type"] == 1 and unink.getpixel((x % unink.width, y % unink.height)) > 0:
                            draw.point([x, y], fill=(255, 255, 255))

            if symmetry:
                sortedx = reflected.copy()
                sortedx.sort(key=lambda x: x[0])
                sortedy = reflected.copy()
                sortedy.sort(key=lambda x: x[1])
                bbox = [math.floor(sortedx[0][0]), math.floor(sortedy[0][1]), math.ceil(sortedx[-1][0]),
                        math.ceil(sortedy[-1][1])]

                shape = Polygon(reflected)
                for x in range(bbox[0], bbox[2]):
                    for y in range(bbox[1], bbox[3]):
                        if Point(x, y).within(shape):
                            if floor["type"] == 2 and grate.getpixel((x % grate.width, y % grate.height)) > 0:
                                draw.point([x, y], fill=fill)
                            elif floor["type"] == 1 and unink.getpixel((x % unink.width, y % unink.height)) > 0:
                                draw.point([x, y], fill=(255, 255, 255))

    #  objective drawing code
    if currentLayer == 2:  # zones
        for zone in level["objectives"]["zones"]:
            points = [(point[0] - bounds[0], point[1] - bounds[1]) for point in
                      zone]
            reflected = [(symmetrical(point)[0] - bounds[0], symmetrical(point)[1] - bounds[1]) for point in zone]

            draw.polygon(points, fill=(0, 0, 0, 0), outline=PURPLE, width=3)
            if symmetry:
                draw.polygon(reflected, fill=(0, 0, 0, 0), outline=GREEN, width=3)
    elif currentLayer == 3:  # tower
        for point in level["objectives"]["tower"]:
            absolute = (point[0] - bounds[0], point[1] - bounds[1])
            reflected = (symmetrical(point)[0] - bounds[0], symmetrical(point)[1] - bounds[1])

            if len(point) == 3:
                draw.rectangle([absolute[0] - 25, absolute[1] - 25, absolute[0] + 25, absolute[1] + 25], fill=PURPLE,
                               outline=LIGHT_PURPLE, width=1)
                if symmetry:
                    draw.rectangle([reflected[0] - 25, reflected[1] - 25, reflected[0] + 25, reflected[1] + 25],
                                   fill=GREEN, outline=LIGHT_GREEN, width=1)

            index = level["objectives"]["tower"].index(point)
            if index > 0:
                prev = level["objectives"]["tower"][index - 1].copy()
                refPrev = symmetrical(prev)
                prev = (prev[0] - bounds[0], prev[1] - bounds[1])
                refPrev = (refPrev[0] - bounds[0], refPrev[1] - bounds[1])

                draw.line([prev, absolute], fill=LIGHT_PURPLE, width=3)
                if symmetry:
                    draw.line([refPrev, reflected], fill=LIGHT_GREEN, width=3)

        if level["symmetryPoint"] and len(level["objectives"]["tower"]) > 0:
            point1 = level["objectives"]["tower"][0 if level["towerStart"] else -1]
            point1 = (point1[0] - bounds[0], point1[1] - bounds[1])
            point2 = symmetrical(level["objectives"]["tower"][0 if level["towerStart"] else -1])
            point2 = (point2[0] - bounds[0], point2[1] - bounds[1])
            mid = ((point1[0] + point2[0]) / 2, (point1[1] + point2[1]) / 2)
            draw.line([point1, mid], fill=LIGHT_PURPLE, width=3)
            draw.line([point2, mid], fill=LIGHT_GREEN, width=3)

    elif currentLayer == 4:
        maker = False
        for podium in level["objectives"]["rain"]:
            fill = PURPLE if len(podium) == 2 else YELLOW
            size = 25 if len(podium) == 2 else 15

            absolute = (podium[0] - bounds[0], podium[1] - bounds[1])
            reflected = symmetrical(podium)
            reflected = (reflected[0] - bounds[0], reflected[1] - bounds[1])

            draw.circle(absolute, size, fill=fill, outline=LIGHT_PURPLE, width=5)
            if level["symmetryPoint"]:
                if len(podium) < 3:
                    draw.circle(reflected, size, fill=GREEN, outline=LIGHT_GREEN, width=5)
                else:
                    maker = True
        if not maker and level["symmetryPoint"]:
            point = (level["symmetryPoint"][0] - bounds[0], level["symmetryPoint"][1] - bounds[1])
            draw.circle(point, 15, fill=YELLOW, outline=LIGHT_PURPLE, width=5)
    elif currentLayer == 5:
        mesh = Image.open(resource_path("images\\mesh.xbm"))

        for clam in level["objectives"]["clams"]:
            absolute = (clam[0] - bounds[0], clam[1] - bounds[1])
            reflected = symmetrical(clam)
            reflected = (reflected[0] - bounds[0], reflected[1] - bounds[1])

            if len(clam) == 2:
                draw.circle(absolute, 5, fill=PURPLE, outline=LIGHT_PURPLE, width=2)
                if symmetry:
                    draw.circle(reflected, 5, fill=GREEN, outline=LIGHT_GREEN, width=2)
            else:
                for x in range(round(absolute[0] - 25), round(absolute[0] + 25)):
                    for y in range(round(absolute[1] - 25), round(absolute[1] + 25)):
                        if mesh.getpixel((x % mesh.width, y % mesh.height)) > 0:
                            draw.point((x, y), fill=PURPLE)
                draw.rectangle((absolute[0] - 25, absolute[1] - 25, absolute[0] + 25, absolute[1] + 25),
                               fill=(0, 0, 0, 0), outline=LIGHT_PURPLE, width=5)

                if symmetry:
                    for x in range(round(reflected[0] - 25), round(reflected[0] + 25)):
                        for y in range(round(reflected[1] - 25), round(reflected[1] + 25)):
                            if mesh.getpixel((x % mesh.width, y % mesh.height)) > 0:
                                draw.point((x, y), fill=GREEN)
                    draw.rectangle((reflected[0] - 25, reflected[1] - 25, reflected[0] + 25, reflected[1] + 25),
                                   fill=(0, 0, 0, 0), outline=LIGHT_GREEN, width=5)

    for sponge in level["sponges"]:
        if sponge[2] != currentLayer and sponge[2] != 0: continue
        absolute = (sponge[0] - bounds[0], sponge[1] - bounds[1])
        draw.rectangle((absolute[0], absolute[1], absolute[0] + 32, absolute[1] + 32), fill=PURPLE)
        if symmetry:
            reflected = symmetrical(sponge)
            reflected = (reflected[0] - bounds[0], reflected[1] - bounds[1])
            secondPoint = symmetrical([sponge[0] + 32, sponge[1] + 32])
            secondPoint = (secondPoint[0] - bounds[0], secondPoint[1] - bounds[1])
            #  PIL complains if the second coord is less than the first >:(
            x = [secondPoint[0], reflected[0]]
            x.sort()
            y = [secondPoint[1], reflected[1]]
            y.sort()
            draw.rectangle((x[0], y[0], x[1], y[1]), fill=GREEN)

    for rail in level["rails"]:
        if rail[0][2] != currentLayer and rail[0][2] != 0: continue
        for point in rail:
            start = rail.index(point) == 0
            size = 10 if start else 5
            absolute = (point[0] - bounds[0], point[1] - bounds[1])

            draw.circle(absolute, size, PURPLE)
            if not start:
                prev = rail[rail.index(point) - 1]
                prev = (prev[0] - bounds[0], prev[1] - bounds[1])
                draw.line([prev, absolute], fill=PURPLE, width=2)

            if symmetry:
                reflected = symmetrical(point)
                reflected = (reflected[0] - bounds[0], reflected[1] - bounds[1])
                draw.circle(reflected, size, fill=GREEN)
                if not start:
                    prev = symmetrical(rail[rail.index(point) - 1])
                    prev = (prev[0] - bounds[0], prev[1] - bounds[1])
                    draw.line([prev, reflected], fill=GREEN, width=2)

    if len(level["spawn"]) >= 2:
        absolute = (level["spawn"][0] - bounds[0], level["spawn"][1] - bounds[1])
        draw.circle(absolute, 40, width=8, fill=PURPLE, outline=LIGHT_GREY)
        if symmetry:
            reflected = symmetrical(level["spawn"])
            reflected = (reflected[0] - bounds[0], reflected[1] - bounds[1])
            draw.circle(reflected, 40, width=8,fill=GREEN,outline=LIGHT_GREY)

    exported.save(fp=path.removesuffix(".splat") + "-" + layerKey[currentLayer] + ".png")

    if showSuccess: messagebox.showinfo(title="Export", message="Map exported successfully!")
    return True


def exportAll(*args):
    global currentLayer
    for layer in range(len(layerKey)):
        currentLayer = layer
        if not export(False): return
    messagebox.showinfo(title="Export", message="Exported map on all layers!")

def updateFloorType():
    if selectedIndex >= 0:
        print("test")
        level["floors"][selectedIndex]["type"] = int(floortype.get())

def updateLayer():
    global currentLayer
    currentLayer = int(layerVar.get())
    print(int(layerVar.get()), currentLayer)

root = tk.Tk()  ##create window
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
root.iconbitmap(resource_path("images\\mappericon.ico"))
root.geometry("1600x900")

root.config(background="#222222")

topBar = tk.Menu(root)
fileMenu = tk.Menu(topBar, tearoff=0)
fileMenu.add_command(label="New Map", command=newFile)
fileMenu.add_command(label="Open Map", command=openFile)
fileMenu.add_command(label="Save Map", command=save)
fileMenu.add_command(label="Export Current Layer", command=export)
fileMenu.add_command(label="Export All Layers", command=exportAll)
fileMenu.add_command(label="preferences", command=settingsWindow)

floorMenu = tk.Menu(topBar, tearoff=0)
floorMenu.add_command(label="raise (↑)", command=floorUp)
floorMenu.add_command(label="lower (↓)", command=floorDown)
floorMenu.add_command(label="change height increment", command=askHeightIncrement)
floortype = tk.StringVar()
floortype.set("0")
typeMenu = tk.Menu(floorMenu, tearoff=False)
typeMenu.add_radiobutton(label="inkable (i)", value="0", variable=floortype, command=updateFloorType)
typeMenu.add_radiobutton(label="uninkable (u)", value="1", variable=floortype, command=updateFloorType)
typeMenu.add_radiobutton(label="grate (g)", value="2", variable=floortype, command=updateFloorType)
floorMenu.add_cascade(menu=typeMenu, label="floor type")
floorMenu.add_separator()
floorMenu.add_command(label="delete floor (delete or backspace)", command=deleteFloor)

layerMenu = tk.Menu(topBar, tearoff=0)
layerVar = tk.StringVar()
layerVar.set("0")
layerMenu.add_radiobutton(label="all (0)", value="0", command=updateLayer, variable=layerVar)
layerMenu.add_separator()
layerMenu.add_radiobutton(label="turf (1)", value="1", command=updateLayer, variable=layerVar)
layerMenu.add_radiobutton(label="zones (2)", value="2", command=updateLayer, variable=layerVar)
layerMenu.add_radiobutton(label="tower (3)", value="3", command=updateLayer, variable=layerVar)
layerMenu.add_radiobutton(label="rain (4)", value="4", command=updateLayer, variable=layerVar)
layerMenu.add_radiobutton(label="clams (5)", value="5", command=updateLayer, variable=layerVar)

symmetryMenu = tk.Menu(topBar, tearoff=0)
symmetryMenu.add_command(label="show symmetry", command=toggleShowSymmetry)
symmetryMenu.add_separator()
symmetryMenu.add_command(label="rotated symmetry", command=rotatenotflip)
symmetryMenu.add_command(label="flip on x", command=xflip)
symmetryMenu.add_command(label="flip on y", command=yflip)
symmetryMenu.add_command(label="flip tower 'start'", command=flipTowerPath)
symmetryMenu.add_separator()
symmetryMenu.add_command(label="reset", command=resetSymmetry)

topBar.add_cascade(label="File", menu=fileMenu)
topBar.add_cascade(label="Floor", menu=floorMenu)
topBar.add_cascade(label="Layer", menu=layerMenu)
topBar.add_cascade(label="Symmetry", menu=symmetryMenu)
topBar.add_command(label="ToggleGrid", command=toggleGrid)
topBar.add_command(label="Snap to grid", command=toggleSnap)
topBar.add_command(label="reset camera", command=resetCamera)
topBar.add_command(label="About", command=about)

def placeFloors():
    global tempPoints
    if len(tempPoints) > 0:
        if len(tempPoints) <= 2 or Polygon(tempPoints).area == 0:
            tempPoints = []
            return
        level["floors"].append({"points": tempPoints, "type": 0, "height": 100, "layer": currentLayer})
        tempPoints = []

def confirmMode():
    global placemode
    global placing
    placemode = 0
    placing = False

    placeFloors()

def floorMode():
    global placemode
    global placing
    placemode = 0
    placing = True

def spawnMode():
    global placemode
    global placing
    placemode = 1
    placing = True

def miscMode():
    global placemode
    global placing
    placemode = 2
    placing = True

def objectivePrimaryMode():
    global placemode
    global placing
    placemode = 3
    placing = True

def objectiveSecondaryMode():
    global placemode
    global placing
    placemode = 4
    placing = True

imageSubsample = 3

mainframe = tk.Frame(root)
mainframe.grid(row=0, column=0, sticky="NSEW")
mainframe.columnconfigure(0, weight=1)

buttonFrame = tk.Frame(mainframe, background=DARK_BLUE, highlightthickness=1, highlightbackground=LIGHT_BLUE)
buttonFrame.grid(row=0, column=0, sticky="NSEW")

# def updateplacemode():
#     global placemode
#     if "Shift_L" in keys:
#         if 'Alt_L' in keys:
#             placemode = 2
#         else:
#             placemode = 4 if "Control_L" in keys else 3
#     elif "Control_L" in keys:
#         placemode = 1
#     else:
#         placemode = 0

confirmImage = tk.PhotoImage(file=resource_path("images\\buttonIcons\\done icon.png"))
confirmImage = confirmImage.subsample(imageSubsample, imageSubsample)
confirmButton = tk.Button(buttonFrame, image=confirmImage, background=LIGHT_BLUE, activebackground=YELLOW, command=confirmMode)
confirmButton.pack(side="left", anchor="w")
Hovertip(confirmButton, "Leave place mode/confirm floor placement\nHotkey: release Lshift", hover_delay=100)

floorImage = tk.PhotoImage(file=resource_path("images\\buttonIcons\\floor placemode.png"))
floorImage = floorImage.subsample(imageSubsample, imageSubsample)
floorButton = tk.Button(buttonFrame, image=floorImage, background=LIGHT_BLUE, activebackground=YELLOW, command=floorMode)
floorButton.pack(side="left")
Hovertip(floorButton, "floor placement mode (right click to create points)\nHotkey: hold LShift", hover_delay=100)

spawnImage = tk.PhotoImage(file=resource_path("images\\buttonIcons\\spawnpoint.png"))
spawnImage = spawnImage.subsample(imageSubsample, imageSubsample)
spawnButton = tk.Button(buttonFrame, image=spawnImage, background=LIGHT_BLUE, activebackground=YELLOW, command=spawnMode)
spawnButton.pack(side="left")
Hovertip(spawnButton, "Spawn point placement mode\nHotkey: LCtrl + left click", hover_delay=100)

miscImage = tk.PhotoImage(file=resource_path("images\\buttonIcons\\misc icon.png"))
miscImage = miscImage.subsample(imageSubsample, imageSubsample)
miscButton = tk.Button(buttonFrame, image=miscImage, background=LIGHT_BLUE, activebackground=YELLOW, command=miscMode)
miscButton.pack(side="left")
Hovertip(miscButton, "Sponge/rail placement mode. (right click to create points, then left click to make a rail)\nHotkey: LShift + LAlt + left click", hover_delay=100)

objectivePrimaryImage = tk.PhotoImage(file=resource_path("images\\buttonIcons\\objective primary.png"))
objectivePrimaryImage = objectivePrimaryImage.subsample(imageSubsample, imageSubsample)
objectivePrimaryButton = tk.Button(buttonFrame, image=objectivePrimaryImage, background=LIGHT_BLUE, activebackground=YELLOW, command=objectivePrimaryMode)
objectivePrimaryButton.pack(side="left")
Hovertip(objectivePrimaryButton, "Primary objective object placement mode (placed objective depends on current layer, right click for points for zones then left click to confirm zone)\nHotkey: LShift + left click", hover_delay=100)

objectiveSecondaryImage = tk.PhotoImage(file=resource_path("images\\buttonIcons\\objective secondary.png"))
objectiveSecondaryImage = objectiveSecondaryImage.subsample(imageSubsample, imageSubsample)
objectiveSecondaryButton = tk.Button(buttonFrame, image=objectiveSecondaryImage, background=LIGHT_BLUE, activebackground=YELLOW, command=objectiveSecondaryMode)
objectiveSecondaryButton.pack(side="left")
Hovertip(objectiveSecondaryButton, "Secondary objective object placement mode (placed objective depends on current layer, not applicable for zones)\nHotkey: LShift + LCtrl + left click", hover_delay=100)

canvas = tk.Canvas(mainframe, width=1600, height=900, background=DARK_BLUE, highlightthickness=0)
canvas.grid(row=1, column=0, sticky="NSEW")

root.bind(sequence="<Control-o>", func=openFile)
root.bind(sequence="<Control-s>", func=save)
root.bind(sequence="<Control-n>", func=newFile)
root.bind(sequence="<Control-e>", func=export)
root.bind(sequence="<Control-Shift-KeyPress-E>",func=exportAll)
root.bind(sequence="<Delete>", func=deleteFloor)
root.bind(sequence="<BackSpace>", func=deleteFloor)
root.bind(sequence="<]>", func=gridinc)
root.bind(sequence="<[>", func=griddec)
root.bind(sequence="<i>", func=updateFloorTypeKeybind)
root.bind(sequence="<u>", func=updateFloorTypeKeybind)
root.bind(sequence="<g>", func=updateFloorTypeKeybind)
root.bind(sequence="<Control-c>", func=copy)
root.bind(sequence="<Control-v>", func=paste)
root.bind(sequence="<Control-r>", func=setSymmetry)

for i in range(6):
    root.bind(sequence=str(i), func=changeLayer)

root.config(menu=topBar)

keys = []

def updateplacemode():
    global placemode
    if "Shift_L" in keys:
        if 'Alt_L' in keys:
            placemode = 2
        else:
            placemode = 4 if "Control_L" in keys else 3
    elif "Control_L" in keys:
        placemode = 1
    else:
        placemode = 0


def keypress(event):
    global placing
    if not event.keysym in keys:
        keys.append(event.keysym)

    placing = "Shift_L" in keys

    updateplacemode()

    # I really want to make this a match statement but I don't really know how I can
    if "Up" in keys and selectedIndex != -1:
        floorUp()
    if "Down" in keys and selectedIndex != -1:
        floorDown()


def keyrelease(event):
    global placing
    if event.keysym in keys:
        keys.remove(event.keysym)

    global tempPoints
    if event.keysym == "Shift_L":
        placeFloors()
        placing = False

    updateplacemode()


dragPrevious = [0, 0]

mousePos = [0, 0]
selectedIndex = -1
selectedPoint = -1
deleteDistance = 5


def updateMousePos(event):
    global mousePos
    mousePos = [event.x, event.y]


def mouseDrag(event):
    global dragPrevious
    updateMousePos(event)
    camera[0] -= dragPrevious[0] - event.x
    camera[1] -= dragPrevious[1] - event.y
    dragPrevious = [event.x, event.y]


def placeMiscElement(event):
    global tempPoints
    for sponge in level["sponges"]:
        if sponge[2] != currentLayer and sponge[2] != 0: continue
        if math.dist(sponge[:2], snappedMouse()) < grid / 2:
            level["sponges"].remove(sponge)
            return
    for rail in level["rails"]:
        if rail[0][2] != currentLayer and rail[0][2] != 0: continue
        if math.dist(rail[0][:2], snappedMouse()) < grid / 2:
            level["rails"].remove(rail)
            return
    if len(tempPoints) >= 2:
        level["rails"].append(tempPoints.copy())
        level["rails"][-1][0].append(currentLayer)
        tempPoints = []
    else:
        level["sponges"].append((*snappedMouse(), currentLayer))


def mousePress(event):
    global dragPrevious
    global selectedIndex
    global tempPoints
    dragPrevious = [event.x, event.y]

    if placemode == 0:
        selected = False
        for floor in level["floors"]:
            if Point(fromScreen(mousePos)).within(Polygon(floor["points"])):
                selectedIndex = level["floors"].index(floor)
                floortype.set(str(floor["type"]))
                selected = True

        if not selected: selectedIndex = -1
    elif placemode == 1:
        level["spawn"] = snappedMouse()
    elif placemode == 2:
        placeMiscElement(event)
    elif placemode == 3 or placemode == 4:
        placeObjective(event)

    # if "Shift_L" in keys:
    #     if 'Alt_L' in keys:
    #         placeMiscElement(event)
    #     else:
    #         placeObjective(event)
    # elif "Control_L" in keys:
    #     level["spawn"] = snappedMouse()
    # else:
    #     selected = False
    #     for floor in level["floors"]:
    #         if Point(fromScreen(mousePos)).within(Polygon(floor["points"])):
    #             selectedIndex = level["floors"].index(floor)
    #             selected = True
    #
    #     if not selected: selectedIndex = -1


def rclickPress(event):
    global selectedPoint
    if placing:
        point = snappedMouse()

        for tempPoint in tempPoints:
            distance = ((point[0] - tempPoint[0]) ** 2 + (point[1] - tempPoint[1]) ** 2) ** 0.5
            if distance < deleteDistance:
                tempPoints.remove(tempPoint)
                return

        tempPoints.append(point)
    elif selectedIndex >= 0:
        points = level["floors"][selectedIndex]["points"]
        lowestDist = 100000000000000
        for index, point in enumerate(points):
            dist = math.dist(point, snappedMouse())
            if dist <= lowestDist and dist <= grid // 4:
                lowestDist = dist
                selectedPoint = index

        if selectedPoint == -1:  # the only way this could happen is if there was no selection found close enough.
            closestLine = [-1, -1, 1000000000000]
            mouse = snappedMouse()
            for index, point1 in enumerate(points):
                point2 = points[index - 1] # this should be fine because -1 (the lowest value) should give the last in the list?

                ls = math.dist(point1, point2) ** 2

                if (ls == 0):
                    dist = math.dist(mouse, point1)
                else:
                    t = ((mouse[0] - point1[0]) * (point2[0] - point1[0]) + (mouse[1] - point1[1]) * (point2[1] - point1[1])) / ls
                    t = max(0, min(1, t))

                    dist = math.dist(mouse,[point1[0] + t * (point2[0] - point1[0]),
                                            point1[1] + t * (point2[1] - point1[1])])

                    # a = (point2[1] - point1[1])
                    # b = (point2[0] - point1[0])
                    # c = point2[0] * point1[1] - point2[1] * point1[0]
                    # dist = (abs(a * mouse[0] - b * mouse[1] + c) / math.dist(point1, point2))

                if dist <= closestLine[2]:
                    # print(dist, closestLine[2])
                    closestLine = ((index-1) % len(points), index, dist)

            # print(closestLine)

            endIndex = (closestLine[0] + 1) % len(points)
            # print(endIndex)
            level["floors"][selectedIndex]["points"].insert(endIndex, snappedMouse())
            selectedPoint = endIndex



# def configEvent(event):
#     canvas.config(width=event.width, height=event.height)


def snappedMouse():
    mpoint = fromScreen(mousePos)
    if snapping:
        mpoint[0] -= mpoint[0] % grid
        mpoint[1] -= mpoint[1] % grid
    return mpoint


def toScreen(coords):
    return [(coords[0] + camera[0]) * zoom, (coords[1] + camera[1]) * zoom]


def fromScreen(coords):
    return [round(coords[0] / zoom, 3) - camera[0], round(coords[1] / zoom, 3) - camera[1]]


def symmetrical(point):
    if not level["symmetryPoint"]:
        return [0, 0]
    if level["rotated"] == "rotated":
        return [
            level["symmetryPoint"][0] + math.cos(math.pi) * (point[0] - level["symmetryPoint"][0]) - math.sin(
                math.pi) * (point[1] - level["symmetryPoint"][1]),
            level["symmetryPoint"][1] + math.sin(math.pi) * (point[0] - level["symmetryPoint"][0]) + math.cos(
                math.pi) * (point[1] - level["symmetryPoint"][1])
        ]

    if level["rotated"] == "x":
        xdiff = point[0] - level["symmetryPoint"][0]
        return [point[0] - (xdiff * 2), point[1]]

    if level["rotated"] == "y":
        ydiff = point[1] - level["symmetryPoint"][1]
        return [point[0], point[1] - (ydiff * 2)]


def scroll(event):
    global zoom
    zoom += 0.1 if event.delta > 0 else -0.1
    zoom = min(2, max(0.5, zoom))


def placeObjective(event):
    global tempPoints
    if currentLayer < 2:
        return

    if currentLayer == 2:
        if len(tempPoints) == 0:
            for zone in level["objectives"]["zones"]:
                if Point(fromScreen(mousePos)).within(Polygon(zone)):
                    level["objectives"]["zones"].remove(zone)

        if len(tempPoints) < 3 or Polygon(tempPoints).area == 0: return
        level["objectives"][layerKey[currentLayer]].append(tempPoints)
        tempPoints = []
    else:
        for objective in level["objectives"][layerKey[currentLayer]]:
            distance = ((objective[0] - snappedMouse()[0]) ** 2 + (objective[1] - snappedMouse()[1]) ** 2) ** 0.5
            if distance < grid / 2:
                level["objectives"][layerKey[currentLayer]].remove(objective)
                return
        level["objectives"][layerKey[currentLayer]].append(snappedMouse())
        if (currentLayer >= 3) and placemode == 4:
            if currentLayer == 4:
                for point in level["objectives"]["rain"]:  # make sure only one rainmaker exists
                    if len(point) > 2:
                        level["objectives"]["rain"].remove(point)
                        break
            level["objectives"][layerKey[currentLayer]][-1].append(True)


def mouseDrag2(event):
    updateMousePos(event)
    if selectedIndex >= 0 and selectedPoint >= 0:
        try:
            level["floors"][selectedIndex]["points"][selectedPoint] = snappedMouse()
        except IndexError:
            print("[WARNING] Invalid point selection index when moving point!")


def mouseRelease(event):
    if event.num == 3: # right click
        global selectedPoint
        selectedPoint = -1

def mouseDoubleClick(event):
    global selectedPoint
    global selectedIndex
    rclickPress(event)
    if selectedPoint >= 0:
        level["floors"][selectedIndex]["points"].remove(level["floors"][selectedIndex]["points"][selectedPoint])
        if len(level["floors"][selectedIndex]["points"]) <= 2:
            level["floors"].remove(level["floors"][selectedIndex])
            selectedIndex = -1
        selectedPoint = -1

root.bind("<KeyPress>", keypress)
root.bind("<KeyRelease>", keyrelease)
# root.bind("<Configure>", configEvent)

canvas.bind("<B1-Motion>", mouseDrag)
canvas.bind("<B3-Motion>", mouseDrag2)
canvas.bind("<ButtonRelease>", mouseRelease)
canvas.bind("<Double-Button-3>", mouseDoubleClick)
canvas.bind("<Motion>", updateMousePos)
canvas.bind("<Button-1>", mousePress)
canvas.bind("<Button-2>", setSymmetry)
canvas.bind("<Button-3>", rclickPress)
canvas.bind("<MouseWheel>", scroll)


def die():
    if askSave:
        saveFile = messagebox.askyesnocancel(title="Close splatographer", message="Save before closing?")
        if saveFile == tk.YES:
            if os.path.exists(path):
                save()
            else:
                newFile()
        elif saveFile == None:
            return;

    global dead
    dead = True


root.wm_protocol("WM_DELETE_WINDOW", die)

if len(sys.argv) >= 2:
    if os.path.exists(sys.argv[1]):
        path = sys.argv[1]
        with open(path, "r") as f:
            level = json.loads(f.read())
        previousHash = hash(str(level))

applySettings()

dead = False


def drawFloors(canvas):
    for floor in level["floors"]:
        if not (floor["layer"] == 0 or floor["layer"] == currentLayer):
            continue

        drawPoly = []
        for i in floor["points"]:
            drawPoly.append(toScreen(i))

        drawSymmetry = []
        if showSymmetry and level["symmetryPoint"]:
            for i in floor["points"]:
                drawSymmetry.append(toScreen(symmetrical(i)))

        # this whole equation converts the height to a hex value between 0x0 and 0xff then formats it like a hex string
        fill = "#" + (
            hex(int(
                255 * (floor["height"] / 100)))
            .removeprefix("0x")) * 3

        if floor["type"] != 1:
            if level["floors"].index(floor) == selectedIndex:
                fill = "#"
                baseColor = [0xF9, 0xC6, 0x22]
                for color in baseColor:
                    added = hex(int(color * (floor["height"] / 100))).removeprefix("0x")
                    if len(added) == 1:
                        added = "0" + added
                    fill += added
        else:
            fill = "#7f7f7f"

        if floor["type"] < 2:
            canvas.create_polygon(*drawPoly, fill=fill)
            if drawSymmetry:
                canvas.create_polygon(*drawSymmetry, fill=fill)
            if floor["type"] == 1:
                canvas.create_polygon(*drawPoly,
                                      fill="white" if level["floors"].index(floor) != selectedIndex else YELLOW,
                                      stipple="@" + resource_path("images\\uninkable.xbm"))
                if drawSymmetry:
                    canvas.create_polygon(*drawSymmetry,
                                          fill="white" if level["floors"].index(floor) != selectedIndex else YELLOW,
                                          stipple="@" + resource_path("images\\uninkable.xbm"))
        else:
            canvas.create_polygon(*drawPoly, fill=fill,
                                  stipple="@" + resource_path("images\\grate.xbm"))
            if drawSymmetry:
                canvas.create_polygon(*drawSymmetry, fill=fill,
                                      stipple="@" + resource_path("images\\grate.xbm"))
        for point in drawPoly:
            canvas.create_rectangle(point[0] - 1, point[1] - 1, point[0] + 1, point[1] + 1, fill="black")
            if level["floors"].index(floor) == selectedIndex and drawPoly.index(point) == selectedPoint and selectedPoint >= 0:
                canvas.create_rectangle(point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3, fill=TOMATO)

        for point in drawSymmetry:
            canvas.create_rectangle(point[0] - 1, point[1] - 1, point[0] + 1, point[1] + 1, fill="black")


def drawObjectives(canvas):
    # objective drawing
    if currentLayer == 2:
        for zone in level["objectives"]["zones"]:
            for index in range(len(zone)):
                canvas.create_line(toScreen(zone[index]), toScreen(zone[(index - 1) % len(zone)]), fill=PURPLE,
                                   width=3 * zoom)
                if level["symmetryPoint"] and showSymmetry:
                    canvas.create_line(toScreen(symmetrical(zone[index])),
                                       toScreen(symmetrical(zone[(index - 1) % len(zone)])), fill=GREEN, width=3 * zoom)
    elif currentLayer == 3:
        for point in level["objectives"]["tower"]:
            width = 2 * zoom if len(point) == 2 else 25 * zoom
            absolute = toScreen(point)
            reflected = toScreen(symmetrical(point))
            canvas.create_rectangle(absolute[0] - width, absolute[1] - width, absolute[0] + width,
                                    absolute[1] + width, fill=PURPLE, outline=LIGHT_PURPLE, width=1 * zoom)
            if level["objectives"]["tower"].index(point) > 0:
                previous = toScreen(level["objectives"]["tower"][level["objectives"]["tower"].index(point) - 1])
                canvas.create_line(previous[0], previous[1], absolute[0], absolute[1], width=3 * zoom,
                                   fill=LIGHT_PURPLE)

            if level["symmetryPoint"] and showSymmetry:
                canvas.create_rectangle(reflected[0] - width, reflected[1] - width, reflected[0] + width,
                                        reflected[1] + width, fill=GREEN, outline=LIGHT_GREEN, width=1 * zoom)
                if level["objectives"]["tower"].index(point) > 0:
                    previous = toScreen(
                        symmetrical(level["objectives"]["tower"][level["objectives"]["tower"].index(point) - 1]))
                    canvas.create_line(previous[0], previous[1], reflected[0], reflected[1], width=3 * zoom,
                                       fill=LIGHT_GREEN)
        if level["symmetryPoint"] and len(level["objectives"]["tower"]) > 0 and showSymmetry:
            previous = toScreen(level["objectives"]["tower"][0 if level["towerStart"] else -1])
            reflected = toScreen(symmetrical(level["objectives"]["tower"][0 if level["towerStart"] else -1]))
            mid = [(previous[0] + reflected[0]) / 2, (previous[1] + reflected[1]) / 2]
            canvas.create_line(previous[0], previous[1], mid[0], mid[1], width=3 * zoom, fill=LIGHT_PURPLE)
            canvas.create_line(mid[0], mid[1], reflected[0], reflected[1], width=3 * zoom, fill=LIGHT_GREEN)
    elif currentLayer == 4:
        maker = False  # this there already a rainmaker or should the symmetry point decide the position
        for podium in level["objectives"]["rain"]:
            fill = PURPLE if len(podium) == 2 else YELLOW
            size = 25 * zoom if len(podium) == 2 else 15 * zoom
            absolute = toScreen(podium)
            reflected = toScreen(symmetrical(podium))
            canvas.create_oval(absolute[0] - size, absolute[1] - size, absolute[0] + size, absolute[1] + size,
                               fill=fill, outline=LIGHT_PURPLE, width=5 * zoom)
            if level["symmetryPoint"] and showSymmetry:
                if len(podium) < 3:
                    canvas.create_oval(reflected[0] - size, reflected[1] - size, reflected[0] + size,
                                       reflected[1] + size,
                                       fill=GREEN, outline=LIGHT_GREEN, width=5 * zoom)
                else:
                    maker = True
        if not maker and level["symmetryPoint"] and showSymmetry:
            point = toScreen(level["symmetryPoint"])
            canvas.create_oval(point[0] - 15, point[1] - 15, point[0] + 15, point[1] + 15, fill=YELLOW,
                               outline=LIGHT_PURPLE, width=5 * zoom)
    elif currentLayer == 5:
        for objective in level["objectives"]["clams"]:
            absolute = toScreen(objective)
            reflected = toScreen(symmetrical(objective))
            if len(objective) > 2:
                canvas.create_rectangle(absolute[0] - 25 * zoom, absolute[1] - 25 * zoom, absolute[0] + 25 * zoom,
                                        absolute[1] + 25 * zoom, fill=PURPLE, outline=LIGHT_PURPLE, width=5 * zoom,
                                        stipple="@" + resource_path("images\\mesh.xbm"))
            else:
                canvas.create_oval(absolute[0] - 5 * zoom, absolute[1] - 5 * zoom, absolute[0] + 5 * zoom,
                                   absolute[1] + 5 * zoom, fill=PURPLE,
                                   outline=LIGHT_PURPLE, width=2 * zoom)

            if level["symmetryPoint"] and showSymmetry:
                if len(objective) > 2:
                    canvas.create_rectangle(reflected[0] - 25 * zoom, reflected[1] - 25 * zoom,
                                            reflected[0] + 25 * zoom,
                                            reflected[1] + 25 * zoom, fill=GREEN, outline=LIGHT_GREEN, width=5 * zoom,
                                            stipple="@" + resource_path("images\\mesh.xbm"))
                else:
                    canvas.create_oval(reflected[0] - 5 * zoom, reflected[1] - 5 * zoom, reflected[0] + 5 * zoom,
                                       reflected[1] + 5 * zoom, fill=GREEN,
                                       outline=LIGHT_GREEN, width=2 * zoom)


def drawMisc(canvas):
    for sponge in level["sponges"]:
        if sponge[2] != currentLayer and sponge[2] != 0: continue
        screen = toScreen(sponge)
        canvas.create_rectangle(screen[0], screen[1], screen[0] + 32 * zoom, screen[1] + 32 * zoom, fill=PURPLE,
                                width=0)
        if level["symmetryPoint"] and showSymmetry:
            screen = toScreen(symmetrical(sponge))
            secondPoint = toScreen(symmetrical([sponge[0] + 32, sponge[1] + 32]))
            secondPoint = [secondPoint[0], secondPoint[1]]
            canvas.create_rectangle(screen[0], screen[1], secondPoint[0], secondPoint[1], fill=GREEN,
                                    width=0)

    for rail in level["rails"]:
        if rail[0][2] != currentLayer and rail[0][2] != 0: continue
        for point in rail:
            screen = toScreen(point)
            screenSymm = toScreen(symmetrical(point))
            size = 10 * zoom if rail.index(point) == 0 else 5 * zoom
            canvas.create_oval(screen[0] - size, screen[1] - size, screen[0] + size, screen[1] + size, fill=PURPLE,
                               width=0)
            if level["symmetryPoint"] and showSymmetry:
                canvas.create_oval(screenSymm[0] - size, screenSymm[1] - size, screenSymm[0] + size,
                                   screenSymm[1] + size, fill=GREEN,
                                   width=0)
            if rail.index(point) > 0:
                prev = toScreen(rail[rail.index(point) - 1])
                canvas.create_line(screen[0], screen[1], prev[0], prev[1], fill=PURPLE, width=2)
                if level["symmetryPoint"] and showSymmetry:
                    prevSymm = toScreen(symmetrical(rail[rail.index(point) - 1]))
                    canvas.create_line(screenSymm[0], screenSymm[1], prevSymm[0], prevSymm[1], fill=GREEN, width=2)

    if len(level["spawn"]) == 2:
        size = 40 * zoom
        screen = toScreen(level["spawn"])
        canvas.create_oval(screen[0] - size, screen[1] - size, screen[0] + size, screen[1] + size, fill=PURPLE,
                           outline=LIGHT_GREY, width=8 * zoom)
        if level["symmetryPoint"] and showSymmetry:
            reflected = toScreen(symmetrical(level["spawn"]))
            canvas.create_oval(reflected[0] - size, reflected[1] - size, reflected[0] + size, reflected[1] + size,
                               fill=GREEN,
                               outline=LIGHT_GREY, width=8 * zoom)
root.title("Splatographer | loading.")
root.update()
time.sleep(0.5) #  so the program doesn't try to draw things while the resize events are happening...
while not dead:
    if hash(str(level)) != previousHash:
        previousHash = hash(str(level))
        askSave = True

    if path == "":
        root.title("Splatographer | No File")
    else:
        if not os.path.exists(path):
            root.title("Splatographer | " + path + " [WARNING] path does not appear to lead to a valid file [WARNING]")
        else:
            root.title("Splatographer | " + path + (" Not saved*" if askSave else " Saved!"))

    zero = toScreen([0, 0])

    if selectedIndex < 0:
        level["floors"] = sorted(level["floors"], key=lambda x: x["height"])
    canvas.delete("all")
    if drawGrid:
        yval = camera[1] % grid * zoom
        while yval < camera[1] % grid * zoom + canvas.winfo_height():
            canvas.create_line(0, yval, canvas.winfo_width(), yval, fill=LIGHT_BLUE)
            yval += grid * zoom

        xval = camera[0] % grid * zoom
        while xval < camera[0] % grid * zoom + canvas.winfo_width():
            canvas.create_line(xval, 0, xval, canvas.winfo_height(), fill=LIGHT_BLUE)
            xval += grid * zoom

    canvas.create_rectangle(zero[0] - 5 * zoom, zero[1] - 5 * zoom, zero[0] + 5 * zoom, zero[1] + 5 * zoom, fill=YELLOW)

    drawFloors(canvas)

    if level["symmetryPoint"]:
        pointWidth = 2 * zoom
        screen = toScreen(level["symmetryPoint"])
        canvas.create_rectangle(screen[0] - pointWidth, screen[1] - pointWidth,
                                screen[0] + pointWidth, screen[1] + pointWidth,
                                fill=TOMATO)

    tempPointWidth = 4 * zoom
    for point in tempPoints:
        absolute = toScreen(point)
        canvas.create_rectangle(absolute[0] - tempPointWidth, absolute[1] - tempPointWidth,
                                absolute[0] + tempPointWidth,
                                absolute[1] + tempPointWidth, fill=RED)

        if len(tempPoints) >= 2:
            prev = toScreen(tempPoints[(tempPoints.index(point) - 1) % len(tempPoints)])
            canvas.create_line(*absolute, *prev, fill=TOMATO)

    drawObjectives(canvas)

    drawMisc(canvas)

    if placing:
        mpoint = mousePos
        if snapping:
            mpoint = toScreen(snappedMouse())
        canvas.create_rectangle(mpoint[0] - 2, mpoint[1] - 2, mpoint[0] + 2, mpoint[1] + 2, fill=YELLOW)

    canvas.create_text(5, 5, text="Grid: {} Snap: {} Layer: {} Zoom {}% Mouse: {} placemode: {}".format(grid, snapping,
                                                                                          layerKey[currentLayer],
                                                                                          round(zoom * 100),
                                                                                          snappedMouse(),
                                                                                          placeStrings[placemode]),
                       fill=YELLOW, anchor="nw",
                       font=['sans-sarif', 12])
    canvas.create_text(5, canvas.winfo_height() - 22, text=str(keys), fill=YELLOW, anchor="nw", font=["sans-sarif", 12])
    root.update()

    if time.time() - autosave_time > autosave_interval and os.path.exists(path) and autosave_interval > 0:
        autosave_time = time.time()
        save()
        print("Autosaved to file.")
