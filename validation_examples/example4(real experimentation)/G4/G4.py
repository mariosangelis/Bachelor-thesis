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
		
		init_system_settings(int(sys.argv[1]),"G4")
		
		#3->1->3->1
		print("init_system_settings returned, I am a singular component")
		dst_components=get_dst_components()
		print("I can send to components",dst_components)
		dst_flows=get_dst_flows()
		print("I can send to flows",dst_flows)
		src_components=get_src_components()
		print("I can receive from components",src_components)
		src_flows=get_src_flows()
		print("I can receive from flows",src_flows)
		
		while(1):
			dst_components=get_dst_components()
			dst_flows=get_dst_flows()
			src_components=get_src_components()
			src_flows=get_src_flows()
			
			for i in range(0,len(src_flows)):
				data_list=receive(src_components[0],src_flows[i],1,1)
				
				rcvmsg=data_list[0]
				data=rcvmsg.get_data()
				print("G4 got data from G3, from flow_id=",rcvmsg.get_src_flow(),", data=",data)
				seq=int(data)
				
				#1 to 1 scenario
				#send(seq,dst_components,[src_flows[i]])
				
			#aggregation scenario
			send(seq,dst_components,dst_flows)
			
			
				

			
