import time
import sys
import random
import socket
from socket import AF_INET, SOCK_DGRAM
import pickle
from system_network_library import *
import cv2
import numpy as np
from PIL import ImageTk, Image
import PIL.Image, PIL.ImageTk

cascPath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascPath)
previous_no_of_faces = 0
face_crop=[]

def detect_faces(frame):
	
	global previous_no_of_faces
	global face_crop
	
	img=frame
	faces = faceCascade.detectMultiScale(frame, 1.3, 5)
	
	face_crop = []
	for f in faces:
		x, y, w, h = [ v for v in f ]
		cv2.rectangle(img, (x,y), (x+w, y+h), (255,0,0), 3)
		# Define the region of interest in the image  
		face_crop.append(img[y:y+h, x:x+w])


def main():
	
	global face_crop
	init_system_settings(int(sys.argv[1]),"F2")
	
	
	#3->1->1
	print("init_system_settings returned, I am a singular component")
	dst_components=get_dst_components()
	print("I can send to components",dst_components)
	dst_flows=get_dst_flows()
	print("I can send to flows",dst_flows)
	src_components=get_src_components()
	print("I can receive from components",src_components)
	src_flows=get_src_flows()
	print("I can receive from flows",src_flows)
	
	
	image_number=0
	while(1):
		dst_components=get_dst_components()
		dst_flows=get_dst_flows()
		src_components=get_src_components()
		src_flows=get_src_flows()
		
		move(1)
		time.sleep(3)
		move(0)
		
		for i in range(0,len(src_flows)):
			data_list=receive(src_components[0],src_flows[i],1,0)
			
			if(len(data_list)>0):
			
				rcvmsg=data_list[0]
				frame=rcvmsg.get_data()
				print("F2 got a frame from F1, from flow_id=",rcvmsg.get_src_flow())
			
				detect_faces(frame)
				
				print("face_crop len is",len(face_crop))
				if(len(face_crop)>0):
					for face in face_crop:
						
						width=300
						height=300
						dim = (width, height)
						
						# resize image
						resized = cv2.resize(face, dim, interpolation = cv2.INTER_AREA)
						send(resized,dst_components,[src_flows[i]])
					
if __name__ == "__main__":
	
	#argv[1] is the port for the socket to bind
	if(len(sys.argv)<2):
		print("Wrong number of arguments")
	else:
		main()
		
