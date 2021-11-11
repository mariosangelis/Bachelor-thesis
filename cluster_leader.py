#Angelis Marios
#Thesis title: Dynamic deployment of modular distributed stream processing applications
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
import select
import struct

cluster_nodes=[]
HEADER_LENGTH=20
CLUSTER_LEADER_PORT=7000
REGISTRATION_TYPE=1000
INFORMATION_TYPE=2000
EXIT_TYPE=3000
EXIT_REPLY_TYPE=20000
CANCEL_EXIT_TYPE=4000
APPROVED_EXIT_TYPE=5000

class cluster_message_class:
	
	def __init__(self,msg_type="",device_ip=""):
		self.device_ip=device_ip
		self.msg_type=msg_type
		
	def get_msg_type(self):
		return self.msg_type
		
	def get_device_ip(self):
		return self.device_ip
	
	
class agent_message_class:
	def __init__(self,msg_type=0,command=0):
		self.msg_type=msg_type
		self.command=command
	
	def get_msg_type(self):
		return self.msg_type
		
	def get_command(self):
		return self.command
	
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
	
	#Create a tcp socket. This socket will accept new connections.
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind(address)
	sock.listen(1024)
	
	inputs = [sock]
	outputs = []
	
	
	#Use select function to get data from multiple sockets simultaneously.
	while inputs:
		readable, writable, exceptional = select.select(inputs, outputs, inputs)
		for s in readable:
			if s is sock:
				#Accept a connection. Append the file descriptor to the inputs list.
				receive_connection, client_address = s.accept()
				#print("Accepted a connection")
				receive_connection.setblocking(1)
				inputs.append(receive_connection)
			else:
				
				rcvmsg=cluster_message_class()
				closed_connection=0
				received_bytes=HEADER_LENGTH
				
				data=bytes()
				while(1):
					data+= s.recv(received_bytes)
					
					if(len(data)==0):
						closed_connection=1
						#print("connection has closed")
						#Remove the file descriptor from the inputs list.
						inputs.remove(s)
						break
					
					
					if(len(data)==HEADER_LENGTH):
						break
					received_bytes=HEADER_LENGTH-len(data)
					
				if(closed_connection==1):
					break
				
				msg_len=int(data)
				received_bytes=msg_len
				
				#Receive the message after the header
				data=bytes()
				while(1):
					
					try:
						data+=s.recv(received_bytes)
					except BlockingIOError:
						exit()
				
					if(len(data)==msg_len):
						break
					
					received_bytes=msg_len-len(data)
					
				rcvmsg=pickle.loads(data)
				

				print("Got a message from leader,type=",rcvmsg.get_msg_type())
				found_same_name=0
				
				#An agent sent a REGISTRATION_TYPE message 
				if(rcvmsg.get_msg_type()==REGISTRATION_TYPE):
					
					for i in range(0,len(cluster_nodes)):
						if(cluster_nodes[i][1]==rcvmsg.get_device_ip()):
							found_same_name=1
							break
					
					if(found_same_name==0):
						#Give a random name to the device
						cluster_nodes.append([chr(ord('a') +device_names).upper(),rcvmsg.get_device_ip(),1])
						device_names+=1
						
					sndmsg_initial=pickle.dumps("ack")
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
				
					print("cluster nodes=",cluster_nodes)
					
				elif(rcvmsg.get_msg_type()==EXIT_TYPE):
					
					for i in range(0,len(cluster_nodes)):
						if(cluster_nodes[i][1]==rcvmsg.get_device_ip()):
							
							cluster_nodes[i][2]=0
							break
					print(cluster_nodes)
					
					sndmsg_initial=pickle.dumps("ack")
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
					
					
				elif(rcvmsg.get_msg_type()==CANCEL_EXIT_TYPE):
					
					print("CANCEL EXIT on device ",rcvmsg.get_device_ip())
					
					for i in range(0,len(cluster_nodes)):
						if(cluster_nodes[i][0]==rcvmsg.get_device_ip()):
							cluster_nodes[i][2]=1
							break
					
					
					#delete_message=pickle.dumps(agent_message_class(LEADER_DELETE_CONTAINER_TYPE,components,sent_seq))
				
					print(cluster_nodes)
					sndmsg_initial=pickle.dumps("ack")
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
					
				elif(rcvmsg.get_msg_type()==APPROVED_EXIT_TYPE):
					
					print("APPROVED EXIT on device ",rcvmsg.get_device_ip())
					
					for i in range(0,len(cluster_nodes)):
						if(cluster_nodes[i][0]==rcvmsg.get_device_ip()):
							cluster_nodes.remove(cluster_nodes[i])
							break
							
					sndmsg_initial=pickle.dumps("ack")
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
					
			
			
				elif(rcvmsg.get_msg_type()==INFORMATION_TYPE):
					
					#available_cluster_nodes=[]
					
					#for i in range(0,len(cluster_nodes)):
				#		if(cluster_nodes[i][2]==1):
				#			available_cluster_nodes.append(cluster_nodes[i])
					
				#	print(available_cluster_nodes)
							
					sndmsg_initial=pickle.dumps(cluster_nodes)
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
					
	

if __name__=="__main__":
	main()
	
	
