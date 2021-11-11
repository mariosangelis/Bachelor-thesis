import time
import sys
import random
import socket
from socket import AF_INET, SOCK_DGRAM
import pickle
import fcntl
import struct
import psutil
import platform
import netifaces
import array
import os
import threading
import select
from threading import *
import subprocess

LEADER_PING_TYPE=14000
LEADER_CREATE_SERVICE_TYPE=15000
LEADER_DELETE_CONTAINER_TYPE=16000
EXIT_REPLY_ACK_TYPE=20000
EXIT_REPLY_NACK_TYPE=21000
REGISTRATION_TYPE=1000
EXIT_TYPE=3000
AGENT_PORT=9000
CLUSTER_LEADER_PORT=7000
HEADER_LENGTH=20
cluster_leader_address=("192.168.1.103",CLUSTER_LEADER_PORT)
exit_mtx=Semaphore(1)
exit_flag=-1

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

def command_thread(my_ip):
	
	global cluster_leader_address
	global exit_flag
	global exit_mtx
	
	while(1):
		command=input()
		command=command.split(" ")
		
		if(command[0]=="exit"):
			sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect(cluster_leader_address)
			
			sndmsg_initial=cluster_message_class(EXIT_TYPE,my_ip)
			sndmsg_initial=pickle.dumps(sndmsg_initial)
			
			#Send a message with the following structure: HEADER(20 Bytes) + pickled object
			cluster_message=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
			sock.sendall(cluster_message)
			
			received_bytes=HEADER_LENGTH
			
			data=bytes()
			while(1):
				data+= sock.recv(received_bytes)
				
				
				if(len(data)==HEADER_LENGTH):
					break
				received_bytes=HEADER_LENGTH-len(data)
				
			
			msg_len=int(data)
			received_bytes=msg_len
			
			#Receive the message after the header
			data=bytes()
			while(1):
				
				try:
					data+=sock.recv(received_bytes)
				except BlockingIOError:
					exit()
			
				if(len(data)==msg_len):
					break
				
				received_bytes=msg_len-len(data)
				
			rcvmsg=pickle.loads(data)
			sock.close()
			
			exit_mtx.acquire()
			exit_flag=-1
			exit_mtx.release()
			
			
			while(1):
				exit_mtx.acquire()
				if(exit_flag==1):
					exit_mtx.release()
					return
				elif(exit_flag==0):
					exit_mtx.release()
					break
				
				exit_mtx.release()
		else:
			print("Invalid Command")
			
class device_HW_characteristics:
	def __init__(self,processor=0,cores=0,frequency=0,available_ram=0,total_ram=0,sensors=0,position=0):
		self.available_ram=available_ram
		self.cores=cores
		self.current_frequency=frequency
		self.processor=processor
		self.sensors=sensors
		self.seq=-1
		self.position=position
			
	def get_processor(self):
		return self.processor
	
	def get_position(self):
		return self.position
	
	def get_cores(self):
		return self.cores
		
	def get_available_ram(self):
		return self.available_ram
		
	def get_current_frequency(self):
		return self.current_frequency
	
	def get_sensors(self):
		return self.sensors
	
	def set_seq(self,seq):
		self.seq=seq
	
	def get_seq(self):
		return(self.seq)
	
	def get_position(self):
		return self.position
		
		
def main():
	
	global exit_flag
	global exit_mtx
	
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
	
	for i in range(0,len(interfaces)):
		
		if(is_interface_up(interfaces[i])==True):
			if(interfaces[i][0]=='e'):
				final_interface=interfaces[i]
				break
			elif(interfaces[i][0]=='w'):
				final_interface=interfaces[i]
    
	print("final_interface=",final_interface)
	print(get_ip_address(final_interface))  # '192.168.0.110'
		
	my_ip=get_ip_address(final_interface)
	address=(my_ip,AGENT_PORT)
	#-------------------------------------------------------------------------
	#Register to cluster
	
	sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect(cluster_leader_address)
	
	sndmsg_initial=cluster_message_class(REGISTRATION_TYPE,my_ip)
	sndmsg_initial=pickle.dumps(sndmsg_initial)
	
	#Send a message with the following structure: HEADER(20 Bytes) + pickled object
	cluster_message=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
	sock.sendall(cluster_message)
	
	received_bytes=HEADER_LENGTH
	
	data=bytes()
	while(1):
		data+= sock.recv(received_bytes)
		
		
		if(len(data)==HEADER_LENGTH):
			break
		received_bytes=HEADER_LENGTH-len(data)
		
	
	msg_len=int(data)
	received_bytes=msg_len
	
	#Receive the message after the header
	data=bytes()
	while(1):
		
		try:
			data+=sock.recv(received_bytes)
		except BlockingIOError:
			exit()
	
		if(len(data)==msg_len):
			break
		
		received_bytes=msg_len-len(data)
		
	rcvmsg=pickle.loads(data)
	sock.close()
	
	
	
	#-------------------------------------------------------------------------
	
	command = Thread(target=command_thread, args=[my_ip])
	#Start the poll thread
	command.start()
	
	
	
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
				
				rcvmsg=agent_message_class()
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
					
				if(rcvmsg.get_msg_type()==LEADER_PING_TYPE):
					cpufreq = psutil.cpu_freq()
					svmem = psutil.virtual_memory()
					
					sensors=[]
					position=""
					
					try:
						fd=open("agent_configuration_file.txt","r")
						sensors_configuration_file_available=1
					except IOError:
						print("Could not read agent configuration file")
					
					while(1):
						line=fd.readline()
						line=line.translate({ord('\n'): None})
						
						if(len(line)==0):
							continue
						
						print("line",line)
						if(line.split('=')[0]=="position"):
							position=line.split('=')[1]
							print(position)
						
						elif(line.split('=')[0]=="sensors"):
							
							sensors=line.split('=')[1].split('/')
							
							print(sensors)
							
						elif(line=="exit"):
							break
							
							
					sndmsg_initial=device_HW_characteristics(platform.processor(),psutil.cpu_count(logical=True),cpufreq.current,svmem.available,svmem.total,sensors,position)
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
					
				elif(rcvmsg.get_msg_type()==LEADER_CREATE_SERVICE_TYPE):
					
					
					print("leader asked me to run the command",rcvmsg.get_command())
					
					start=time.time()
					process=subprocess.Popen(rcvmsg.get_command(), stdout=subprocess. PIPE)
					process.communicate()
					end=time.time()
					
					print("GENERATION CONTAINER TIME=",end-start)
					
					print("send reply")
					sndmsg_initial=device_HW_characteristics()
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
					
				elif(rcvmsg.get_msg_type()==LEADER_DELETE_CONTAINER_TYPE):
					
					print("leader asked me to delete containers",rcvmsg.get_command())
					
					start=time.time()
					bashcmd = ["docker","ps","--format","table {{.Names}}\t"]
					
					process=subprocess.Popen(bashcmd, stdout=subprocess. PIPE)
					running_containers,error=process.communicate()
					running_containers=running_containers.decode('utf-8')
					running_containers=running_containers.split()
					
					for i in range(len(running_containers)):
						if(running_containers[i] in rcvmsg.get_command()):
						
							bashcmd = ["docker","container","rm","--force",running_containers[i]]
						
							process=subprocess.Popen(bashcmd, stdout=subprocess. PIPE)
							output,error=process.communicate()
							
					end=time.time()
					
					print("DELETE CONTAINER TIME=",end-start)
					
					print("send reply")
					
					print("send reply")
					sndmsg_initial=device_HW_characteristics()
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
					
					
				elif(rcvmsg.get_msg_type()==EXIT_REPLY_ACK_TYPE or rcvmsg.get_msg_type()==EXIT_REPLY_NACK_TYPE):
					
					print("send reply")
					sndmsg_initial=device_HW_characteristics()
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					reply_msg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					s.sendall(reply_msg)
					
					
					if(rcvmsg.get_msg_type()==EXIT_REPLY_ACK_TYPE):
						
						exit_mtx.acquire()
						exit_flag=1
						exit_mtx.release()
						return
					else:
						exit_mtx.acquire()
						exit_flag=0
						exit_mtx.release()
					
				
	
if __name__ == "__main__":
	
	main()


