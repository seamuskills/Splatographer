import json
import os.path
import re
import sys
import time
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog, messagebox
from shapely.geometry import Polygon, Point

VERSION = 0.1

print("Splatographer version: " + str(VERSION))

autosave_time = time.time()

path = ""

level = {
    "floors": []
}

## Coded by Seamus Donahue, feel free to mod/redistribute but I just ask that you leave the credit to me alone :)

"""
temp points will hold points to be closed into a shape on the release of the shift key
then the shape will be added to level["floors"] in this format:
{"points": [points array], "type": 0-2, "height": 0-100, layer = int}
points is the array of points
type is the following: 0 inkable, 1 uninkable, 3 grates
height is the percentile height of the floor that decides its color
layer will decide the draw order in theory...
"""

tempPoints = []

grid = 32
camera = [0, 0]
drawGrid = True
snapping = True
heightIncrement = 10

askSave = False
previousHash = hash(str(level))

def toggleGrid():
    global drawGrid
    drawGrid = not drawGrid


def toggleSnap():
    global snapping
    snapping = not snapping


def resetCamera():
    global camera
    camera = [16, 16]


YELLOW = "#F9C622"
DARK_BLUE = "#0F2129"
LIGHT_BLUE = "#1E8798"
PURPLE = "#6342f5"
RED = "#ff3f14"


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
    newIncrement = simpledialog.askinteger("New height increment", "How many units should the raise and lower command modify a floors height by?")

def makeInkable():
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["type"] = 0

def makeUninkable():
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["type"] = 1

def makeGrate():
    if selectedIndex in range(len(level["floors"])):
        level["floors"][selectedIndex]["type"] = 2

def deleteFloor(*args):
    global selectedIndex
    if selectedIndex in range(len(level["floors"])):
        level["floors"].remove(level["floors"][selectedIndex])
        selectedIndex = -1

root = tk.Tk()  ##create window
root.iconbitmap("images/mappericon.ico")
root.geometry("1600x900")

root.config(background="#222222")

topBar = tk.Menu(root, fg="white")
fileMenu = tk.Menu(topBar, tearoff=0)
fileMenu.add_command(label="New Map", command=newFile)
fileMenu.add_command(label="Open Map", command=openFile)
fileMenu.add_command(label="Save Map", command=save)

floorMenu = tk.Menu(topBar, tearoff=0)
floorMenu.add_command(label="raise (↑)", command=floorUp)
floorMenu.add_command(label="lower (↓)", command=floorDown)
floorMenu.add_command(label="change height increment", command=askHeightIncrement)
floorMenu.add_command(label="make inkable", command=makeInkable)
floorMenu.add_command(label="make uninkable", command=makeUninkable)
floorMenu.add_command(label="make grate", command=makeGrate)
floorMenu.add_separator()
floorMenu.add_command(label="delete floor (delete or backspace)", command=deleteFloor)

topBar.add_cascade(label="File", menu=fileMenu)
topBar.add_cascade(label="Floor", menu=floorMenu)
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
        level["floors"].append({"points": tempPoints, "type": 0, "height": 50, "layer": 0})
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

    selected = False
    for floor in level["floors"]:
        if Point(mousePos[0] - camera[0], mousePos[1] - camera[1]).within(Polygon(floor["points"])):
            selectedIndex = level["floors"].index(floor)
            selected = True

    if not selected: selectedIndex = -1


def rclickPress(event):
    if "Shift_L" in keys:
        point = [event.x - camera[0], event.y - camera[1]]
        if snapping:
            point[0] -= point[0] % grid
            point[1] -= point[1] % grid

        for tempPoint in tempPoints:
            distance = ((point[0] - tempPoint[0]) ** 2 + (point[1] - tempPoint[1])**2) ** 0.5
            if distance < deleteDistance:
                tempPoints.remove(tempPoint)
                return

        tempPoints.append(point)


root.bind("<KeyPress>", keypress)
root.bind("<KeyRelease>", keyrelease)

canvas.bind("<B1-Motion>", mouseDrag)
canvas.bind("<Motion>", updateMousePos)
canvas.bind("<Button-1>", mousePress)
canvas.bind("<Button-3>", rclickPress)


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

    if selectedIndex < 0:
        level["floors"] = sorted(level["floors"], key=lambda x: x["height"])
    canvas.delete("all")
    if drawGrid:
        for y in range(camera[1] % grid, camera[1] % grid + 900, grid):
            canvas.create_line(0, y, 1600, y, fill=LIGHT_BLUE)
        for x in range(camera[0] % grid, camera[0] % grid + 1600, grid):
            canvas.create_line(x, 0, x, 900, fill=LIGHT_BLUE)

    canvas.create_rectangle(camera[0] - 5, camera[1] - 5, camera[0] + 5, camera[1] + 5, fill=YELLOW)

    for floor in level["floors"]:
        drawPoly = []
        for i in floor["points"]:
            drawPoly.append([i[0] + camera[0], i[1] + camera[1]])

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
            if floor["type"] == 1:
                canvas.create_polygon(*drawPoly, fill="white" if level["floors"].index(floor) != selectedIndex else YELLOW, stipple="@images/uninkable.xbm")
        else:
            canvas.create_polygon(*drawPoly, fill=fill,
                                  stipple="@images/grate.xbm")
        for point in drawPoly:
            canvas.create_rectangle(point[0] - 1, point[1] - 1, point[0] + 1, point[1] + 1, fill="black")

    for point in tempPoints:
        canvas.create_rectangle(camera[0] + point[0] - 4, camera[1] + point[1] - 4, camera[0] + point[0] + 4, camera[1] + point[1] + 4, fill=RED)

    if "Shift_L" in keys:
        mpoint = [mousePos[0], mousePos[1]]
        if snapping:
            mpoint = [mpoint[0] - camera[0], mpoint[1] - camera[1]]
            mpoint[0] -= mpoint[0] % grid
            mpoint[1] -= mpoint[1] % grid
            mpoint = [mpoint[0] + camera[0], mpoint[1] + camera[1]]
        canvas.create_rectangle(mpoint[0] - 2, mpoint[1] - 2, mpoint[0] + 2, mpoint[1] + 2, fill=YELLOW)

    canvas.create_text(5, 5, text="Grid: {} Snap: {}".format(grid, snapping), fill=YELLOW, anchor="nw",
                       font=['sans-sarif', 12])
    root.update()

    if time.time() - autosave_time > 180 and os.path.exists(path):
        autosave_time = time.time()
        save()
        print("Autosaved to file.")