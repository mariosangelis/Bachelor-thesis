import time
import sys
import random
import socket
from socket import AF_INET, SOCK_DGRAM
import pickle
from system_network_library import *


if __name__ == "__main__":

	#argv[1] is the service id and argv[2] is client's socket reply port
	if(len(sys.argv)<2):
		print("Wrong number of arguments")
	else:
		
		init_system_settings(int(sys.argv[1]),"G1")
			
			
		#3->1->3->1
		print("init_system_settings returned, I am not a singular component")
		
		dst_components=get_dst_components()
		print("I can send to components",dst_components)
		src_components=get_src_components()
		print("I can receive from components",src_components)
		
		seq=0
		
		while(1):
			
			#time.sleep(5)
			seq+=1
			
			move(1)
			time.sleep(3)
			move(0)
			
			
			#start = time.time()
			send(seq,dst_components,None)
			
			#data_list=receive(src_components[0],None,1,1)
			#end = time.time()
			
				
			#rcvmsg=data_list[0]
			#data=rcvmsg.get_data()
			#print("G1 got loopback data from G4, data=",data,"RTT=",end-start)
			#print(end-start)
			
			
			
			
			
			
			
			
			
			
			
			
			
			
