#!/usr/bin/env python3
import numpy as np
from pathlib import Path
import time
import os
import cv2
import skimage.measure
from skimage import measure
from system_network_library import *
import time
import sys
import random
import socket
from socket import AF_INET, SOCK_DGRAM
import pickle

def compare_images(path1,path2):
	
	# load the two input images
	imageA = cv2.imread(path1)
	imageB = cv2.imread(path2)
	
	try:
	
		# convert the images to grayscale
		grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
		grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
		
		# compute the Structural Similarity Index (SSIM) between the two
		# images, ensuring that the difference image is returned
		(score, diff) = skimage.metrics.structural_similarity(grayA, grayB, full=True)
		diff = (diff * 255).astype("uint8")
	
	except (ValueError,IndexError):
		return 0
	
	return(score)


def main():
	
	#3->1->1
	init_system_settings(int(sys.argv[1]),"F3")
	print("init_system_settings returned, I am a singular component")
	dst_components=get_dst_components()
	print("I can send to components",dst_components)
	dst_flows=get_dst_flows()
	print("I can send to flows",dst_flows)
	src_components=get_src_components()
	print("I can receive from components",src_components)
	src_flows=get_src_flows()
	print("I can receive from flows",src_flows)
	
	images_inside_database=0
	image_name="current_image.jpeg"
	
	while(1):
		dst_components=get_dst_components()
		dst_flows=get_dst_flows()
		src_components=get_src_components()
		src_flows=get_src_flows()
		
		move(1)
		time.sleep(2)
		move(0)
		
		
		for i in range(0,len(src_flows)):
			data_list=receive(src_components[0],src_flows[i],1,0)
			
			if(data_list!=None and len(data_list)==1):
			
				rcvmsg=data_list[0]
				face=rcvmsg.get_data()
				print("F3 got a cropped face from F2, from flow_id=",rcvmsg.get_src_flow())
				
				fd = os.open(image_name, os.O_RDWR|os.O_CREAT|os.O_TRUNC)
				os.close(fd)
				
				cv2.imwrite(image_name,face)
				for j in range(0,images_inside_database):
					
					image="images/"+str(j)+".jpeg"
					print("Compare received image with image",image)
					ret=compare_images(image_name,"images/"+str(j)+".jpeg")
					
					if(ret>0.5):
						print("These images are of the same person!")
						break
					
				cv2.imwrite("images/"+str(images_inside_database)+".jpeg", face)
				images_inside_database+=1
					
				
if __name__ == '__main__':
    #argv[1] is the port for the socket to bind
	if(len(sys.argv)<2):
		print("Wrong number of arguments")
	else:
		main()
