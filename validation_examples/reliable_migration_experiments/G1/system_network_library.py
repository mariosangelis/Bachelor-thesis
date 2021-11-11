#Angelis Marios
#Thesis title: Dynamic deployment of stream processing applications
#This file contains the implementation of the system network library. This library should be imported at each component's source code.

from threading import *
import time
import sys
import random
import socket
from socket import AF_INET, SOCK_DGRAM
import pickle
import fcntl
import struct
import select
import platform
import netifaces
import array
import os
import subprocess
F_Red = "\x1b[31m"
Reset = "\x1b[0m"

LEADER_MESSAGE_TYPE=12000
CLOSE_DESTINATION_CONNECTIONS_TYPE=14000
DATA_MESSAGE_TYPE=13000
MOVE_STATUS_CHECK=15000
START_TCP_RELIABILITY_CHECK_TYPE=16000
TCP_RELIABILITY_CHECK_TYPE=17000
START_MOVE_BUFFER_TYPE=18000
MOVE_BUFFER_TYPE=19000
LEADER_MESSAGE_TYPE_MOVE_INITALIZATION=20000

HEADER_LENGTH=20
POLL_PORT=8000
destination_address=[]
my_address=0
data_buffer=[]
data_mtx=Semaphore(1)
init_mtx=Semaphore(0)
leader_message_mtx=Semaphore(1)
component_name=0
leader_message=0
singular=0
move_status=0
close_connections_mtx=Semaphore(1)
move_status_mtx=Semaphore(1)
leader_address=("192.168.1.103",POLL_PORT)

#When an instance starts, it sends a poll message to the parser. A poll message is an object created from the following class.
class poll_message:
	
	def __init__(self,instance_name=""):
		self.instance_name=instance_name
		
	def get_instance_name(self):
		return self.instance_name

#This is the core messaging class. All messages exchanged between instances are objects created from the following class.
class message_class:
	def __init__(self,msg_type=0,data=0,dst_ip=None,dst_port=None,dst_components=None,dst_flows=None,singular=-1,src_components=None,src_flows=None,reliable=0):
		self.msg_type=msg_type
		self.data=data
		self.singular=singular
		self.src_components=src_components
		self.src_flows=src_flows
		self.dst_components=dst_components
		self.dst_flows=dst_flows
		self.dst_ip=dst_ip
		self.dst_port=dst_port
		self.reliable=reliable
	
	def is_reliable(self):
		return self.reliable
	
	def set_reliability(self,reliability):
		self.reliable=reliability
	
	def get_dst_components(self):
		return self.dst_components
	
	def get_dst_flow(self):
		return self.dst_flows
	
	def get_src_components(self):
		return self.src_components
	
	def get_src_flow(self):
		return self.src_flows
	
	def is_singular(self):
		return self.singular
	
	def get_data(self):
		return(self.data)
	
	def get_type(self):
		return(self.msg_type)
	
	def get_ip(self):
		return(self.dst_ip)
	
	def get_port(self):
		return(self.dst_port)
	
	def set_type(self,new_type):
		self.msg_type=new_type
	
#This thread receives messages from other components
def waiting_connections():
	
	global data_buffer
	global my_address
	global singular
	global destination_address
	global leader_message
	global move_status
	global move_status_mtx
	
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
	
	#Give a priority to ethernet interfaces.
	for i in range(0,len(interfaces)):
		
		if(is_interface_up(interfaces[i])==True):
			if(interfaces[i][0]=='e'):
				final_interface=interfaces[i]
				break
			elif(interfaces[i][0]=='w'):
				final_interface=interfaces[i]

	print("final_interface=",final_interface)
	print(get_ip_address(final_interface))
	
	my_ip=get_ip_address(final_interface)
	my_port=int(sys.argv[1])
	my_address=(my_ip,my_port)
	
	#Create a tcp socket. This socket will accept new connections.
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	
	first_leader_message=0
	sock.bind(my_address)
	sock.listen(1024)
	
	inputs = [sock]
	outputs = []
	
	print("Send a poll message")
	
	udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
	udp_sock.settimeout(5.0)
	
	#Send a poll message to the parser.
	ping_message=pickle.dumps(poll_message(component_name))
	
	ack_received=0
	total_bytes_received=0
	#Use at least once semantics
	while(1):
		
		udp_sock.sendto(ping_message,leader_address)
		
		while(1):
			try:
				data, addr = udp_sock.recvfrom(1024)
				ack_received=1
				print("Got a right ack")
				
			except socket.timeout:
				print("Timeout")
				break
			
		if(ack_received==1):
			break
	
	#Use select function to get data from multiple sockets simultaneously.
	while inputs:
		readable, writable, exceptional = select.select(inputs, outputs, inputs)
		for s in readable:
			if s is sock:
				#Accept a connection. Append the file descriptor to the inputs list.
				receive_connection, client_address = s.accept()
				print("Accepted a connection")
				receive_connection.setblocking(1)
				inputs.append(receive_connection)
			else:
				
				rcvmsg=message_class()
				closed_connection=0
				received_bytes=HEADER_LENGTH
				
				data=bytes()
				while(1):
					data+= s.recv(received_bytes)
					
					if(len(data)==0):
						closed_connection=1
						print("connection has closed")
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
				
				#If this is a data message, append it to the data_buffer
				#ATTENTION The data_buffer is data message specific. Instead, the destination_address is leader message specific
				if(rcvmsg.get_type()==DATA_MESSAGE_TYPE):
					
					total_bytes_received+=len(data)
					
					print("RECEIVED ",total_bytes_received,"BYTES OF DATA")
					data_buffer_initialized=0
					
					data_mtx.acquire()
					
					if(singular==0):
						
						#A non-singular component should not care about data flows. Thus, the buffer contains only the src component id at his first position.
						#Example (for component F4) :
						#Component_name    Data_flow    Messages
						#    F2                -          ...
						#    F3                -          ...
						
						#Check if we have already initialized the source component. If no, append a lew entry to the data buffer. If yes, append only the received message.
						for i in range(0,len(data_buffer)):
							if(data_buffer[i][0]==rcvmsg.get_src_components()):
								data_buffer_initialized=1
								break
							
						if(data_buffer_initialized==0):
							data_buffer.append([rcvmsg.get_src_components(),""])
						
						for i in range(0,len(data_buffer)):
							if(data_buffer[i][0]==rcvmsg.get_src_components()):
								data_buffer[i].append(rcvmsg)
								print("Got a message from src component",rcvmsg.get_src_components(),"buffer size=",len(data_buffer[i])*1000,"bytes")
								break
					else:
						
						#A singular component should care about data flows. Thus, the buffer contains a conbination of the src component name and the src data flow.
						#Example (for component F3) :
						#Component_name    Data_flow    Messages
						#    F2                1          ...
						#    F2                2          ...
						#    F2                3          ...
						
						#Check if we have already initialized the combination source component-source flow. If no, append a lew entry to the data buffer. If yes, append only the received message.
						for i in range(0,len(data_buffer)):
							if(data_buffer[i][0]==rcvmsg.get_src_components() and data_buffer[i][1]==rcvmsg.get_src_flow()):
								data_buffer_initialized=1
								break
							
						if(data_buffer_initialized==0):
							data_buffer.append([rcvmsg.get_src_components(),rcvmsg.get_src_flow()])
						
						for i in range(0,len(data_buffer)):
							if(data_buffer[i][0]==rcvmsg.get_src_components() and data_buffer[i][1]==rcvmsg.get_src_flow()):
								data_buffer[i].append(rcvmsg)
								print("Got a message from src component",rcvmsg.get_src_components(),"and src flow",rcvmsg.get_src_flow(),"buffer size=",len(data_buffer[i])*1000,"bytes")
								break
												
					data_mtx.release()
				elif(rcvmsg.get_type()==LEADER_MESSAGE_TYPE):
					
					print("Got a message from leader. Send my data to ip",rcvmsg.get_ip(),"port",rcvmsg.get_port(),"components",rcvmsg.get_dst_components(),"flows=",rcvmsg.get_dst_flow())
					close_connections_mtx.acquire()
					
					#Set destination address.
					for i in range (0,len(rcvmsg.get_ip())):
						found_entry=0
						
						#This thread can receive more than one leader messages because some devices could be inserted to the cluster and the algorithm may update the number of running instances.
						#If a same entry has been inserted in the destination_address, do not add it again.
						for t in range(0,len(destination_address)):
							
							#Update the ip address of an existing destination list's entry. "move" command uses this case
							if((destination_address[t][2]==rcvmsg.get_dst_components()[i]) and (destination_address[t][5]==rcvmsg.get_dst_flow()[i]) and (destination_address[t][0]!=rcvmsg.get_ip()[i])):
								destination_address[t][0]=rcvmsg.get_ip()[i]
								destination_address[t][3]=0
								if(destination_address[t][4]!=None):
									
									#If reliable flag is up, send a TCP control message before closing the connection in order to ensure that all data have reached their destination.
									if(rcvmsg.is_reliable()):
										sndmsg_initial=message_class(TCP_RELIABILITY_CHECK_TYPE)
										sndmsg_initial=pickle.dumps(sndmsg_initial)
										
										#Send a message with the following structure: HEADER(20 Bytes) + pickled object
										sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
										
										destination_address[t][4].sendall(sndmsg)
										destination_address[t][4].recv(1000)
										print("GOT AN ACK from component",destination_address[t][2],"and flow",destination_address[t][5])
									
									#Close the connection. This connection will be reset at the first call of the send function.
									destination_address[t][4].close()
									destination_address[t][4]=None
								found_entry=1
								break
							
							elif((destination_address[t][0]==rcvmsg.get_ip()[i]) and (destination_address[t][2]==rcvmsg.get_dst_components()[i]) and (destination_address[t][5]==rcvmsg.get_dst_flow()[i])):
								found_entry=1
								break
						
						if(found_entry==0):
							#destination_address has the following form:
							# IP  PORT   COMPONENT_NAME  INITIALIZED_FLAG  CONNECTION_DESCRIPTOR   FLOW_ID 
							destination_address.append([rcvmsg.get_ip()[i],rcvmsg.get_port()[i],rcvmsg.get_dst_components()[i],0,None,rcvmsg.get_dst_flow()[i]])
					
					close_connections_mtx.release()
					
					#Store the last leader message
					leader_message_mtx.acquire()
					leader_message=rcvmsg
					leader_message_mtx.release()
					
					if(first_leader_message==0):
						first_leader_message=1
						#singular=rcvmsg.is_singular()
						#Wake up the init_system_settings function
						print("WAKE UP INIT_MTX SEMAPHORE")
						init_mtx.release()
					
					reply_msg=pickle.dumps("ack")
					s.sendall(reply_msg)
					
				elif(rcvmsg.get_type()==LEADER_MESSAGE_TYPE_MOVE_INITALIZATION):
					singular=rcvmsg.is_singular()
					
					print("Got a LEADER_MESSAGE_TYPE_MOVE_INITALIZATION message")
					reply_msg=pickle.dumps("ack")
					s.sendall(reply_msg)
					
				elif(rcvmsg.get_type()==CLOSE_DESTINATION_CONNECTIONS_TYPE):
					close_connections_mtx.acquire()
					
					#Got a CLOSE_DESTINATION_CONNECTIONS_TYPE message. Close all the connections
					for i in range(0,len(destination_address)):
						if(destination_address[i][4]!=None):
							
							#If reliable flag is up, send a TCP control message before closing the connection in order to ensure that all data have reached their destination.
							if(rcvmsg.is_reliable()):
								sndmsg_initial=message_class(TCP_RELIABILITY_CHECK_TYPE)
								sndmsg_initial=pickle.dumps(sndmsg_initial)
								
								#Send a message with the following structure: HEADER(20 Bytes) + pickled object
								sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
								
								destination_address[i][4].sendall(sndmsg)
								destination_address[i][4].recv(1000)
								print("GOT AN ACK from component",destination_address[i][2],"and flow",destination_address[i][5])
							
							#Close the connection.
							destination_address[i][4].close()
							destination_address[i][4]=None
					
					close_connections_mtx.release()
					reply_msg=pickle.dumps("ack")
					s.sendall(reply_msg)
					
				elif(rcvmsg.get_type()==MOVE_STATUS_CHECK):
					
					#Return the move status to the parser. If move status is 1, this component will be moved. Thus, the move_status_mtx will remain locked until the process is complete.
					move_status_mtx.acquire()
					reply_msg_initial=pickle.dumps(move_status)
					reply_msg=bytes(f'{len(reply_msg_initial):<{HEADER_LENGTH}}',"utf-8") + reply_msg_initial

					s.sendall(reply_msg)
					
					print("my move status is",move_status)
					
					if(move_status==0):
						move_status_mtx.release()
				
				elif(rcvmsg.get_type()==TCP_RELIABILITY_CHECK_TYPE):
					
					print("Got a TCP_RELIABILITY_CHECK_TYPE message")
					reply_msg=pickle.dumps("ack")
					s.sendall(reply_msg)
					
				elif(rcvmsg.get_type()==START_MOVE_BUFFER_TYPE):
					data_mtx.acquire()
					
					#Create a tcp socket. This socket connects the old instance and the new instance.
					buffer_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					buffer_socket.connect((rcvmsg.get_ip(),my_port))
					
					total_bytes_moved=0
					
					start=time.time()
					for i in range(0,len(data_buffer)):
						print("position",i,"BUFFER LENGTH is",len(data_buffer[i]))
						for j in range(2,len(data_buffer[i])):
							print("Move message",j)
							
							#Move message j from the old isntance to the new instance.
							sndmsg_initial=data_buffer[i][j]
							#sndmsg_initial.set_type(MOVE_BUFFER_TYPE)
							sndmsg_initial=pickle.dumps(sndmsg_initial)
							
							total_bytes_moved+=len(sndmsg_initial)
							
							#Send a message with the following structure: HEADER(20 Bytes) + pickled object
							sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
							buffer_socket.sendall(sndmsg)
							
					buffer_socket.close()
					data_mtx.release()
					reply_msg=pickle.dumps("ack")
					s.sendall(reply_msg)
					

#This function can be called from the application for the move status to be changed.
def move(status):
	
	global move_status
	global move_status_mtx
	
	move_status_mtx.acquire()
	move_status=status
	print("Move status changed to",move_status)
	move_status_mtx.release()
	
#This function can be called from non-singular and singular components. It returns a list of the source components from which data can be arrived to the current component.
def get_src_components():
	global leader_message
	
	leader_message_mtx.acquire()
	components_list=[]
	
	for i in range(0,len(leader_message.get_src_components())):
		if(leader_message.get_src_components()[i] not in components_list):
			components_list.append(leader_message.get_src_components()[i])
	
	leader_message_mtx.release()
	
	return components_list

#This function can be called only from singular components. It returns a list of the source flows from which data can be arrived to the current component.
def get_src_flows():
	
	global leader_message
	global singular
	
	if(singular==0):
		print("You dont need flows")
		return None
	
	leader_message_mtx.acquire()
	flow_list=[]
	
	for i in range(0,len(leader_message.get_src_flow())):
		if(leader_message.get_src_flow()[i] not in flow_list):
			flow_list.append(leader_message.get_src_flow()[i])
	
	leader_message_mtx.release()
	
	return flow_list

#This function can be called only from singular components. It returns a list which contains combinations of component_names-flow_ids from which data can be arrived to the current component.
def dst_components_and_flows():
	
	global leader_message
	global singular
	
	if(singular==0):
		print(F_Red,"You dont need flows",Reset,sep='')
		return None
	
	leader_message_mtx.acquire()
	components_and_flows=[]
	
	for i in range(0,len(leader_message.get_dst_components())):
		components_and_flows.append([leader_message.get_dst_components()[i],leader_message.get_dst_flow()[i]])
		
	leader_message_mtx.release()
	
	return components_list

#This function can be called from non-singular and singular components. It returns a list of the destination components.
def get_dst_components():
	
	global leader_message
	leader_message_mtx.acquire()
	components_list=[]
	
	for i in range(0,len(leader_message.get_dst_components())):
		if(leader_message.get_dst_components()[i] not in components_list):
			components_list.append(leader_message.get_dst_components()[i])
		
	leader_message_mtx.release()
	
	return components_list

#This function can be called only from singular components. It returns a list of the destination flows.
def get_dst_flows():
	
	global leader_message
	global singular
	
	if(singular==0):
		print(F_Red,"You dont need flows",Reset,sep='')
		return None
	
	leader_message_mtx.acquire()
	flow_list=[]
	
	for i in range(0,len(leader_message.get_dst_flow())):
		if(leader_message.get_dst_flow()[i] not in flow_list):
			flow_list.append(leader_message.get_dst_flow()[i])
	
	leader_message_mtx.release()
	
	return flow_list

#This function is called first.
def init_system_settings(port,who_am_i):
	
	global component_name
	global leader_message
	
	component_name=who_am_i
	
	#This function is called for the first time. Create a thread in order to wait for new connections
	connections_thread = Thread(target=waiting_connections, args=[])
	#Start the thread
	connections_thread.start()

	#acquire init mtx
	init_mtx.acquire()
	#init_mtx released from the "waiting_leader_messages" thread
	
	return leader_message
			
#Send function
def send(data,destination_list,destination_flow_id_list):
	
	global destination_address
	global singular
	global move_status
	global move_status_mtx
	
	move_status_mtx.acquire()
	if(move_status==1):
		move_status_mtx.release()
		print(F_Red,"Move command is disabled, can not call send function",Reset,sep='')
		return None
	move_status_mtx.release()
		
	
	#A non-singular component should specify the destination_list and should not specify the destination_flow_id_list
	#Example: send(data,["F2","F3"],None)
	if((singular==0 and destination_list==None) or (singular==0 and destination_flow_id_list!=None)):
		print(F_Red,"Specify a valid destination components list",Reset,sep='')
		return None
	
	close_connections_mtx.acquire()
	
	if(destination_list!=None and destination_flow_id_list==None):
		for j in range(0,len(destination_list)):
			print("send to component",destination_list[j])
			
			for k in range(0,len(destination_address)):
				if(destination_address[k][2]==destination_list[j]):
					if(destination_address[k][3]==0):
						destination_address[k][3]=1
						print("First time send,create a tcp connection,dst=",destination_address[k])
						#Create a tcp socket
						destination_address[k][4]=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						destination_address[k][4].connect((destination_address[k][0],destination_address[k][1]))
					
					if(destination_address[k][4]==None):
						close_connections_mtx.release()
						return(None)
					
					#Create ab object from the message class
					sndmsg_initial=message_class(DATA_MESSAGE_TYPE,data,0,0,0,0,0,component_name,destination_address[k][5])
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					print("SEND A MESSAGE WITH LENGTH=",len(sndmsg_initial))
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					
					destination_address[k][4].sendall(sndmsg)
					
	elif(destination_list==None and destination_flow_id_list!=None):
		for j in range(0,len(destination_flow_id_list)):
			print("send to flow",destination_flow_id_list[j])
			
			for k in range(0,len(destination_address)):
				if(destination_address[k][5]==destination_flow_id_list[j]):
					if(destination_address[k][3]==0):
						destination_address[k][3]=1
						print("First time send,create a tcp connection,dst=",destination_address[k])
						#Create a tcp socket
						destination_address[k][4]=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						destination_address[k][4].connect((destination_address[k][0],destination_address[k][1]))
						
					if(destination_address[k][4]==None):
						close_connections_mtx.release()
						return(None)
					
					#Create ab object from the message class
					sndmsg_initial=message_class(DATA_MESSAGE_TYPE,data,0,0,0,0,0,component_name,destination_address[k][5])
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					
					destination_address[k][4].sendall(sndmsg)
					
					
	elif(destination_list!=None and destination_flow_id_list!=None):
		if(len(destination_list)>1):
			print(F_Red,"Destination List should be length 1",Reset,sep='')
			close_connections_mtx.release()
			return None
		
		for j in range(0,len(destination_flow_id_list)):
			print("send to flow",destination_flow_id_list[j])
			
			for k in range(0,len(destination_address)):
				if(destination_address[k][5]==destination_flow_id_list[j] and destination_address[k][2]==destination_list[0]):
					if(destination_address[k][3]==0):
						destination_address[k][3]=1
						print("First time send,create a tcp connection,dst=",destination_address[k])
						#Create a tcp socket
						destination_address[k][4]=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						destination_address[k][4].connect((destination_address[k][0],destination_address[k][1]))
						
					if(destination_address[k][4]==None):
						close_connections_mtx.release()
						return(None)
					
					#Create ab object from the message class
					sndmsg_initial=message_class(DATA_MESSAGE_TYPE,data,0,0,0,0,0,component_name,destination_address[k][5])
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					
					
					destination_address[k][4].sendall(sndmsg)
	close_connections_mtx.release()
	
	
#Receive function
def receive(from_component,flow_id,how_much_messages,blocking_mode):
    
	global singular
	global data_buffer
	global move_status
	global move_status_mtx
	
	move_status_mtx.acquire()
	if(move_status==1):
		move_status_mtx.release()
		print(F_Red,"Move command is disabled, can not call receive function",Reset,sep='')
		return None
	move_status_mtx.release()
	
	#A non-singular component should specify the from_component and should not specify the flow_id
	#Example: receive("F2",None,1,1)
	if((singular==0 and from_component==None) or (singular==0 and flow_id!=None)):
		print(F_Red,"Specify a valid source component",Reset,sep='')
		return None
	
	data=None
	if(from_component!=None and flow_id==None):
		data=[]
		if(blocking_mode==1):
			while(1):
				data_mtx.acquire()
				for i in range(0,len(data_buffer)):
					if(data_buffer[i][0]==from_component):
						print("")
						data_mtx.release()
						
						while(1):
							if(len(data)==how_much_messages):
								break
							
							data_mtx.acquire()
							if(len(data_buffer[i])>2):
								data.append(data_buffer[i][2])
								data_buffer[i].pop(2)
								
							data_mtx.release()
				
				if(len(data)==how_much_messages):
					break
				else:
					data_mtx.release()
		else:
			data_mtx.acquire()
			data=[]
			for i in range(0,len(data_buffer)):
				if(data_buffer[i][0]==from_component):
					
					if(len(data_buffer[i])>2):
					
						for j in range(0,how_much_messages):
							data.append(data_buffer[i][2])
							data_buffer[i].pop(2)
							
							if(len(data_buffer[i])==2):
								break
				
					break
			data_mtx.release()

	elif(from_component==None and flow_id!=None):
		data=[]
		if(blocking_mode==1):
			while(1):
				data_mtx.acquire()
				for i in range(0,len(data_buffer)):
					if(data_buffer[i][1]==flow_id):
						
						data_mtx.release()
						while(1):
							if(len(data)==how_much_messages):
								break
							
							data_mtx.acquire()
							if(len(data_buffer[i])>2):
								data.append(data_buffer[i][2])
								data_buffer[i].pop(2)
								
							data_mtx.release()
				
				if(len(data)==how_much_messages):
					break
				else:
					data_mtx.release()
		else:
			data_mtx.acquire()
			data=[]
			for i in range(0,len(data_buffer)):
				if(data_buffer[i][1]==flow_id):
					
					if(len(data_buffer[i])>2):
					
						for j in range(0,how_much_messages):
							data.append(data_buffer[i][2])
							data_buffer[i].pop(2)
							
							if(len(data_buffer[i])==2):
								break
				
					break
			data_mtx.release()
			
	elif(from_component!=None and flow_id!=None):
		data=[]
		if(blocking_mode==1):
			while(1):
				data_mtx.acquire()
				for i in range(0,len(data_buffer)):
					if(data_buffer[i][0]==from_component  and data_buffer[i][1]==flow_id):
						
						data_mtx.release()
						
						while(1):
							if(len(data)==how_much_messages):
								break
							
							data_mtx.acquire()
							if(len(data_buffer[i])>2):
								data.append(data_buffer[i][2])
								data_buffer[i].pop(2)
								
							data_mtx.release()
				
				if(len(data)==how_much_messages):
					break
				else:
					data_mtx.release()
			
		else:
			data_mtx.acquire()
			data=[]
			for i in range(0,len(data_buffer)):
				if(data_buffer[i][1]==flow_id and data_buffer[i][0]==from_component):
					
					if(len(data_buffer[i])>2):
						for j in range(0,how_much_messages):
							data.append(data_buffer[i][2])
							data_buffer[i].pop(2)
							
							if(len(data_buffer[i])==2):
								break
				
					break
			data_mtx.release()
	
	return data
	

