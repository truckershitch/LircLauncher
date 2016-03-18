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

lirc.init("lirclauncher","/home/alex/.config/lircrc")
#import applications & get icons & exe paths:
def pilToPygame(img):
	mode = img.mode
	size = img.size
	data = img.tobytes()
	return pygame.image.fromstring(data, size, mode)


icon_theme = gtk.icon_theme_get_default()



pygame.init()


screen = pygame.display.set_mode((0,0),pygame.HWSURFACE|pygame.FULLSCREEN)

pygame.mouse.set_visible(False)

image = Image.open("background.jpg")

infoObject = pygame.display.Info()
width,height =  image.size


image=image.resize((infoObject.current_w,infoObject.current_h),Image.ANTIALIAS)

imageDraw=image#.filter(ImageFilter.GaussianBlur(radius=2))

#z=image.crop((200,200,200,200))

whiteFull=Image.new("RGB",(infoObject.current_w,infoObject.current_h),"white")

z=image
z=z.filter(ImageFilter.GaussianBlur(radius=5))
z=Image.blend(z,whiteFull,0.2)
apps=["steam","kodi","plexhometheater","google-chrome-unstable"]
intvl = int(math.floor(infoObject.current_w/(len(apps)*2+1)))

middleT = int(math.floor(infoObject.current_h/2))-100


mode = imageDraw.mode
size = imageDraw.size
data = imageDraw.tobytes()

backdrop = pygame.image.fromstring(data, size, mode)




apps_complete=[]
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
			icon = Image.open(iconPath)
			width,height = icon.size
			ratio=min(float(intvl-50)/float(width), float((intvl-50))/float(height))
			print ratio
			icon=icon.resize((int(width*ratio),int(height*ratio)),Image.ANTIALIAS)
			iconPath=pilToPygame(icon)
	apps_complete.append({"icon":iconPath,"name":name,"exec":exePath})

imgs=[]
for i in range(0,len(apps)):
	imgs.append(pilToPygame(z.crop((intvl*((2*i)+1),middleT,intvl*((2*i)+1)+intvl,middleT+intvl))))


def draw(highlight):
	global apps_complete,intvl,middleT,backdrop,apps
	
	screen.blit(backdrop,(0,0))

	for i in range(0,len(apps)):
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
proc=subprocess.Popen(["echo","alive"])
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
			break
		if current < 0:
			current=0
		if current > len(apps_complete)-1:
			current=len(apps_complete)-1
		draw(current)

lirc.deinit()
sys.exit()
