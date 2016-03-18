import pygame
import pygame.gfxdraw
import time
import subprocess
import sys
from PIL import Image,ImageFilter,ImageChops
import math
import gtk
import re
import lirc


#Rough theory of operation:
#Process apps, get icons
#Take background, Gauss. Blur it, add some white to make it stand out
#Put original background on screen
#Take chunks of blurred background as backdrops for icons
#Allow user to select app with LIRC.


#Start lirc listener
lirc.init("lirclauncher","/home/alex/.config/lircrc")


def pilToPygame(img):
	mode = img.mode
	size = img.size
	data = img.tobytes()
	return pygame.image.fromstring(data, size, mode)

#this is used to get icons.
icon_theme = gtk.icon_theme_get_default()

#Import our list of apps.
apps_complete=[]
apps=[]
settingsFile=open("settings.config")
settingsLines=settingsFile.readlines()
for line in settingsLines:
	if line.find("Custom") == -1:
		apps.append(line.replace("\n",""))
	else:
		customStuff=line.split(":")
		apps_complete.append({"icon":customStuff[3].replace("\n",""),"exec":customStuff[2],"name":customStuff[1]})


pygame.init()


screen = pygame.display.set_mode((0,0),pygame.HWSURFACE|pygame.FULLSCREEN)
infoObject = pygame.display.Info()

pygame.mouse.set_visible(False)


image = Image.open("background.jpg")
width,height =  image.size
#Scale our image to fit the screen
#Yes, this loses aspect ratio, but it's better than black bars,
# and 1080p/1440p/720p wallpapers are easy to find.
image=image.resize((infoObject.current_w,infoObject.current_h),Image.ANTIALIAS)

imageDraw=image #This is what we're actually going to draw.
mode = imageDraw.mode
size = imageDraw.size
data = imageDraw.tobytes()

backdrop = pygame.image.fromstring(data, size, mode)


#need this to highlight behind icons.
whiteFull=Image.new("RGB",(infoObject.current_w,infoObject.current_h),"white")

z=image
z=Image.blend(z,whiteFull,0.2)
z=z.filter(ImageFilter.GaussianBlur(radius=10))


#This length is a little weird.
#We currently have processed custom apps and unprocessed .desktop names in two different arrays
# which are about to be combined.
intvl = int(math.floor(infoObject.current_w/((len(apps)+len(apps_complete))*2+1)))


#middle of the screen
middleT = int(math.floor(infoObject.current_h/2))-int(float(intvl)/float(2))


#We're parsing .desktop files to get icon, name (currently unused), and executable path.
for app in apps:
	f=open("/usr/share/applications/"+app+".desktop")
	lns=f.readlines()
	name=""
	exePath=""
	iconPath=None
	for x in lns:
		if x.find("Name") != -1 and name =="":
			name=x.split("=")[1]
		if x.find("Exec") != -1 and exePath=="":
			exePath=re.sub(r'%.','',x.split("=")[1]).replace("\n","").split(" ")
		if x.find("Icon") != -1 and iconPath==None:
			iconPath=x.split("=")[1]
			iconPath=iconPath.replace(" ","").replace("\n","")
			if iconPath.find("/") == -1:
				iconPath=icon_theme.lookup_icon(iconPath, 1024, 0).get_filename()
	apps_complete.append({"icon":iconPath,"name":name,"exec":exePath})

#Process & scale icons once.
for app in apps_complete:
	icon = Image.open(app["icon"])
	width,height = icon.size
	ratio=min(float(intvl-50)/float(width), float((intvl-50))/float(height))

	icon=icon.resize((int(width*ratio),int(height*ratio)),Image.ANTIALIAS)
	app["icon"]=pilToPygame(icon)


#These are the list of icon backdrops, cropped properly.
imgs=[]
for i in range(0,len(apps_complete)):
	imgs.append(pilToPygame(z.crop((intvl*((2*i)+1),middleT,intvl*((2*i)+1)+intvl,middleT+intvl))))

#Draw everything!
def draw(highlight):
	global apps_complete,intvl,middleT,backdrop,apps
	
	screen.blit(backdrop,(0,0))

	for i in range(0,len(apps_complete)):
		screen.blit(imgs[i],(intvl*((2*i)+1),middleT))
	#Scale and draw first app icon
	i=0
	for app in apps_complete:
		screen.blit(app["icon"],(intvl*((2*i)+1)+25,middleT+25))
		i=i+1

	pygame.draw.rect(screen, (0,0,128), (intvl*((2*highlight)+1),middleT,intvl,intvl), 10)
	pygame.display.flip()


current=1
draw(current)
proc=subprocess.Popen(["sleep","0"])
while True:
	pygame.event.pump()
	x=lirc.nextcode()
	if x != [] and proc.poll() != None:
		if x[0]=="left":
			current=current-1
		if x[0]=="right":
			current=current+1
		if x[0]=="go":
			proc=subprocess.Popen(apps_complete[current]["exec"])
			#break
		if x[0]=="die":
			break
		if current < 0:
			current=0
		if current > len(apps_complete)-1:
			current=len(apps_complete)-1
		draw(current)

lirc.deinit()
sys.exit()
