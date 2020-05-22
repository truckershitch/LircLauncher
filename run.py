#!/usr/bin/env python3

import pygame
import pygame.gfxdraw
import subprocess
import sys
from PIL import Image, ImageFilter, ImageChops
import math
import gi
from gi.repository import Gtk
#import re
import lirc
import os

WAIT_TICKS = 20000

#Rough theory of operation:
#Process apps, get icons
#Take background, Gauss. Blur it, add some white to make it stand out
#Put original background on screen
#Take chunks of blurred background as backdrops for icons
#Allow user to select app with LIRC.

#Start lirc listener
lirc_sock = lirc.init("lirclauncher", "./lircrc", blocking=False)

def pilToPygame(img):
    mode = img.mode
    size = img.size
    data = img.tobytes()
    return pygame.image.fromstring(data, size, mode)

#this is used to get icons.
icon_theme = Gtk.IconTheme.get_default()

#Import our list of apps.
#Format of settings.config:
#Custom:NameOfApplication:ApplicationCommandLine:IconPath
#eg:
#Custom:Exit:pkill -1 -f run.py:./exit.png
apps_complete = []
apps = []
settingsFile = open("settings.config")
settingsLines = settingsFile.readlines()
for line in settingsLines:
    line = line.rstrip()
    if line.find("Custom") == -1:
        apps.append(line)
    else:
        customStuff = line.split(":")
        apps_complete.append({"icon": customStuff[3],
                              "exec": customStuff[2].split(" "),
                              "name": customStuff[1]})

pygame.init()


screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
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
#We currently have processed custom apps and unprocessed .desktop names in two different arrays
# which are about to be combined.
intvl = int(math.floor(infoObject.current_w /
            ((len(apps) + len(apps_complete)) * 2 + 1)))


#middle of the screen
middleT = int(math.floor(infoObject.current_h / 2)) - int(float(intvl) / float(2))


#We're parsing .desktop files to get icon, name (currently unused), and executable path.
for app in apps:
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
        if x.find("Icon") != -1 and iconPath == None:
            iconPath = x.split("=")[1]
            iconPath = iconPath.replace(" ", "")
            if iconPath.find("/") == -1:
                iconPath = icon_theme.lookup_icon(iconPath, 1024, 0).get_filename()
    apps_complete.append({"icon": iconPath, "name": name, "exec": exePath})

#Process & scale icons once.
for app in apps_complete:
    icon = Image.open(app["icon"])
    width,height = icon.size
    ratio = min(float(intvl - 50) / float(width), float((intvl - 50)) / float(height))

    icon = icon.resize((int(width * ratio), int(height * ratio)), Image.ANTIALIAS)
    app["icon"] = pilToPygame(icon)


#These are the list of icon backdrops, cropped properly.
imgs=[]
for i in range(len(apps_complete)):
    imgs.append(pilToPygame(z.crop((intvl * ((2 * i) + 1), middleT,
                                    intvl * ((2 * i) + 1) + intvl,
                                    middleT + intvl))))

#Draw everything!
def draw(highlight):
    global apps_complete, intvl, middleT, backdrop, apps
    
    screen.blit(backdrop, (0,0))

    for i in range(len(apps_complete)):
        screen.blit(imgs[i], (intvl * ((2 * i) + 1), middleT))
    #Scale and draw app icons
    for i, app in enumerate(apps_complete):
        screen.blit(app["icon"], (intvl * ((2 * i) + 1) + 25, middleT + 25))

    pygame.draw.rect(screen, (0, 0, 128), (intvl * ((2 * highlight) + 1),
                     middleT, intvl, intvl), 10)
    pygame.display.flip()


current = 0
draw(current)
proc=subprocess.Popen(["sleep", "0"])
cfull = True
ticker = 0

while True:
    def get_index(name):
        global current

        for index, app in enumerate(apps_complete):
            if app["name"] == name:
                current = index
                return index

    def call_by_index(index):
        global proc, cfull

        cfull = False
        draw(current)
        
        import os
        exec_name = apps_complete[index]["exec"]
        print('Opening %s' % exec_name)
        proc = subprocess.Popen(exec_name)

        # if external program is called, LircLauncher will be windowed (not fullscreen)
        if not pygame.mouse.get_focused():
            screen = pygame.display.set_mode(
                    (infoObject.current_w, infoObject.current_h),
                    pygame.FULLSCREEN)

    def move_current(dir):
        global current, ticker

        if dir == 'left':
            current = max(0, current - 1)
        elif dir == 'right':
            current = min(len(apps_complete) - 1, current + 1)

        ticker = WAIT_TICKS
        draw(current)
        os.system('DISPLAY=:0 /usr/bin/xscreensaver-command -deactivate')

    pygame.event.pump()

    if ticker > 0:
        ticker -= 1
    
    keyDown = pygame.key.get_pressed()
    if ticker == 0:
        if keyDown[pygame.K_LEFT]:
            move_current('left')
        if keyDown[pygame.K_RIGHT]:
            move_current('right')
        if keyDown[pygame.K_RETURN]:
            # App has been selected by arrows and Return keys
            ticker = WAIT_TICKS
            call_by_index(current)

    x = lirc.nextcode()

    lirc_config_programs = {
            "pmp": "Plex Media Player",
            "kodi": "Kodi",
            "torrent": "Torrent Status"
            }

    if x != [] and proc.poll() != None:
                
        if x[0] == "Left":
            move_current('left')
        if x[0] == "Right":
            move_current('right')
        if x[0] == "Return":
            # App has been selected with arrow and OK buttons
            call_by_index(current)

        # Specific calls via Harmony Remote (mceusb) and lirc
        # current will not point to the right program
        # See lircrc file
        if x[0] in lirc_config_programs.keys():
            call_by_index(get_index(lirc_config_programs[x[0]]))

        # if x[0] == "die":
        #    break

        x[0] = ""

    if proc.poll() != None and cfull == False:
        pygame.display.flip()
        cfull = True

lirc.deinit()
sys.exit()
