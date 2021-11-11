#Angelis Marios
#Thesis title: Dynamic deployment of stream processing applications
#This file contains the implementation of the cluster leader 

import threading
import time
import socket
import sys
import pickle
import subprocess
from threading import *
import os
import netifaces
from service import *
import fcntl
import struct

cluster_nodes=[]
CLUSTER_LEADER_PORT=7000
REGISTRATION_TYPE=1000
INFORMATION_TYPE=2000


class cluster_message_class:
	
	def __init__(self,msg_type="",device_ip=""):
		self.device_ip=device_ip
		self.msg_type=msg_type
		
	def get_msg_type(self):
		return self.msg_type
		
	def get_device_ip(self):
		return self.device_ip
	
def main():
	
	global cluster_nodes
	
	def getAllInterfaces():
		return os.listdir('/sys/class/net/')
	
	def get_ip_address(ifname):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		return socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s',  bytes(ifname[:15], 'utf-8')))[20:24])
	
	def is_interface_up(interface):
		addr = netifaces.ifaddresses(interface)
		return netifaces.AF_INET in addr

	interfaces=getAllInterfaces()
	final_interface=""
	device_names=0
	
	for i in range(0,len(interfaces)):
		
		if(is_interface_up(interfaces[i])==True):
			if(interfaces[i][0]=='e'):
				final_interface=interfaces[i]
				break
			elif(interfaces[i][0]=='w'):
				final_interface=interfaces[i]
		
		
	my_ip=get_ip_address(final_interface)
	address=(my_ip,CLUSTER_LEADER_PORT)
	print(address)
	
	sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind(address)
	
	
	#TEMPORARY
	for i in range(0,4):
		cluster_nodes.append([chr(ord('a') +device_names).upper(),"192.168.1.101"])
		device_names+=1
	print("cluster nodes=",cluster_nodes)
	
	while(1):
		print("Waiting for new nodes to join the cluster")
		
		#receive a poll message from an istance
		rcvmsg=cluster_message_class()
		rcvmsg, addr = sock.recvfrom(1024)
		rcvmsg=pickle.loads(rcvmsg)
		found_same_name=0
		
		#An agent sent a REGISTRATION_TYPE message 
		if(rcvmsg.get_msg_type()==REGISTRATION_TYPE):
			
			for i in range(0,len(cluster_nodes)):
				if(cluster_nodes[i][1]==rcvmsg.get_device_ip()):
					found_same_name=1
					break
			
			if(found_same_name==0):
				#Give a random name to the device
				cluster_nodes.append([chr(ord('a') +device_names).upper(),rcvmsg.get_device_ip()])
				device_names+=1
				
			reply_msg=pickle.dumps("ack")
			sock.sendto(reply_msg,addr)
		
			print("cluster nodes=",cluster_nodes)
			
		elif(rcvmsg.get_msg_type()==INFORMATION_TYPE):
			#Config parse sent an INFORMATION_TYPE message 
			reply_msg=pickle.dumps(cluster_nodes)
			sock.sendto(reply_msg,addr)
	

if __name__=="__main__":
	main()
	
	
