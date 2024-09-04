import json
import math
import os.path
import re
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import simpledialog

from shapely.affinity import translate
from shapely.geometry import Polygon, Point, mapping

VERSION = 0.5

print("Splatographer version: " + str(VERSION))

autosave_time = time.time()

path = ""

levelTemplate = {
    "spawn": [], # A coordinate pair for where the spawnpoint should be.
    "floors": [],
    "symmetryPoint": [],  # The point at which symmetry occurs, empty if not defined.
    "rotated": "rotated",  # is this level rotated or flipped? valid values: rotated, x, y
    "towerStart": True, # the "start" of the tower path is either index 0 or -1 if this value is True or False respectively
    "objectives": {
        "zones": [],  # list of splatzones, each zone is a list of points
        "tower": [],  # list of points which lay out the path, a third entry can make the point a checkpoint.
        "rain": [],  # list of coordinates for podiums be them checkpoints or goals, third entry in a datapoint can be the rainmaker itself if needed.
        "clams": []  # basket coordinates
    }
}

level = levelTemplate.copy()

## Coded by Seamus Donahue, feel free to mod/redistribute but I just ask that you leave alone the credit to me :)

tempPoints = []
copiedFloor = {}

grid = 32
camera = [0, 0]
zoom = 1
drawGrid = True
snapping = True
heightIncrement = 10
currentLayer = 0
layerKey = ["all", "turf", "zones", "tower", "rain", "clams"]  # which layer is what

askSave = False
previousHash = hash(str(level))
preferences = {
    "grid": 32,
    "height_increment": 10,
    "snap": True
}
showSymmetry = True

settingsPath = os.getcwd() + "\\settings.json"

"""
compile with pyInstaller:
pyinstaller --noconfirm --onefile --windowed --add-data "./images;images/" --icon "images/mappericon.ico"  "./main.py"
"""


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
    if len(newPath) > 0:
        if re.search("(?:\.splat)$", newPath):
            path = newPath
            with open(path, "r") as f:
                level = json.loads(f.read())
                validateLevel()
            camera = [-grid, -grid]
            askSave = False
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


def makeInkable(*args):
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["type"] = 0


def makeUninkable(*args):
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["type"] = 1


def makeGrate(*args):
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["type"] = 2


def deleteFloor(*args):
    global selectedIndex
    if selectedIndex in range(len(level["floors"])):
        level["floors"].remove(level["floors"][selectedIndex])
        selectedIndex = -1


def changeLayer(event):
    global currentLayer
    currentLayer = int(event.keysym)


def xflip():
    level["rotated"] = "x"


def yflip():
    level["rotated"] = "y"


def rotatenotflip():
    level["rotated"] = "rotated"


# these have to be here to put them in the menu... I hate it
def layer0():
    global currentLayer
    currentLayer = 0


def layer1():
    global currentLayer
    currentLayer = 1


def layer2():
    global currentLayer
    currentLayer = 2


def layer3():
    global currentLayer
    currentLayer = 3


def layer4():
    global currentLayer
    currentLayer = 4


def layer5():
    global currentLayer
    currentLayer = 5


def applySettings():
    global grid
    global heightIncrement
    global snapping
    global preferences
    if not os.path.exists(settingsPath):
        with open(settingsPath, "w") as f:
            f.write(json.dumps(preferences))
    with open(settingsPath, "r") as f:
        preferences = preferences | json.loads(f.read())

    grid = int(preferences["grid"])
    heightIncrement = preferences["height_increment"]
    snapping = preferences["snap"]


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


root = tk.Tk()  ##create window
root.iconbitmap(resource_path("images\\mappericon.ico"))
root.geometry("1600x900")

root.config(background="#222222")

topBar = tk.Menu(root, fg="white")
fileMenu = tk.Menu(topBar, tearoff=0)
fileMenu.add_command(label="New Map", command=newFile)
fileMenu.add_command(label="Open Map", command=openFile)
fileMenu.add_command(label="Save Map", command=save)
fileMenu.add_command(label="preferences", command=settingsWindow)

floorMenu = tk.Menu(topBar, tearoff=0)
floorMenu.add_command(label="raise (↑)", command=floorUp)
floorMenu.add_command(label="lower (↓)", command=floorDown)
floorMenu.add_command(label="change height increment", command=askHeightIncrement)
floorMenu.add_command(label="make inkable (i)", command=makeInkable)
floorMenu.add_command(label="make uninkable (u)", command=makeUninkable)
floorMenu.add_command(label="make grate (g)", command=makeGrate)
floorMenu.add_separator()
floorMenu.add_command(label="delete floor (delete or backspace)", command=deleteFloor)

layerMenu = tk.Menu(topBar, tearoff=0)
layerMenu.add_command(label="all (0)", command=layer0)
layerMenu.add_separator()
layerMenu.add_command(label="turf (1)", command=layer1)
layerMenu.add_command(label="zones (2)", command=layer2)
layerMenu.add_command(label="tower (3)", command=layer3)
layerMenu.add_command(label="rain (4)", command=layer4)
layerMenu.add_command(label="clams (5)", command=layer5)

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

canvas = tk.Canvas(root, width=1600, height=900, background=DARK_BLUE)
canvas.pack()

root.bind(sequence="<Control-o>", func=openFile)
root.bind(sequence="<Control-s>", func=save)
root.bind(sequence="<Control-n>", func=newFile)
root.bind(sequence="<Delete>", func=deleteFloor)
root.bind(sequence="<BackSpace>", func=deleteFloor)
root.bind(sequence="<]>", func=gridinc)
root.bind(sequence="<[>", func=griddec)
root.bind(sequence="<i>", func=makeInkable)
root.bind(sequence="<u>", func=makeUninkable)
root.bind(sequence="<g>", func=makeGrate)
root.bind(sequence="<Control-c>", func=copy)
root.bind(sequence="<Control-v>", func=paste)
root.bind(sequence="<Control-r>", func=setSymmetry)

for i in range(6):
    root.bind(sequence=str(i), func=changeLayer)

root.config(menu=topBar)

keys = []


def keypress(event):
    if not event.keysym in keys:
        keys.append(event.keysym)

    # I really want to make this a match statement but I don't really know how I can
    if "Up" in keys and selectedIndex != -1:
        floorUp()
    if "Down" in keys and selectedIndex != -1:
        floorDown()


def keyrelease(event):
    if event.keysym in keys:
        keys.remove(event.keysym)

    global tempPoints
    if event.keysym == "Shift_L" and len(tempPoints) > 0:
        if len(tempPoints) <= 2:
            tempPoints = []
            return
        level["floors"].append({"points": tempPoints, "type": 0, "height": 100, "layer": currentLayer})
        tempPoints = []


dragPrevious = [0, 0]

mousePos = [0, 0]
selectedIndex = -1
deleteDistance = 5


def updateMousePos(event):
    global mousePos
    mousePos = [event.x, event.y]


def mouseDrag(event):
    global dragPrevious
    camera[0] -= dragPrevious[0] - event.x
    camera[1] -= dragPrevious[1] - event.y
    dragPrevious = [event.x, event.y]


def mousePress(event):
    global dragPrevious
    global selectedIndex
    dragPrevious = [event.x, event.y]

    if "Shift_L" in keys:
        placeObjective(event)
    elif "Control_L" in keys:
        level["spawn"] = snappedMouse()
    else:
        selected = False
        for floor in level["floors"]:
            if Point(fromScreen(mousePos)).within(Polygon(floor["points"])):
                selectedIndex = level["floors"].index(floor)
                selected = True

        if not selected: selectedIndex = -1


def rclickPress(event):
    if "Shift_L" in keys:
        point = snappedMouse()

        for tempPoint in tempPoints:
            distance = ((point[0] - tempPoint[0]) ** 2 + (point[1] - tempPoint[1]) ** 2) ** 0.5
            if distance < deleteDistance:
                tempPoints.remove(tempPoint)
                return

        tempPoints.append(point)


def configEvent(event):
    canvas.config(width=event.width, height=event.height)


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

        if len(tempPoints) < 3: return
        level["objectives"][layerKey[currentLayer]].append(tempPoints)
        tempPoints = []
    else:
        for objective in level["objectives"][layerKey[currentLayer]]:
            distance = ((objective[0] - snappedMouse()[0]) ** 2 + (objective[1] - snappedMouse()[1]) ** 2) ** 0.5
            if distance < grid / 2:
                level["objectives"][layerKey[currentLayer]].remove(objective)
                return
        level["objectives"][layerKey[currentLayer]].append(snappedMouse())
        if (currentLayer >= 3) and "Control_L" in keys:
            if currentLayer == 4:
                for point in level["objectives"]["rain"]: #make sure only one rainmaker exists
                    if len(point) > 2:
                        level["objectives"]["rain"].remove(point)
                        break
            level["objectives"][layerKey[currentLayer]][-1].append(True)


root.bind("<KeyPress>", keypress)
root.bind("<KeyRelease>", keyrelease)
root.bind("<Configure>", configEvent)

canvas.bind("<B1-Motion>", mouseDrag)
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

if len(sys.argv) >= 3:
    if sys.argv[1] == "-f":
        valid = os.path.exists(sys.argv[2])

        if valid:
            path = sys.argv[2]
            with open(path, "r") as f:
                level = json.loads(f.read())
        else:
            messagebox.showerror(title="Invalid file", message="The file being opened does not exist!")

applySettings()

dead = False

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

    canvas.create_rectangle(zero[0] - 5, zero[1] - 5, zero[0] + 5, zero[1] + 5, fill=YELLOW)

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

        for point in drawSymmetry:
            canvas.create_rectangle(point[0] - 1, point[1] - 1, point[0] + 1, point[1] + 1, fill="black")

    if level["symmetryPoint"]:
        screen = toScreen(level["symmetryPoint"])
        canvas.create_rectangle(screen[0] - 2, screen[1] - 2,
                                screen[0] + 2, screen[1] + 2,
                                fill=TOMATO)

    for point in tempPoints:
        absolute = toScreen(point)
        canvas.create_rectangle(absolute[0] - 4, absolute[1] - 4, absolute[0] + 4,
                                absolute[1] + 4, fill=RED)

    #objective drawing
    if currentLayer == 2:
        for zone in level["objectives"]["zones"]:
            for index in range(len(zone)):
                canvas.create_line(toScreen(zone[index]), toScreen(zone[(index - 1) % len(zone)]), fill=PURPLE, width=3)
                if level["symmetryPoint"] and showSymmetry:
                    canvas.create_line(toScreen(symmetrical(zone[index])), toScreen(symmetrical(zone[(index - 1) % len(zone)])), fill=GREEN, width=3)
    elif currentLayer == 3:
        for point in level["objectives"]["tower"]:
            width = 2 if len(point) == 2 else 25 * zoom
            absolute = toScreen(point)
            reflected = toScreen(symmetrical(point))
            canvas.create_rectangle(absolute[0] - width, absolute[1] - width, absolute[0] + width,
                                    absolute[1] + width, fill=PURPLE, outline=LIGHT_PURPLE, width=1)
            if level["objectives"]["tower"].index(point) > 0:
                previous = toScreen(level["objectives"]["tower"][level["objectives"]["tower"].index(point) - 1])
                canvas.create_line(previous[0], previous[1], absolute[0], absolute[1], width=3, fill=LIGHT_PURPLE)

            if level["symmetryPoint"] and showSymmetry:
                canvas.create_rectangle(reflected[0] - width, reflected[1] - width, reflected[0] + width,
                                        reflected[1] + width, fill=GREEN, outline=LIGHT_GREEN, width=1)
                if level["objectives"]["tower"].index(point) > 0:
                    previous = toScreen(symmetrical(level["objectives"]["tower"][level["objectives"]["tower"].index(point) - 1]))
                    canvas.create_line(previous[0], previous[1], reflected[0], reflected[1], width=3, fill=LIGHT_GREEN)
        if level["symmetryPoint"] and len(level["objectives"]["tower"]) > 0 and showSymmetry:
            previous = toScreen(level["objectives"]["tower"][0 if level["towerStart"] else -1])
            reflected = toScreen(symmetrical(level["objectives"]["tower"][0 if level["towerStart"] else -1]))
            mid = [(previous[0] + reflected[0]) / 2, (previous[1] + reflected[1]) / 2]
            canvas.create_line(previous[0], previous[1], mid[0], mid[1], width=3, fill=LIGHT_PURPLE)
            canvas.create_line(mid[0], mid[1], reflected[0], reflected[1], width=3, fill=LIGHT_GREEN)
    elif currentLayer == 4:
        maker = False # this there already a rainmaker or should the symmetry point decide the position
        for podium in level["objectives"]["rain"]:
            fill = PURPLE if len(podium) == 2 else YELLOW
            size = 25 if len(podium) == 2 else 15
            absolute = toScreen(podium)
            reflected = toScreen(symmetrical(podium))
            canvas.create_oval(absolute[0] - size, absolute[1] - size, absolute[0] + size, absolute[1] + size, fill=fill, outline=LIGHT_PURPLE, width=5)
            if level["symmetryPoint"] and showSymmetry:
                if len(podium) < 3:
                    canvas.create_oval(reflected[0] - size, reflected[1] - size, reflected[0] + size, reflected[1] + size,
                                   fill=GREEN, outline=LIGHT_GREEN, width=5)
                else:
                    maker = True
        if not maker and level["symmetryPoint"] and showSymmetry:
            point = toScreen(level["symmetryPoint"])
            canvas.create_oval(point[0] - 15, point[1] - 15, point[0] + 15, point[1] + 15, fill=YELLOW, outline=LIGHT_PURPLE, width=5)
    elif currentLayer == 5:
        for objective in level["objectives"]["clams"]:
            absolute = toScreen(objective)
            reflected = toScreen(symmetrical(objective))
            if len(objective) > 2:
                canvas.create_rectangle(absolute[0] - 25 * zoom, absolute[1] - 25 * zoom, absolute[0] + 25 * zoom, absolute[1] + 25 * zoom, fill=PURPLE, outline=LIGHT_PURPLE, width=5, stipple="@" + resource_path("images\\mesh.xbm"))
            else:
                canvas.create_oval(absolute[0] - 5, absolute[1] - 5, absolute[0] + 5, absolute[1] + 5, fill=PURPLE,
                                   outline=LIGHT_PURPLE, width=2)

            if level["symmetryPoint"] and showSymmetry:
                if len(objective) > 2:
                    canvas.create_rectangle(reflected[0] - 25 * zoom, reflected[1] - 25 * zoom, reflected[0] + 25 * zoom,
                                            reflected[1] + 25 * zoom, fill=GREEN, outline=LIGHT_GREEN, width=5,
                                            stipple="@" + resource_path("images\\mesh.xbm"))
                else:
                    canvas.create_oval(reflected[0] - 5, reflected[1] - 5, reflected[0] + 5, reflected[1] + 5, fill=GREEN,
                                       outline=LIGHT_GREEN, width=2)

    if len(level["spawn"]) == 2:
        screen = toScreen(level["spawn"])
        canvas.create_oval(screen[0] - 40, screen[1] - 40, screen[0] + 40, screen[1] + 40, fill=PURPLE, outline=LIGHT_GREY, width=8)
        if level["symmetryPoint"] and showSymmetry:
            reflected = toScreen(symmetrical(level["spawn"]))
            canvas.create_oval(reflected[0] - 40, reflected[1] - 40, reflected[0] + 40, reflected[1] + 40, fill=GREEN,
                               outline=LIGHT_GREY, width=8)
    if "Shift_L" in keys:
        mpoint = snappedMouse()
        if snapping:
            mpoint = toScreen(mpoint)
        canvas.create_rectangle(mpoint[0] - 2, mpoint[1] - 2, mpoint[0] + 2, mpoint[1] + 2, fill=YELLOW)

    canvas.create_text(5, 5, text="Grid: {} Snap: {} Layer: {} Zoom {}%".format(grid, snapping, layerKey[currentLayer],
                                                                                round(zoom * 100)),
                       fill=YELLOW, anchor="nw",
                       font=['sans-sarif', 12])
    root.update()

    if time.time() - autosave_time > 180 and os.path.exists(path):
        autosave_time = time.time()
        save()
        print("Autosaved to file.")
