#!/usr/bin/env python3

import subprocess
import sys
import math
from time import sleep
from PIL import Image, ImageFilter
from gi.repository import Gtk

import pygame
import pygame.gfxdraw
import lirc

WINDOW_NAME = 'lirclauncher'

#Rough theory of operation:
#Process APPS, get icons
#Take background, Gauss. Blur it, add some white to make it stand out
#Put original background on screen
#Take chunks of blurred background as backdrops for icons
#Allow user to select app with LIRC or keyboard with arrow and ENTER keys

#Start lirc listener
lirc_sock = lirc.init(WINDOW_NAME, "./lircrc", blocking=False)

def pilToPygame(img):
    mode = img.mode
    size = img.size
    data = img.tobytes()
    return pygame.image.fromstring(data, size, mode)

#this is used to get icons.
icon_theme = Gtk.IconTheme.get_default()

#Import our list of APPS.
#Format of settings.config:
#Custom:Name_Of_Application:Application_Command_Line:Icon_Path
# OR #
#Custom:Name_Of_Application:Application_Command_Line:Icon_Path:lircrc_Button_Code
#eg:
#Custom:Exit:pkill -1 -f run.py:./exit.png
APPS_COMPLETE = []
APPS = []
LIRCRC_APPS = {}
settingsFile = open("settings.config")
settingsLines = settingsFile.readlines()
for i, line in enumerate(settingsLines):
    line = line.rstrip()
    if line.find("Custom") == -1:
        APPS.append(line)
    else:
        customStuff = line.split(":")
        APPS_COMPLETE.append({"icon": customStuff[3],
                              "exec": customStuff[2].split(" "),
                              "name": customStuff[1]})
        if len(customStuff) == 5: # has lircrc button field
            LIRCRC_APPS[customStuff[4]] = i

pygame.init()
pygame.display.set_caption(WINDOW_NAME)
WINDOW_ID = subprocess.check_output('DISPLAY=:0 xdotool search --name %s' %
        WINDOW_NAME, shell=True).decode('utf-8').rstrip()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

infoObject = pygame.display.Info()

pygame.mouse.set_visible(False)


image = Image.open("background.jpg")
width,height =  image.size
#Scale our image to fit the screen
#Yes, this loses aspect ratio, but it's better than black bars,
# and 1080p/1440p/720p wallpapers are easy to find.
image = image.resize((infoObject.current_w, infoObject.current_h), Image.ANTIALIAS)

imageDraw = image #This is what we're actually going to draw.
mode = imageDraw.mode
size = imageDraw.size
data = imageDraw.tobytes()

backdrop = pygame.image.fromstring(data, size, mode)


#need this to highlight behind icons.
whiteFull = Image.new("RGB", (infoObject.current_w, infoObject.current_h), "white")

z = image
z = Image.blend(z, whiteFull, 0.2)
z = z.filter(ImageFilter.GaussianBlur(radius = 10))


#This length is a little weird.
#We currently have processed custom APPS and unprocessed .desktop names in two different arrays
# which are about to be combined.
intvl = int(math.floor(infoObject.current_w /
            ((len(APPS) + len(APPS_COMPLETE)) * 2 + 1)))


#middle of the screen
middleT = int(math.floor(infoObject.current_h / 2)) - int(float(intvl) / float(2))


#We're parsing .desktop files to get icon, name (currently unused), and executable path.
for app in APPS:
    f = open("/usr/share/applications/" + app + ".desktop")
    lns = f.readlines()
    name = ""
    exePath = ""
    iconPath = None
    for x in lns:
        x = x.rstrip()
        if x.find("Name") != -1 and name == "":
            name = x.split("=")[1]
        if x.find("Exec") != -1 and exePath == "":
            #exePath = re.sub(r'%.', '', x.split("=")[1]).replace("\n", "").split(" ")
            exePath = (' '.join(list(filter(lambda i: not i.startswith('%'),
                                            x.split('=')[1].split(' ')))))
        if x.find("Icon") != -1 and iconPath is None:
            iconPath = x.split("=")[1]
            iconPath = iconPath.replace(" ", "")
            if iconPath.find("/") == -1:
                iconPath = icon_theme.lookup_icon(iconPath, 1024, 0).get_filename()
    APPS_COMPLETE.append({"icon": iconPath, "name": name, "exec": exePath})

#Process & scale icons once.
for app in APPS_COMPLETE:
    icon = Image.open(app["icon"])
    width,height = icon.size
    ratio = min(float(intvl - 50) / float(width), float((intvl - 50)) / float(height))

    icon = icon.resize((int(width * ratio), int(height * ratio)), Image.ANTIALIAS)
    app["icon"] = pilToPygame(icon)


#These are the list of icon backdrops, cropped properly.
imgs = []
for i in range(len(APPS_COMPLETE)):
    imgs.append(pilToPygame(z.crop((intvl * ((2 * i) + 1), middleT,
                                    intvl * ((2 * i) + 1) + intvl,
                                    middleT + intvl))))

#Draw everything!
def draw(highlight):
    global APPS_COMPLETE, intvl, middleT, backdrop, APPS

    screen.blit(backdrop, (0,0))

    for i in range(len(APPS_COMPLETE)):
        screen.blit(imgs[i], (intvl * ((2 * i) + 1), middleT))
    #Scale and draw app icons
    for i, app in enumerate(APPS_COMPLETE):
        screen.blit(app["icon"], (intvl * ((2 * i) + 1) + 25, middleT + 25))

    pygame.draw.rect(screen, (0, 0, 128), (intvl * ((2 * highlight) + 1),
                     middleT, intvl, intvl), 10)
    pygame.display.flip()


current = 0 # index of selected icon/program
draw(current)
menu_proc = subprocess.Popen(['sleep', '0']) # subprocess id of chosen menu item (pmp, kodi, etc)
watch_proc = subprocess.Popen(['sleep', '0']) # subprocess id of xscreensaver watcher

while True:
    def get_focused():
        subprocess.call('xdotool windowfocus %s' % WINDOW_ID, shell=True)
        start_watcher()

    def start_watcher():
        global watch_proc

        watch_proc = subprocess.Popen(['./xscreensaver-watcher.pl'])

    def call_by_index(index):
        global menu_proc

        draw(current)

        exec_name = APPS_COMPLETE[index]['name']
        exec_cmd = APPS_COMPLETE[index]['exec']
        print('Opening %s' % exec_name)
        if exec_name == 'Exit':
            exit_menu()
        menu_proc = subprocess.Popen(exec_cmd)

    def move_current(direction):
        global current

        if direction == 'left':
            current = max(0, current - 1)
        elif direction == 'right':
            current = min(len(APPS_COMPLETE) - 1, current + 1)

        draw(current)
        subprocess.call('xscreensaver-command -deactivate', shell=True)

    def exit_menu():
        lirc.deinit()
        watch_proc.terminate()
        sys.exit()

    if watch_proc.poll() is not None:
        # xscreensaver 'unblanked' or first trip through loop
        get_focused()

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN: # key pressed
            if event.key == pygame.K_LEFT:
                move_current('left')
            if event.key == pygame.K_RIGHT:
                move_current('right')
            if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                # App has been selected
                call_by_index(current)

    lirc_input = lirc.nextcode()

    if lirc_input != [] and menu_proc.poll() is not None: # remote button pressed
        ir_code = lirc_input.pop()
        if ir_code == "Left":
            move_current('left')
        if ir_code == "Right":
            move_current('right')
        if ir_code == "Return":
            # App has been selected with arrow and OK buttons
            call_by_index(current)

        # Specific calls via Harmony Remote (mceusb) and lirc
        # current will not point to the right program
        # See lircrc file
        if ir_code in LIRCRC_APPS:
            current = LIRCRC_APPS[ir_code]
            call_by_index(current)

        # if ir_code == "die":
        #    break

    if menu_proc.poll() is not None:
        pygame.display.flip()

    sleep(0.1)
