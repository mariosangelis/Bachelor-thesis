import time
import sys
import random
import socket
from socket import AF_INET, SOCK_DGRAM
import pickle
from system_network_library import *
import cv2
import numpy as np
import os

def main():
	
	init_system_settings(int(sys.argv[1]),"F1")
	
	#3->1->1
	print("init_system_settings returned, I am not a singular component")
	
	dst_components=get_dst_components()
	print("I can send to components",dst_components)
	src_components=get_src_components()
	print("I can receive from components",src_components)
	
	
	cap = cv2.VideoCapture(0)

	# Check if camera opened successfully
	if (cap.isOpened() == False): 
		print("Unable to read camera feed")
		exit()
		
	frame_width = int(cap.get(3))
	frame_height = int(cap.get(4))
	
	while(1):
		
		move(1)
		time.sleep(2)
		move(0)
		
		ret, frame = cap.read()
		
		if ret == True:
			frame=cv2.resize(frame, (900, 500))
			send(frame,dst_components,None)
			 
		else:
			print("Error during reading from camera feed")
		
	
if __name__ == "__main__":
	

	#argv[1] is the service id and argv[2] is client's socket reply port
	if(len(sys.argv)<2):
		print("Wrong number of arguments")
	else:
		
		main()
		
