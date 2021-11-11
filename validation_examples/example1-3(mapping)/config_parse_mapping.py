#Angelis Marios
#Thesis title: Dynamic deployment of stream processing applications usingdocker swarm
#This file contains the implementation of the load balancer running on top of the Docker Swarm

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
import psutil
import signal
import platform

F_Red = "\x1b[31m"
Reset = "\x1b[0m"

SLEEP_TIME=10
MAX_RETRANSMISSIONS=10

LEADER_PING_TYPE=14000
LEADER_CREATE_SERVICE_TYPE=15000
LEADER_DELETE_CONTAINER_TYPE=16000

LEADER_MESSAGE_TYPE=12000
CLOSE_DESTINATION_CONNECTIONS_TYPE=14000
MOVE_STATUS_CHECK=15000
START_MOVE_BUFFER_TYPE=18000
LEADER_MESSAGE_TYPE_MOVE_INITALIZATION=20000

INFORMATION_TYPE=2000
HEADER_LENGTH=20
CLUSTER_LEADER_PORT=7000
POLL_PORT=8000
AGENT_PORT=9000
PORT_ASSIGNMENT=9001

registry_ip="192.168.0.151"
cluster_leader_address=("192.168.0.151",CLUSTER_LEADER_PORT)
agent_instances=0
cluster_nodes=[]
flow_id=0
first=0
components=0
sequence_number=0
exit_flag=0
exit_mtx=Semaphore(1)
seq_num_mtx=Semaphore(1)
running_instances_table_message_mtx=Semaphore(1)
poll_thread_mtx=Semaphore(0)
placement_mtx=Semaphore(1)
current_service=None

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
		

class agent_message_class:
	def __init__(self,msg_type=0,command=0,seq=-1):
		self.msg_type=msg_type
		self.command=command
		self.sequence=seq
	
	def get_seq(self):
		return self.sequence
	
	def get_msg_type(self):
		return self.msg_type
		
	def get_command(self):
		return self.command
	
class cluster_message_class:
	
	def __init__(self,msg_type="",host_name="",device_ip=""):
		self.host_name=host_name
		self.device_ip=device_ip
		self.msg_type=msg_type
		
	def get_msg_type(self):
		return self.msg_type
		
	def get_device_ip(self):
		return self.device_ip
	
	def get_host_name(self):
		return self.host_name

def command_thread():
	
	global sequence_number
	global exit_flag
	global current_service
	
	while(1):
		
		command=input()
		command=command.split(" ")
		
		if(command[0]=="exit"):
			#Set the current service's running_instances_table
			for i in range(0,len(cluster_nodes)):
				
				#Ping the agent located in each device of the cluster in order to remove all the running containers.
				ip=cluster_nodes[i][1]
				
				device_address = (ip,AGENT_PORT)
				print("Trying to ping ",device_address)
				sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
				sock.settimeout(5.0)
				rcvmsg=device_HW_characteristics()
				
				seq_num_mtx.acquire()
				sequence_number+=1
				sent_seq=sequence_number
				seq_num_mtx.release()
				delete_message=pickle.dumps(agent_message_class(LEADER_DELETE_CONTAINER_TYPE,components,sent_seq))
				
				
				ack_received=0
				#Use at most once semantics
				for retransmissions in range(0,MAX_RETRANSMISSIONS):
					
					sock.sendto(delete_message,device_address)
					
					while(1):
						try:
							data, addr = sock.recvfrom(1024)
							rcvmsg=pickle.loads(data)
							
							if(rcvmsg.get_seq()==sent_seq):
								ack_received=1
								break
							else:
								continue
							
						except socket.timeout:
							print("Timeout")
							break
						
					if(ack_received==1):
						break
					
					
				if(ack_received==1):
					rcvmsg=pickle.loads(data)
					print("OK FROM AGENT")
					
			exit_mtx.acquire()
			exit_flag=1
			exit_mtx.release()
			sys.exit(0)
			
		elif(command[0]=="status"):
			#Print the current status
			current_service.print_running_instances_table()
	
		elif(command[0]=="move"):
			
			#move F1 from A to B
			if(len(command)!=6):
				print("Wrong number of arguments")
				continue
			
			component_to_move=command[1]
			from_device=command[3]
			to_device=command[5]
			
			placement_mtx.acquire()
			
			component_replicas_table=current_service.get_component_replicas_table()
			running_instances_table=current_service.get_original_running_instances_table()
			
			exit=0
			
			#Check if there is already a running instance on the same device
			for i in range(0,len(running_instances_table)):
				if(running_instances_table[i][0]==to_device):
					for j in range(0,len(running_instances_table[i][4])):
						if(component_to_move==running_instances_table[i][4][j].get_instance_name()):
							print("There is already a running instance on the same device. Can not move")
							exit=1
							break
					break
				
				
			if(exit==1):
				placement_mtx.release()
				continue
			
			#Check if the component to be moved exists 
			if(current_service.component_exists(component_to_move)==0):
				print("There is not such a component")
				placement_mtx.release()
				continue
			
			if(current_service.component_exists_in_device(component_to_move,from_device)==0):
				print("There is not such a component in device",from_device)
				placement_mtx.release()
				continue
			
			
			#Check if the "from_device" exists
			if(current_service.device_exists(from_device)==0):
				
				print("There is not device with name",from_device)
				placement_mtx.release()
				continue
			
			#Check if the "to_device" exists
			if(current_service.device_exists(to_device)==0):
				
				print("There is not device with name",to_device)
				placement_mtx.release()
				continue
				
			instances_table=current_service.get_original_running_instances_table()
			
			#Restart the changed state of all the running instances
			for i in range(0,len(instances_table)):
				for j in range(0,len(instances_table[i][4])):
					instances_table[i][4][j].set_changed_state(0)
			exit=0
			
			#Check the destination device's compatibility
			for i in range(0,len(component_replicas_table)):
				if(component_replicas_table[i][0]==component_to_move):
					if(to_device in component_replicas_table[i][4]):
						port=component_replicas_table[i][2]
					else:
						print("Can not move this component. Device is uncompatible")
						exit=1
					break
			
			if(exit==1):
				placement_mtx.release()
				continue
			
			#Fetch the image
			for i in range(0,len(cluster_nodes)):
				if(cluster_nodes[i][0]==to_device):
					
					bashCmd = ["docker","pull",registry_ip+":5000/"+current_service.find_image_name(component_to_move)+":latest"]
			
					device_address = (current_service.get_ip(to_device),AGENT_PORT)
					sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
					sock.settimeout(20.0)
					rcvmsg=device_HW_characteristics()
					
					seq_num_mtx.acquire()
					sequence_number+=1
					sent_seq=sequence_number
					seq_num_mtx.release()
					command_message=pickle.dumps(agent_message_class(LEADER_CREATE_SERVICE_TYPE,bashCmd,sent_seq))
					
					ack_received=0
					#Use at least once semantics
					while(1):
						sock.sendto(command_message,device_address)
						
						while(1):
							try:
								data, addr = sock.recvfrom(1024)
								rcvmsg=pickle.loads(data)
								if(rcvmsg.get_seq()==sent_seq):
									ack_received=1
									print("Got a right ack")
									break
								else:
									print("Got a false ack, dismiss the message")
									continue
								
							except socket.timeout:
								print("Timeout")
								break
							
						if(ack_received==1):
							break
			
			start = time.time()
			old_instance=current_service.get_running_instance(component_to_move,from_device)
			
			#Check the move status of the old instance
			move_status=send_move_status_check_message(component_to_move,from_device)
			print("MOVE_STATUS=",move_status)
			
			if(move_status==0):
				print("Can not move")
				placement_mtx.release()
				continue
			
			#Create the new instance after setting the destination and source flows
			#Do not change the status of the new_instance. This instance will be informed later
			new_instance=current_service.add_running_instance(component_to_move,to_device)
			new_instance.src_flow=old_instance.src_flow
			new_instance.src_component=old_instance.src_component
			new_instance.flow_id=old_instance.flow_id
			new_instance.dst_ip=old_instance.dst_ip
			new_instance.dst_port=old_instance.dst_port
			new_instance.dst_component=old_instance.dst_component
			
			link_table=current_service.get_link_table()
			
			left_reliability="unreliable"
			right_reliability="unreliable"
			
			for link_index in range(0,len(link_table)):
				
				link=link_table[link_index][0].split("->")
				left_component=link[0]
				right_component=link[1]
				
				if(right_component==component_to_move):
					left_reliability=link_table[link_index][2]
				elif(left_component==component_to_move):
					right_reliability=link_table[link_index][2]
			
			#Set all the links between the instance to move and its left instances
			for link_index in range(0,len(link_table)):
				
				link=link_table[link_index][0].split("->")
				left_component=link[0]
				right_component=link[1]
				
				if(right_component==component_to_move):
					
					for k in range(0,len(instances_table)):
						for j in range(0,len(instances_table[k][4])):
							
							if(instances_table[k][4][j].get_instance_name()==left_component):
								print(instances_table[k][4][j].dst_ip,instances_table[k][4][j].dst_component)
								
								for t in range(0,len(instances_table[k][4][j].get_dst_ip())):
									if(instances_table[k][4][j].dst_component[t]==component_to_move and instances_table[k][4][j].dst_ip[t]==current_service.get_ip(from_device)):
										
										instances_table[k][4][j].set_changed_state(1)
										instances_table[k][4][j].dst_ip[t]=current_service.get_ip(to_device)
										print("change ip from",current_service.get_ip(from_device),"to",current_service.get_ip(to_device))
										
			
			#Create the new container. ATTENTION The old instance is still running
			for i in range(0,len(cluster_nodes)):
				if(cluster_nodes[i][0]==to_device):
					
					bashCmd = ["docker","run","-d","--name",component_to_move,"--rm","--privileged","--network","host",registry_ip+":5000/"+current_service.find_image_name(component_to_move)+":latest",str(port)]
			
					device_address = (current_service.get_ip(to_device),AGENT_PORT)
					sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
					sock.settimeout(20.0)
					rcvmsg=device_HW_characteristics()
					
					seq_num_mtx.acquire()
					sequence_number+=1
					sent_seq=sequence_number
					seq_num_mtx.release()
					command_message=pickle.dumps(agent_message_class(LEADER_CREATE_SERVICE_TYPE,bashCmd,sent_seq))
					
					ack_received=0
					#Use at least once semantics
					while(1):
						sock.sendto(command_message,device_address)
						
						while(1):
							try:
								data, addr = sock.recvfrom(1024)
								rcvmsg=pickle.loads(data)
								if(rcvmsg.get_seq()==sent_seq):
									ack_received=1
									print("Got a right ack")
									break
								else:
									print("Got a false ack, dismiss the message")
									continue
								
							except socket.timeout:
								print("Timeout")
								break
							
						if(ack_received==1):
							break
			
			#Wait until all the instances are up and running
			while(1):
				running_instances_table_message_mtx.acquire()
				running_instances_table=current_service.get_original_running_instances_table()
				ready_instances=0
				total_istances=0
				
				for i in range(0,len(running_instances_table)):
					for j in range(0,len(running_instances_table[i][4])):
						total_istances+=1
						if(running_instances_table[i][4][j].get_poll_flag()==1):
							ready_instances+=1
				
				running_instances_table_message_mtx.release()
				if(total_istances==ready_instances):
					break
				else:
					print("System not ready. Try again after 2 seconds")
					time.sleep(2)
			
			#Inform the change state instances about the changed destination flows
			send_parser_message(component_to_move,to_device,LEADER_MESSAGE_TYPE_MOVE_INITALIZATION)
			
			
			if(left_reliability=="reliable"):
				#Inform only left instances. ATTENTION We want reliability
				inform_instances(1)
				print("left_reliability=reliable, send a START_MOVE_BUFFER_TYPE message")
				#Move all data from the old instance buffer to the new instance.
				send_parser_message(component_to_move,from_device,START_MOVE_BUFFER_TYPE,current_service.get_ip(to_device))
			else:
				#Inform only left instances. We dont want reliability
				inform_instances()
				
			if(right_reliability=="reliable"):
				print("right_reliability=reliable, send a CLOSE_DESTINATION_CONNECTIONS_TYPE message")
				#Close all the right connections of the old instance
				send_parser_message(component_to_move,from_device,CLOSE_DESTINATION_CONNECTIONS_TYPE,1)
				
			else:
				#Close all the right connections of the old instance
				send_parser_message(component_to_move,from_device,CLOSE_DESTINATION_CONNECTIONS_TYPE)
			
			#Delete the old instance
			current_service.delete_running_instance(component_to_move,from_device)
			new_instance.set_changed_state(1)
			
			#Inform the new instance about its src and destination flows
			inform_instances()
			
			#Delete the old instance container
			for i in range(0,len(cluster_nodes)):
				if(cluster_nodes[i][0]==from_device):
				
					ip=cluster_nodes[i][1]
					
					device_address = (ip,AGENT_PORT)
					print("Trying to ping ",device_address)
					sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
					sock.settimeout(5.0)
					rcvmsg=device_HW_characteristics()
					
					seq_num_mtx.acquire()
					sequence_number+=1
					sent_seq=sequence_number
					seq_num_mtx.release()
					delete_message=pickle.dumps(agent_message_class(LEADER_DELETE_CONTAINER_TYPE,[component_to_move],sent_seq))
					
					ack_received=0
					#Use at most once semantics
					for retransmissions in range(0,MAX_RETRANSMISSIONS):
						
						sock.sendto(delete_message,device_address)
						
						while(1):
							try:
								data, addr = sock.recvfrom(1024)
								rcvmsg=pickle.loads(data)
								
								if(rcvmsg.get_seq()==sent_seq):
									ack_received=1
									break
								else:
									continue
								
							except socket.timeout:
								print("Timeout")
								break
							
						if(ack_received==1):
							break
						
					if(ack_received==1):
						rcvmsg=pickle.loads(data)
						print("OK FROM AGENT, REMOVED COMPONENT")
						
			print("MOVE COMMAND FINISHED")
			placement_mtx.release()
			
			end = time.time()
			print("ELAPSED TIME IS ",end - start)
			
		else:
			print("Invalid command")

def poll_thread():
	
	global exit_flag
	global current_service
	
	def getAllInterfaces():
		return os.listdir('/sys/class/net/')
	
	def get_ip_address(ifname):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		return socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s',  bytes(ifname[:15], 'utf-8')))[20:24])
	
	def is_interface_up(interface):
		addr = netifaces.ifaddresses(interface)
		return netifaces.AF_INET in addr
	
	print("INSIDE POLL THREAD")

	interfaces=getAllInterfaces()
	final_interface=""
	
	for i in range(0,len(interfaces)):
		
		if(is_interface_up(interfaces[i])==True):
			if(interfaces[i][0]=='e'):
				final_interface=interfaces[i]
				break
			elif(interfaces[i][0]=='w'):
				final_interface=interfaces[i]

	my_ip=get_ip_address(final_interface)
	address=(my_ip,POLL_PORT)
	
	sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.settimeout(5.0)
	sock.bind(address)
	
	poll_thread_mtx.release()
	
	while(1):
		
		#receive a poll message from an istance
		rcvmsg=poll_message()
		try:
			rcvmsg, addr = sock.recvfrom(1024)
			rcvmsg=pickle.loads(rcvmsg)
		except socket.timeout:
			
			exit_mtx.acquire()
			if(exit_flag==1):
				exit_mtx.release()
				print("Poll thread exits")
				return()
			
			exit_mtx.release()
			
			continue
		
		print("Got a message from address",addr,"from instance=",rcvmsg.get_instance_name())
		
		reply_msg=pickle.dumps("ack")
		sock.sendto(reply_msg,addr)
		
		set_poll_flag=0
		
		running_instances_table_message_mtx.acquire()
		running_instances_table=current_service.get_original_running_instances_table()
		
		#Set the poll flag of the running instance which sent the message to 1
		for i in range(0,len(running_instances_table)):
			if(addr[0]==running_instances_table[i][3]):
				for j in range(0,len(running_instances_table[i][4])):
					if(running_instances_table[i][4][j].get_instance_name()==rcvmsg.get_instance_name()):
						running_instances_table[i][4][j].set_poll_flag(1)
						set_poll_flag=1
						break
				
				if(set_poll_flag==1):
					break
		
		running_instances_table_message_mtx.release()
		
#This algorithm creates the number of instances computed in the previous step for each component and places them into real nodes
def placement_algorithm():
	
	global flow_id
	global first
	global sequence_number
	global current_service
	
	print(F_Red,"Apply the placement algorithm...",Reset,sep='')
	
	if(first==0):
		first=1
		poll = Thread(target=poll_thread, args=[])
		#Start the poll thread
		poll.start()
		
		command = Thread(target=command_thread, args=[])
		command.start()
		poll_thread_mtx.acquire()
		print("START THE PLACEMENT ALGORITHM")
	
	
	#Get a copy of the link table
	link_table=current_service.get_link_table()
	
	#Scan the link_table in descending order of affinity
	#For each unchecked link, apply the following formula
	#Calculate the diff=current_replicas(Fx) - number_of_running_instances(Fx)
	#If diff>0,find the devices which are compatible with component Fx. From these devices, select those which have not a running Fx instance. (devices_list)
	#From the remaining devices, select those which are common with the same link's other component’s compatible devices.                      (common_devices_list)
	#Finally, select the devices which have a running instance of the same link's other component.                                        (common_devices_list_with_running_left_instance)
	#Create “diff” instances starting from bottom to top.
	
	start=time.time()
	#iterations=0
	internal_iterations=0
	while(1):
		#iterations+=1
		new_instances=0
		checked_links=[]
		current_service.reset_check_table()
		
		flow_id+=1
		
		for k in range(0,len(link_table)):
			internal_iterations+=1
			
			#print("111111111111111111111111111111111111111111111111111111111111111111111111111111")
		
			#Find the next link with the maximum affinity
			maximum_affinity=-1
			for i in range(0,len(link_table)):
				if((link_table[i][0] not in  checked_links) and int(link_table[i][1])>maximum_affinity):
					maximum_affinity=int(link_table[i][1])
					link=link_table[i][0]
					
			checked_links.append(link)
			
			link=link.split("->")
			left_component=link[0]
			right_component=link[1]
			
			#Apply the algorithm to the left component of this link
			if(current_service.is_checked(left_component)==0):
				current_service.set_checked(left_component)
				
				diff_left=int(current_service.get_current_replicas(left_component))-int(current_service.get_running_instances(left_component))
				
				if(diff_left>0):
					
					#print("222222222222222222222222222222222222222222222222222222222222222222")
					new_instances+=1
					
					right_component_compatible_devices=current_service.get_compatible_devices(right_component)
					left_component_compatible_devices=current_service.get_compatible_devices(left_component)
					devices_list=left_component_compatible_devices
					
					instances_table=current_service.get_running_instances_table()
					
					for i in range(0,len(instances_table)):
						for j in range(0,len(instances_table[i][4])):
							if(left_component==instances_table[i][4][j].get_instance_name()):
								devices_list.remove(instances_table[i][0])
								break
					
					common_devices_list=[]
					for i in range(0,len(devices_list)):
						if(devices_list[i] in right_component_compatible_devices):
							common_devices_list.append(devices_list[i])
					
					common_devices_list_with_running_right_instance=[]
					
					for i in range(0,len(instances_table)):
						if((instances_table[i][0] in common_devices_list)):
							for j in range(0,len(instances_table[i][4])):
								if(right_component==instances_table[i][4][j].get_instance_name()):
									common_devices_list_with_running_right_instance.append(instances_table[i][0])
					
					
					port=current_service.get_component_port(left_component)
				
					if(len(common_devices_list_with_running_right_instance)>0):
							
						print("create service",left_component,"on device",common_devices_list_with_running_right_instance[0])
						if(current_service.is_initialized(left_component)==0):
							current_service.initialize_component(left_component)
							
						#Add the new instance to the running_instances_table
						new_instance=current_service.add_running_instance(left_component,common_devices_list_with_running_right_instance[0])
						
						'''bashCmd = ["docker","run","-d","--name",left_component,"--rm","--privileged","--network","host",registry_ip+":5000/"+current_service.find_image_name(left_component)+":latest",str(port)]
						
						device_address = (current_service.get_ip(common_devices_list_with_running_right_instance[0]),AGENT_PORT)
						sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
						sock.settimeout(20.0)
						rcvmsg=device_HW_characteristics()
						
						seq_num_mtx.acquire()
						sequence_number+=1
						sent_seq=sequence_number
						seq_num_mtx.release()
						command_message=pickle.dumps(agent_message_class(LEADER_CREATE_SERVICE_TYPE,bashCmd,sent_seq))
						
						ack_received=0
						#Use at least once semantics
						while(1):
							
							sock.sendto(command_message,device_address)
							
							while(1):
								try:
									data, addr = sock.recvfrom(1024)
									rcvmsg=pickle.loads(data)
									
									print("msg seq=",rcvmsg.get_seq(),"and exp=",sent_seq)
									if(rcvmsg.get_seq()==sent_seq):
										ack_received=1
										print("Got a right ack")
										break
									else:
										print("Got a false ack, dismiss the message")
										continue
									
								except socket.timeout:
									print("Timeout")
									break
								
							if(ack_received==1):
								break
					'''	
						common_devices_list.remove(common_devices_list_with_running_right_instance[0])
						devices_list.remove(common_devices_list_with_running_right_instance[0])
						common_devices_list_with_running_right_instance.remove(common_devices_list_with_running_right_instance[0])
						
					
					elif(len(common_devices_list)>0):
						#Add a label to the device in which the new instance will run
						
						print("create service",left_component,"on device",common_devices_list[0])
						if(current_service.is_initialized(left_component)==0):
							current_service.initialize_component(left_component)
							
						#Add the new instance to the running_instances_table
						new_instance=current_service.add_running_instance(left_component,common_devices_list[0])
						
						'''
						bashCmd = ["docker","run","-d","--name",left_component,"--rm","--privileged","--network","host",registry_ip+":5000/"+current_service.find_image_name(left_component)+":latest",str(port)]
						
						device_address = (current_service.get_ip(common_devices_list[0]),AGENT_PORT)
						sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
						sock.settimeout(20.0)
						rcvmsg=device_HW_characteristics()
						
						seq_num_mtx.acquire()
						sequence_number+=1
						sent_seq=sequence_number
						seq_num_mtx.release()
						command_message=pickle.dumps(agent_message_class(LEADER_CREATE_SERVICE_TYPE,bashCmd,sent_seq))
						
						ack_received=0
						#Use at least once semantics
						while(1):
							
							sock.sendto(command_message,device_address)
							
							while(1):
								try:
									data, addr = sock.recvfrom(1024)
									rcvmsg=pickle.loads(data)
									print("msg seq=",rcvmsg.get_seq(),"and exp=",sent_seq)
									if(rcvmsg.get_seq()==sent_seq):
										ack_received=1
										print("Got a right ack")
										break
									else:
										print("Got a false ack, dismiss the message")
										continue
									
								except socket.timeout:
									print("Timeout")
									break
								
							if(ack_received==1):
								break
						'''
						devices_list.remove(common_devices_list[0])
						common_devices_list.remove(common_devices_list[0])
						
					
					elif(len(devices_list)>0):
						
						print("create service",left_component,"on device",devices_list[0])
						if(current_service.is_initialized(left_component)==0):
							current_service.initialize_component(left_component)
						
						#Add the new instance to the running_instances_table
						new_instance=current_service.add_running_instance(left_component,devices_list[0])
						
						'''
						bashCmd = ["docker","run","-d","--name",left_component,"--rm","--privileged","--network","host",registry_ip+":5000/"+current_service.find_image_name(left_component)+":latest",str(port)]
						
						device_address = (current_service.get_ip(devices_list[0]),AGENT_PORT)
						sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
						sock.settimeout(20.0)
						rcvmsg=device_HW_characteristics()
						
						seq_num_mtx.acquire()
						sequence_number+=1
						sent_seq=sequence_number
						seq_num_mtx.release()
						command_message=pickle.dumps(agent_message_class(LEADER_CREATE_SERVICE_TYPE,bashCmd,sent_seq))
							
						ack_received=0
						#Use at least once semantics
						while(1):
							
							sock.sendto(command_message,device_address)
							
							while(1):
								try:
									data, addr = sock.recvfrom(1024)
									rcvmsg=pickle.loads(data)
									print("msg seq=",rcvmsg.get_seq(),"and exp=",sent_seq)
									if(rcvmsg.get_seq()==sent_seq):
										ack_received=1
										print("Got a right ack")
										break
									else:
										print("Got a false ack, dismiss the message")
										continue
									
								except socket.timeout:
									print("Timeout")
									break
								
							if(ack_received==1):
								break
						'''
						devices_list.remove(devices_list[0])
				
					if(current_service.get_component(left_component).is_singular()==0):
						new_instance.add_flow_num(flow_id)
						
			#Apply the algorithm to the left component of this pair
			if(current_service.is_checked(right_component)==0):
				current_service.set_checked(right_component)
				
				diff_right=int(current_service.get_current_replicas(right_component))-int(current_service.get_running_instances(right_component))
				
				if(diff_right>0):
					#print("333333333333333333333333333333333333333333333333333333333333333333")
					new_instances+=1
					
					right_component_compatible_devices=current_service.get_compatible_devices(right_component)
					left_component_compatible_devices=current_service.get_compatible_devices(left_component)
					devices_list=right_component_compatible_devices
					
					instances_table=current_service.get_running_instances_table()
							
					for i in range(0,len(instances_table)):
						for j in range(0,len(instances_table[i][4])):
							if(right_component==instances_table[i][4][j].get_instance_name()):
								devices_list.remove(instances_table[i][0])
								break
					
					common_devices_list=[]
					for i in range(0,len(devices_list)):
						if(devices_list[i] in left_component_compatible_devices):
							common_devices_list.append(devices_list[i])
					
					common_devices_list_with_running_left_instance=[]
					
					for i in range(0,len(instances_table)):
						if((instances_table[i][0] in common_devices_list)):
							
							for j in range(0,len(instances_table[i][4])):
								if(left_component==instances_table[i][4][j].get_instance_name()):
									common_devices_list_with_running_left_instance.append(instances_table[i][0])
							
					port=current_service.get_component_port(right_component)
					
					if(len(common_devices_list_with_running_left_instance)>0):
						
						print("create service",right_component,"on device",common_devices_list_with_running_left_instance[0])
						if(current_service.is_initialized(right_component)==0):
							current_service.initialize_component(right_component)
							
							
						#Add the new instance to the running_instances_table
						new_instance=current_service.add_running_instance(right_component,common_devices_list_with_running_left_instance[0])
						
						'''
						bashCmd = ["docker","run","-d","--name",right_component,"--rm","--privileged","--network","host",registry_ip+":5000/"+current_service.find_image_name(right_component)+":latest",str(port)]
						
						device_address = (current_service.get_ip(common_devices_list_with_running_left_instance[0]),AGENT_PORT)
						sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
						sock.settimeout(20.0)
						rcvmsg=device_HW_characteristics()
						
						seq_num_mtx.acquire()
						sequence_number+=1
						sent_seq=sequence_number
						seq_num_mtx.release()
						command_message=pickle.dumps(agent_message_class(LEADER_CREATE_SERVICE_TYPE,bashCmd,sent_seq))
						
						ack_received=0
						#Use at least once semantics
						while(1):
							
							sock.sendto(command_message,device_address)
							
							while(1):
								try:
									data, addr = sock.recvfrom(1024)
									rcvmsg=pickle.loads(data)
									print("msg seq=",rcvmsg.get_seq(),"and exp=",sent_seq)
									if(rcvmsg.get_seq()==sent_seq):
										ack_received=1
										print("Got a right ack")
										break
									else:
										print("Got a false ack, dismiss the message")
										continue
									
								except socket.timeout:
									print("Timeout")
									break
								
							if(ack_received==1):
								break
						'''
						common_devices_list.remove(common_devices_list_with_running_left_instance[0])
						devices_list.remove(common_devices_list_with_running_left_instance[0])
						common_devices_list_with_running_left_instance.remove(common_devices_list_with_running_left_instance[0])
					
					elif(len(common_devices_list)>0):
						
						print("create service",right_component,"on device",common_devices_list[0])
						
						if(current_service.is_initialized(right_component)==0):
							current_service.initialize_component(right_component)
							
						#Add the new instance to the running_instances_table
						new_instance=current_service.add_running_instance(right_component,common_devices_list[0])
						
						'''
						bashCmd = ["docker","run","-d","--name",right_component,"--rm","--privileged","--network","host",registry_ip+":5000/"+current_service.find_image_name(right_component)+":latest",str(port)]
						
						device_address = (current_service.get_ip(common_devices_list[0]),AGENT_PORT)
						sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
						sock.settimeout(20.0)
						rcvmsg=device_HW_characteristics()
						
						seq_num_mtx.acquire()
						sequence_number+=1
						sent_seq=sequence_number
						seq_num_mtx.release()
						command_message=pickle.dumps(agent_message_class(LEADER_CREATE_SERVICE_TYPE,bashCmd,sent_seq))
						
						ack_received=0
						#Use at least once semantics
						while(1):
							
							sock.sendto(command_message,device_address)
							
							while(1):
								try:
									data, addr = sock.recvfrom(1024)
									rcvmsg=pickle.loads(data)
									print("msg seq=",rcvmsg.get_seq(),"and exp=",sent_seq)
									if(rcvmsg.get_seq()==sent_seq):
										ack_received=1
										print("Got a right ack")
										break
									else:
										print("Got a false ack, dismiss the message")
										continue
									
								except socket.timeout:
									print("Timeout")
									break
								
							if(ack_received==1):
								break
						'''
						devices_list.remove(common_devices_list[0])
						common_devices_list.remove(common_devices_list[0])
					
					elif(len(devices_list)>0):
						
						print("create service",right_component,"on device",devices_list[0])
						if(current_service.is_initialized(right_component)==0):
							current_service.initialize_component(right_component)
							
						#Add the new instance to the running_instances_table
						new_instance=current_service.add_running_instance(right_component,devices_list[0])
							
						'''
						bashCmd = ["docker","run","-d","--name",right_component,"--rm","--privileged","--network","host",registry_ip+":5000/"+current_service.find_image_name(right_component)+":latest",str(port)]
						
						device_address = (current_service.get_ip(devices_list[0]),AGENT_PORT)
						sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
						sock.settimeout(20.0)
						rcvmsg=device_HW_characteristics()
						
						seq_num_mtx.acquire()
						sequence_number+=1
						sent_seq=sequence_number
						seq_num_mtx.release()
						command_message=pickle.dumps(agent_message_class(LEADER_CREATE_SERVICE_TYPE,bashCmd,sent_seq))
						
						ack_received=0
						#Use at least once semantics
						while(1):
							
							sock.sendto(command_message,device_address)
							
							while(1):
								try:
									data, addr = sock.recvfrom(1024)
									rcvmsg=pickle.loads(data)
									print("msg seq=",rcvmsg.get_seq(),"and exp=",sent_seq)
									if(rcvmsg.get_seq()==sent_seq):
										ack_received=1
										print("Got a right ack")
										break
									else:
										print("Got a false ack, dismiss the message")
										continue
									
								except socket.timeout:
									print("Timeout")
									break
								
							if(ack_received==1):
								break
							'''
						devices_list.remove(devices_list[0])
						
					if(current_service.get_component(right_component).is_singular()==0):
						new_instance.add_flow_num(flow_id)
						
		if(new_instances==0):
			flow_id-=1
			break
		
	end=time.time()
	print("POSITION ALGORITHM ELAPSED TIME=",end-start,"iterations=",internal_iterations)
	
	while(1):
		print("22222")
		time.sleep(1)
	#set_links_between_instances()
	
	return()
	
def set_links_between_instances():
	
	global flow_id
	global current_service
	
	#Set links between instances
	print(F_Red,"Set links between instances...",Reset,sep='')
	#Get the original instances_table and a copy of the link_table
	instances_table=current_service.get_original_running_instances_table()
	link_table=current_service.get_link_table()
	
	
	for i in range(0,len(instances_table)):
		for j in range(0,len(instances_table[i][4])):
			instances_table[i][4][j].set_changed_state(0)
	
	for link_index in range(0,len(link_table)):
		
		link=link_table[link_index][0].split("->")
		left_component=link[0]
		right_component=link[1]
		
		print("left is",left_component,"and right is",right_component)
		right_component_port=current_service.get_component_port(right_component)
		
		#Set available ports for each right component of the graph
		for i in range(0,len(instances_table)):
			for j in range(0,len(instances_table[i][4])):
				if(instances_table[i][4][j].get_instance_name()==left_component):
					#instances_table[i][4][j].set_initialized_flag(0)
					continue
					
				if(instances_table[i][4][j].get_instance_name()==right_component):
					if(current_service.get_component(right_component).is_singular()==1):
						instances_table[i][4][j].set_available_ports(current_service.get_current_replicas(left_component))
					else:
						instances_table[i][4][j].set_available_ports(1)
						
		if(current_service.get_component(left_component).is_singular()==1):
			#Try to match each left_component of each pair with "fan_out_ports" right_components which is running on the same device 
			for i in range(0,len(instances_table)):
				for j in range(0,len(instances_table[i][4])):
					found_left_singular=0
					if(instances_table[i][4][j].get_instance_name()==left_component):
						
						found_left_singular=1
						fan_out_loop=current_service.get_current_replicas(right_component)
						
						if(current_service.get_component(right_component).is_singular()==1):
							print("left and right are singular components")
							found_right_component=0
							for k in range(0,len(instances_table)):
								for m in range(0,len(instances_table[k][4])):
									
									if(instances_table[k][4][m].get_instance_name()==right_component):
										#print("Found right in other device,add port",right_component_port)
										for w in range(1,flow_id+1):
											found_same_entry=0
											
											#This function can be called more than one times because some devices could be inserted to the cluster and the algorithm may update the number of running instances. If a same entry has been inserted, do not add it again.
											for t in range(0,len(instances_table[i][4][j].get_dst_ip())):
												if((instances_table[i][4][j].get_dst_ip()[t]==instances_table[k][3]) and (instances_table[i][4][j].get_dst_port()[t]==right_component_port) and (instances_table[i][4][j].get_dst_components()[t]==right_component) and (instances_table[i][4][j].get_flow_num()[t]==w)):
													found_same_entry=1
												
											if(found_same_entry==0):
												instances_table[i][4][j].set_changed_state(1)
												instances_table[k][4][m].set_changed_state(1)
												instances_table[i][4][j].add_dst_ip(instances_table[k][3])
												instances_table[i][4][j].add_dst_component(right_component)
												instances_table[i][4][j].add_dst_port(right_component_port)
												instances_table[i][4][j].add_flow_num(w)
												instances_table[k][4][m].add_scr_component(left_component)
												instances_table[k][4][m].add_scr_flow(w)
												
										instances_table[k][4][m].decrease_available_ports()
										found_right_component=1
										break
								if(found_right_component==1):
									break
						
						else:
							print("only left component is singular ==> fan out")
							print("Establish",fan_out_loop,"connections")
							
							#Establish "fan_out_loop" connections between this left component and "fan_out_loop" right components
							for w in range(0,fan_out_loop):
								found_right_component=0
								for k in range(0,len(instances_table)):
									for m in range(0,len(instances_table[k][4])):
										
										if(instances_table[k][4][m].get_instance_name()==right_component and instances_table[k][4][m].get_available_ports()>0):
											
											found_same_entry=0
											#This function can be called more than one times because some devices could be inserted to the cluster and the algorithm may update the number of running instances. If a same entry has been inserted, do not add it again.
											for t in range(0,len(instances_table[i][4][j].get_dst_ip())):
												if((instances_table[i][4][j].get_dst_ip()[t]==instances_table[k][3]) and (instances_table[i][4][j].get_dst_port()[t]==right_component_port) and (instances_table[i][4][j].get_dst_components()[t]==right_component) and (instances_table[i][4][j].get_flow_num()[t]==instances_table[k][4][m].get_flow_num()[0])):
													found_same_entry=1
													break
												
											if(found_same_entry==0):
												instances_table[i][4][j].set_changed_state(1)
												instances_table[k][4][m].set_changed_state(1)
												#print("Found right in other device,add port",right_component_port)
												instances_table[i][4][j].add_dst_ip(instances_table[k][3])
												instances_table[i][4][j].add_flow_num(instances_table[k][4][m].get_flow_num()[0])
												instances_table[i][4][j].add_dst_component(right_component)
												instances_table[i][4][j].add_dst_port(right_component_port)
												instances_table[k][4][m].add_scr_component(left_component)
												instances_table[k][4][m].add_scr_flow(instances_table[k][4][m].get_flow_num()[0])
												
											instances_table[k][4][m].decrease_available_ports()
											found_right_component=1
											break
									if(found_right_component==1):
										break
								
						#instances_table[i][4][j].set_initialized_flag(1)
						break
					
				if(found_left_singular==1):
					break
			
		else:
			#Try to match each left_component of each link with a right_component which is running on the same device
			print("left is not a singular component")
			for i in range(0,len(instances_table)):
				found_right_component=0
				for j in range(0,len(instances_table[i][4])):
					if(instances_table[i][4][j].get_instance_name()==left_component):
						
						left_flow=instances_table[i][4][j].get_flow_num()[0]
						
						for k in range(0,len(instances_table)):
							for m in range(0,len(instances_table[k][4])):
								
								#This function can be called more than one times because some devices could be inserted to the cluster and the algorithm may update the number of running instances. If a same entry has been inserted, do not add it again.
								if((instances_table[k][4][m].get_instance_name()==right_component and left_flow in instances_table[k][4][m].get_flow_num()) or (instances_table[k][4][m].get_instance_name()==right_component and current_service.get_component(right_component).is_singular()==1)):
									found_same_entry=0
									
									for t in range(0,len(instances_table[i][4][j].get_dst_ip())):
										if((instances_table[i][4][j].get_dst_ip()[t]==instances_table[k][3]) and (instances_table[i][4][j].get_dst_port()[t]==right_component_port) and (instances_table[i][4][j].get_dst_components()[t]==right_component) and (instances_table[i][4][j].get_flow_num()[t]==left_flow)):
											found_same_entry=1
											break
										
									if(found_same_entry==0):
										instances_table[i][4][j].set_changed_state(1)
										instances_table[k][4][m].set_changed_state(1)
										#print("Found right in other device,add port",right_component_port)
										
										instances_table[i][4][j].add_dst_ip(instances_table[k][3])
										instances_table[i][4][j].add_dst_component(right_component)
										instances_table[i][4][j].add_dst_port(right_component_port)
										instances_table[k][4][m].add_scr_component(left_component)
										instances_table[k][4][m].add_scr_flow(left_flow)
										
										#The left component has already a flow at the first position.
										if(len(instances_table[i][4][j].get_dst_ip())>1):
											instances_table[i][4][j].add_flow_num(left_flow)
										
									found_right_component=1
									instances_table[k][4][m].decrease_available_ports()
									#instances_table[i][4][j].set_initialized_flag(1)
									break
								
							if(found_right_component==1):
								break
							
						if(found_right_component==1):
							break
						
	current_service.print_running_instances_table()
	
	#Wait until all the instances are up and running
	while(1):
		running_instances_table_message_mtx.acquire()
		running_instances_table=current_service.get_original_running_instances_table()
		ready_instances=0
		total_istances=0
		
		for i in range(0,len(running_instances_table)):
			for j in range(0,len(running_instances_table[i][4])):
				total_istances+=1
				if(running_instances_table[i][4][j].get_poll_flag()==1):
					ready_instances+=1
		
		running_instances_table_message_mtx.release()
		
		print("total_istances=",total_istances,"ready_instances=",ready_instances)
		
		if(total_istances==ready_instances):
			break
		else:
			print("System not ready. Try again after 2 seconds")
			time.sleep(2)
			
	#Inform the change state instances about the changed destination flows
	inform_instances()


def send_parser_message(component_name,device_name,message_type,dst_ip="",reliability=0):
	
	global flow_id
	global current_service
	
	#Inform each instance about the destination ip and the destination port of its data
	instances_table=current_service.get_running_instances_table()
	
	#Add the new instance to the running_instances_table
	for i in range(0,len(instances_table)):
		if(device_name==instances_table[i][0]):
			for j in range(0,len(instances_table[i][4])):
				if(component_name==instances_table[i][4][j].get_instance_name()):
					sndmsg_initial=message_class(message_type,0,dst_ip)
					sndmsg_initial.set_reliability(reliability)
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					component_address = (instances_table[i][3],current_service.get_component_port(instances_table[i][4][j].get_instance_name()))
					#Create a tcp socket
					sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					
					while(1):
						try:
							sock.connect(component_address)
							
							break
						except socket.error:
							print("CAN NOT CONNECT")
							continue
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
					
					sock.sendall(sndmsg)
					data=sock.recv(1000)
					sock.close()
					return()
				
def send_move_status_check_message(component_name,device_name):
	
	global flow_id
	global current_service
	
	instances_table=current_service.get_running_instances_table()
	
	#Ask the move status from the old instance. This is a communication between the parser and the old instance.
	for i in range(0,len(instances_table)):
		if(device_name==instances_table[i][0]):
			for j in range(0,len(instances_table[i][4])):
				if(component_name==instances_table[i][4][j].get_instance_name()):
					sndmsg_initial=message_class(MOVE_STATUS_CHECK)
					sndmsg_initial=pickle.dumps(sndmsg_initial)
					
					component_address = (instances_table[i][3],current_service.get_component_port(instances_table[i][4][j].get_instance_name()))
					#Create a tcp socket
					sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					
					while(1):
						try:
							sock.connect(component_address)
							break
						except socket.error:
							print("CAN NOT CONNECT")
							continue
					
					#Send a message with the following structure: HEADER(20 Bytes) + pickled object
					sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
						
					sock.sendall(sndmsg)
					
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
						
					move_status=pickle.loads(data)
					sock.close()
					return move_status
				
def inform_instances(reliability=0):
	
	global flow_id
	global current_service
	
	#Inform each instance about the destination ip and the destination port of its data.
	#Reliable flag is used from the move command in order to urge the left instances to check if all the sent data have reached their destination.
	instances_table=current_service.get_running_instances_table()
	for i in range(0,len(instances_table)):
		print("--------------- Device",instances_table[i][0],"---------------")
		for j in range(0,len(instances_table[i][4])):
			
			if(instances_table[i][4][j].get_changed_state()==1):
				#If this is the last component of the graph and there are not cycles, the instances_table[i][4][j].get_dst_ip() and the instances_table[i][4][j].get_dst_port() will be empty
				print("component",instances_table[i][4][j].get_instance_name(),"connected with ip",instances_table[i][4][j].get_dst_ip(),"and port",instances_table[i][4][j].get_dst_port())
				
				sndmsg_initial=message_class(LEADER_MESSAGE_TYPE,-1,instances_table[i][4][j].get_dst_ip(),instances_table[i][4][j].get_dst_port(),instances_table[i][4][j].get_dst_components(),instances_table[i][4][j].get_flow_num(),current_service.get_component(instances_table[i][4][j].get_instance_name()).is_singular(),instances_table[i][4][j].get_src_components(),instances_table[i][4][j].get_src_flows(),reliability)
                
				sndmsg_initial=pickle.dumps(sndmsg_initial)
				
				component_address = (instances_table[i][3],current_service.get_component_port(instances_table[i][4][j].get_instance_name()))
				#Create a tcp socket
				sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
				while(1):
					try:
						sock.connect(component_address)
						
						break
					except socket.error:
						print("CAN NOT CONNECT")
						continue
				
				#Send a message with the following structure: HEADER(20 Bytes) + pickled object
				sndmsg=bytes(f'{len(sndmsg_initial):<{HEADER_LENGTH}}',"utf-8") + sndmsg_initial
				
				sock.sendall(sndmsg)
				data=sock.recv(1000)
				sock.close()
				
	print(F_Red,"Finished, all instances are running smoothly",Reset,sep='')
	

#This function calculates the current replica column of the service's "component_replicas_table"
def calculate_current_replicas():
	
	global current_service
	print(F_Red,"Calculate the current replicas column...",Reset,sep='')
	
	#Get a copy of the link_table
	link_table=current_service.get_link_table()
	component_replicas_table=current_service.get_component_replicas_table()
	
	for i in range(0,len(component_replicas_table)):
		current_service.set_current_replicas(component_replicas_table[i][0],1)
	
	compatibility_table=[]
	print(len(component_replicas_table))
	
	#We have computed the minimum replicas table. Lets try to meet the desired state
	for i in range(0,len(component_replicas_table)):
		if(current_service.get_component(component_replicas_table[i][0]).is_singular()==0):
			compatibility_table.append(int(len(component_replicas_table[i][4])/component_replicas_table[i][1]))
		
	#We have computed the minimum replicas table. Lets try to meet the desired state
	for i in range(0,len(component_replicas_table)):
		if(current_service.get_component(component_replicas_table[i][0]).is_singular()==1 and int(len(component_replicas_table[i][4]))==0):
			print("Compatible devices are less than the minimum state")
			return -1
	
	if(current_service.get_as_many_as_possible_parameter()==0):
		minimum=min(min(compatibility_table),current_service.get_desired_state_factor())
	else:
		#All components are singular
		if(len(compatibility_table)==0):
			minimum=1
		else:
			minimum=min(compatibility_table)
		
	#print("minimum is",minimum)
	
	if(minimum==0):
		print("Compatible devices are less than the minimum state")
		return -1
	else:
		#Compute the best deployment in the current infrastructure
		for i in range(0,len(component_replicas_table)):
			if(current_service.get_component(component_replicas_table[i][0]).is_singular()==0):
				current_service.set_current_replicas(component_replicas_table[i][0],component_replicas_table[i][1]*minimum)
	
	current_service.print_component_replicas_table()
	return 1


def main(config_name):
	
	global sequence_number
	global cluster_nodes
	global components
	global exit_flag
	global PORT_ASSIGNMENT
	global current_service
	
	try:
		fd=open(config_name,"r")
	except IOError:
		print("Could not read configuration file")
		return()
	
	while(1):
		
		line=fd.readline()
		line=line.translate({ord('\n'): None})
		
		#Skip empty lines
		if len(line)==0 or line=="----global configuration----":
			continue
		
		split_line=line.split()
		if split_line[0]=="components:":
			
			#ex components=["F1","F2","F3","F4"]
			components=split_line[1].split(",")
			
			#Create a service object
			current_service=service(len(components))
			
			while(1):
				line=fd.readline()
				line=line.translate({ord('\n'): None})
				
				#Skip empty lines
				if len(line)==0:
					continue
				
				split_line=line.split()
				if split_line[0]=="scale:":
					if split_line[1]=="as_many_as_possible":
						current_service.set_as_many_as_possible_parameter(1)
					else:
						current_service.set_desired_scale_factor(int(split_line[1]))
					break
				
			#Parse the configuration file to specify the parameters for each component of the graph
			for i in range(0,len(components)):
				while(1):
					line=fd.readline()
					line=line.translate({ord('\n'): None})
					#Skip empty lines
					if len(line)==0:
						continue
					
					split_line=line.split()
					
					#component Fi
					if(split_line[0]=="component:"):
						current_service.add_component(component(components[i]))
						current_service.get_component(components[i]).set_name(split_line[1])
						
					elif(split_line[0]=="source_files_directory:"):
						current_service.get_component(components[i]).set_source_files_directory(split_line[1])
						
					elif(split_line[0]=="position:"):
						current_service.get_component(components[i]).set_position(split_line[1])
						
					elif(split_line[0]=="mandatory:"):
						if(split_line[1]=="yes"):
							current_service.get_component(components[i]).set_mandatory(1)
						else:
							current_service.get_component(components[i]).set_mandatory(0)
							
					elif(split_line[0]=="singular:"):
						if(split_line[1]=="yes"):
							current_service.get_component(components[i]).set_singular(1)
						else:
							current_service.get_component(components[i]).set_singular(0)
						
					elif(split_line[0]=="ram:"):
						current_service.get_component(components[i]).set_ram(int(split_line[1]))
						
					elif(split_line[0]=="processor:"):
						current_service.get_component(components[i]).set_processor(split_line[1])
						
					elif(split_line[0]=="cpu_cores:"):
						current_service.get_component(components[i]).set_cpu_cores(int(split_line[1]))
						
					elif(split_line[0]=="sensors:"):
						current_service.get_component(components[i]).set_sensors(split_line[1])
						
					elif(split_line[0]=="ports_inside_container:"):
						current_service.get_component(components[i]).set_ports_inside_container(int(split_line[1]))
						
					elif(split_line[0]=="status:"):
						current_service.get_component(components[i]).set_status(split_line[1])
						
					elif(split_line[0]=="----Links----"):
						
						while(1):
							line=fd.readline()
							line=line.translate({ord('\n'): None})
							#Skip empty lines
							if len(line)==0:
								continue
							elif line=="end_component":
								break
							
							split_line=line.split(",")
							current_service.set_link_table(split_line[0],int(split_line[1]),split_line[2])
						break
				
			break
		else:
			print("Error during parsing the configuration file")
			return
	
	'''
	#Build an image for each component
	for i in range(0,len(components)):
		current_component=current_service.get_component(components[i])
		current_service.set_image_name(components[i],components[i].lower())
		
		platforms=""
		
		components_processor_list=current_service.get_component(components[i]).get_processor().split("/")
		for j in range(0,len(components_processor_list)):
			if(components_processor_list[j]=="x86_64"):
				platforms+="linux/amd64,"
			elif(components_processor_list[j]=="aarch64"):
				platforms+="linux/arm64,"
				
		platforms=platforms[:len(platforms)-1]
		
		print("component",components[i],"source files inside",current_component.get_source_files_directory(),"directory, image name=",current_service.find_image_name(components[i]))
		
		bashCmd = ["docker","buildx","build","--platform",platforms,"--push","-t",registry_ip+":5000/"+current_service.find_image_name(components[i])+":latest",current_component.get_source_files_directory()+"/"]
		
		process = subprocess.Popen(bashCmd, stdout=subprocess. PIPE,stderr=subprocess. PIPE)
		output, error = process.communicate()
	'''
	#Print the links between the components
	current_service.print_link_table()
	
	previous_step_available_devices=0
	node_id_table=[]
	devices=[]
	current_replicas=[]
	
	#Node handler
	while(1):
		
		#Find the cluster's available nodes
		#Send a message to cluster leader in order to receive the information of the cluster
		udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
		udp_sock.settimeout(5.0)
		
		cluster_message=pickle.dumps(cluster_message_class(INFORMATION_TYPE))
		
		ack_received=0
		#Use at least once semantics
		while(1):
			
			udp_sock.sendto(cluster_message,cluster_leader_address)
			
			while(1):
				try:
					data, addr = udp_sock.recvfrom(1024)
					cluster_nodes=pickle.loads(data)
					ack_received=1
					
				except socket.timeout:
					break
				
			if(ack_received==1):
				break
			
		exit_mtx.acquire()
		if(exit_flag==1):
			exit_mtx.release()
			print("Main exits")
			return()
		
		exit_mtx.release()
		
		#Current nodes are more than the previous step's available devices
		if(len(cluster_nodes)>previous_step_available_devices):
			
			#Desired state is a real number
			if(current_service.get_as_many_as_possible_parameter()==0):
				#Check if the current state of each component is the same as the desired state
				component_replicas_table=current_service.get_component_replicas_table()
				
				desired_equals_current=0
				for i in range(0,len(component_replicas_table)):
					if(int(component_replicas_table[i][2])==int(component_replicas_table[i][3])):
						desired_equals_current+=1
				
				#If the desired state is equal to the current state for all the components, we have met the user's desired state, so we dont make any changes 
				if(desired_equals_current==len(component_replicas_table) and len(component_replicas_table)!=0):
					print(F_Red,"Met the desired state...",Reset,sep='')
					time.sleep(SLEEP_TIME)
					continue
			
			current_service.reset_check_table()
			
			placement_mtx.acquire()
			
			#TEMPORARY *************************************************************
			
			cpufreq = psutil.cpu_freq()
			svmem = psutil.virtual_memory()
			sensors=[]
			ip="192.168.1.104"
			device_names=0
			
			
			sensors=["camera"]
			rcvmsg=device_HW_characteristics(platform.processor(),psutil.cpu_count(logical=True),cpufreq.current,4000000000,4000000000,sensors,"end")
			current_service.set_running_instances_table("device"+str(device_names),rcvmsg,rcvmsg.get_position(),ip,[])
			devices.append("device"+str(device_names))
			device_names+=1
			
			'''
			sensors=["camera"]
			rcvmsg=device_HW_characteristics(platform.processor(),psutil.cpu_count(logical=True),cpufreq.current,8000000000,8000000000,sensors,"end")
			current_service.set_running_instances_table("device"+str(device_names),rcvmsg,rcvmsg.get_position(),ip,[])
			devices.append("device"+str(device_names))
			device_names+=1
			
			sensors=["camera"]
			rcvmsg=device_HW_characteristics(platform.processor(),psutil.cpu_count(logical=True),cpufreq.current,4000000000,4000000000,sensors,"edge")
			current_service.set_running_instances_table("device"+str(device_names),rcvmsg,rcvmsg.get_position(),ip,[])
			devices.append("device"+str(device_names))
			device_names+=1
			
			sensors=["camera","gpu"]
			rcvmsg=device_HW_characteristics(platform.processor(),psutil.cpu_count(logical=True),cpufreq.current,8000000000,8000000000,sensors,"edge")
			current_service.set_running_instances_table("device"+str(device_names),rcvmsg,rcvmsg.get_position(),ip,[])
			devices.append("device"+str(device_names))
			device_names+=1
			
			sensors=["camera"]
			rcvmsg=device_HW_characteristics(platform.processor(),psutil.cpu_count(logical=True),cpufreq.current,8000000000,8000000000,sensors,"cloud")
			'''
			
			#LARGE GRAPH ONLY
			#for i in range(0,998):
			#	current_service.set_running_instances_table("device"+str(device_names),rcvmsg,rcvmsg.get_position(),ip,[])
			#	devices.append("device"+str(device_names))
			#	device_names+=1
		
			#END TEMPORARY *************************************************************
				
			
			'''
			#Set the current service's running_instances_table
			for i in range(0,len(cluster_nodes)):
				
				#ping the agent located in each device of the cluster in order to receive HW characteristics
				ip=cluster_nodes[i][1]
				
				device_address = (ip,AGENT_PORT)
				print("Trying to ping ",device_address)
				sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
				sock.settimeout(5.0)
				rcvmsg=device_HW_characteristics()
				
				seq_num_mtx.acquire()
				sequence_number+=1
				sent_seq=sequence_number
				seq_num_mtx.release()
				ping_message=pickle.dumps(agent_message_class(LEADER_PING_TYPE,"",sent_seq))
				
				ack_received=0
				#Use at most once semantics
				for retransmissions in range(0,MAX_RETRANSMISSIONS):
					
					sock.sendto(ping_message,device_address)
					
					while(1):
						try:
							data, addr = sock.recvfrom(1024)
							rcvmsg=pickle.loads(data)
							
							if(rcvmsg.get_seq()==sent_seq):
								ack_received=1
								break
							else:
								continue
							
						except socket.timeout:
							print("Timeout")
							break
						
					if(ack_received==1):
						break
					
				if(ack_received==1):
					rcvmsg=pickle.loads(data)
					print("OK FROM AGENT")
					#If we have checked this device at least one time, simply update the HW characteristics of this device.
					if(cluster_nodes[i][0] in devices):
						current_service.update_running_instances_table(cluster_nodes[i][0],rcvmsg,rcvmsg.get_position(),ip,[])
					else:
						#This is the first time we check this device. Append it to the list, remove all existing labels (from a previous setup)
						devices.append(cluster_nodes[i][0])
						
						previous_step_available_devices+=1
						#Add a new row to the current service's "running_instances_table"
						current_service.set_running_instances_table(cluster_nodes[i][0],rcvmsg,rcvmsg.get_position(),ip,[])
			'''
			
			current_service.print_running_instances_table()
			
			#This is the first time we refer to that service. Initialize the component_replicas_table
			if(len(current_service.get_component_replicas_table())==0):
				for j in range(0,len(components)):
					
					current_service.set_check_table(components[j],0)
					compatible_devices=[]
					
					#Find compatible devices for this component
					running_instances_table=current_service.get_running_instances_table()
					#A device is compatible with this component if the position of the device is same with the position of the component (specified in the configuration file)
					for i in range(0,len(running_instances_table)):
						if(running_instances_table[i][2] in current_service.get_component(components[j]).get_position().split("/") and current_service.get_component(components[j]).get_ram()<=running_instances_table[i][1].get_available_ram() and running_instances_table[i][1].get_processor() in current_service.get_component(components[j]).get_processor().split("/")):
							
							attached_sensors=0
							if(len(current_service.get_component(components[j]).get_sensors())>0):
								sensors_list=current_service.get_component(components[j]).get_sensors().split("/")
								
								#print("sensors list=",sensors_list)
								#print("device sensors list=",running_instances_table[i][1].get_sensors())

								for k in range(0,len(sensors_list)):
									if(sensors_list[k] in running_instances_table[i][1].get_sensors()):
										attached_sensors+=1
							
								if(len(sensors_list)==attached_sensors):
									compatible_devices.append(running_instances_table[i][0])
							else:
								compatible_devices.append(running_instances_table[i][0])
					
					#Select a port for this component
					PORT_ASSIGNMENT+=1
					current_service.set_component_replicas_table(components[j],-1,int(PORT_ASSIGNMENT)-1,0,compatible_devices)
					
				current_service.print_component_replicas_table()
			else:
				#component_replicas_table table is already set, update it. The compatible_devices may have been changed.
				for j in range(0,len(components)):
					
					compatible_devices=[]
					#Find compatible devices
					running_instances_table=current_service.get_running_instances_table()
					for i in range(0,len(running_instances_table)):
						
						if(running_instances_table[i][2] in current_service.get_component(components[j]).get_position().split("/") and current_service.get_component(components[j]).get_ram()<=running_instances_table[i][1].get_available_ram() and running_instances_table[i][1].get_processor() in current_service.get_component(components[j]).get_processor().split("/")):
							
							attached_sensors=0
							if(len(current_service.get_component(components[j]).get_sensors())>0):
								sensors_list=current_service.get_component(components[j]).get_sensors().split("/")

								for k in range(0,len(sensors_list)):
									if(sensors_list[k] in running_instances_table[i][1].get_sensors()):
										attached_sensors+=1
							
								if(len(sensors_list)==attached_sensors):
									compatible_devices.append(running_instances_table[i][0])
							else:
								compatible_devices.append(running_instances_table[i][0])
					
					current_service.update_component_replicas_table(components[j],compatible_devices)
					
				current_service.print_component_replicas_table()
			
			current_replicas=current_service.get_current_replicas_column()
			mandatory_replicas_met=calculate_current_replicas()
			
			if(mandatory_replicas_met==-1): 
				print(F_Red,"Can not deploy this service...",Reset,sep='')
			
			elif(mandatory_replicas_met==1): 
				#If we can not meet the mandatory_replicas criteria, do not call the placement algorithm.
				new_replicas=current_service.get_current_replicas_column()
			
				#Call the placement_algorithm only if at least once component has more computed replicas than the existing running replicas (if diff>0)
				for i in range(0,len(current_replicas)):
					if(int(current_replicas[i])<int(new_replicas[i])):
						current_service.reset_check_table()
						placement_algorithm()
						break
		
			placement_mtx.release()
		time.sleep(SLEEP_TIME)

if __name__=="__main__":
	
	if(len(sys.argv)<2):
		print("Wrong number of arguments. Please give the configuration file's name as a first argument")
		exit()
		
	main(sys.argv[1])
