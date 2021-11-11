import time
import sys
import random
import socket
from socket import AF_INET, SOCK_DGRAM
import pickle
from system_network_library import *

if __name__ == "__main__":
	
	#argv[1] is the port for the socket to bind
	if(len(sys.argv)<2):
		print("Wrong number of arguments")
	else:
		
		init_system_settings(int(sys.argv[1]),"G3")
		
		#3->1->3->1
		print("init_system_settings returned, I am not a singular component")
		dst_components=get_dst_components()
		print("I can send to components",dst_components)
		src_components=get_src_components()
		print("I can receive from components",src_components)
		
		while(1):
			
			dst_components=get_dst_components()
			src_components=get_src_components()
			
			move(1)
			time.sleep(3)
			move(0)
			
			
			data_list=receive(src_components[0],None,1,0)
			
			if(len(data_list)>0):
			
				rcvmsg=data_list[0]
				data=rcvmsg.get_data()
				print("G3 got data from G2, data=",data)
				
				send(data,dst_components,None)
	
	
	
	
	
	
	
	
	
	
	
	
