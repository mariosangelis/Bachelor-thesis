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

		
		init_system_settings(int(sys.argv[1]),"G2")

		
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
			
			move(1)
			time.sleep(3)
			move(0)
			
			for i in range(0,len(src_flows)):
				data_list=receive(src_components[0],src_flows[i],1,0)
				
				if(len(data_list)>0):
				
					rcvmsg=data_list[0]
					data=rcvmsg.get_data()
					print("G2 got data from F1, from flow_id=",rcvmsg.get_src_flow(),", data=",data)
					seq=int(data)
					
					#1 to 1 scenario
					send(seq,dst_components,[src_flows[i]])
		
			#aggregation scenario
			#send(seq,dst_components,dst_flows)
		
		'''
		print("init_system_settings returned, I am not a singular component")
		
		dst_components=get_dst_components()
		print("I can send to components",dst_components)
		src_components=get_src_components()
		print("I can receive from components",src_components)
		
		
		while(1):
			dst_components=get_dst_components()
			src_components=get_src_components()
		
			data_list=receive(src_components[0],None,1,1)
				
			rcvmsg=data_list[0]
			data=rcvmsg.get_data()
			print("G2 got data from F1, data=",data)
			seq=int(data)
			
			#1 to 1 scenario
			send(seq,dst_components,None)
			
			'''
			
