#Angelis Marios
#Thesis title: Dynamic deployment of modular distributed stream processing applications
#This file contains the implementations of the main classes

import threading
from threading import *


class instance:
	def __init__(self,instance_name,device_name):
		self.instance_name=instance_name
		self.device_name=device_name
		self.available_ports=0
		self.dst_ip=[]
		self.dst_port=[]
		self.dst_component=[]
		self.flow_id=[]
		self.src_component=[]
		self.src_flow=[]
		self.changed_state=0
		self.poll_flag=0
	
	
	def set_poll_flag(self,val):
		self.poll_flag=val
		
	def get_poll_flag(self):
		return self.poll_flag
		
	def get_changed_state(self):
		return self.changed_state
	
	def set_changed_state(self,val):
		self.changed_state=val
		
	def get_flow_num(self):
		return self.flow_id
	
	def add_flow_num(self,flow_num):
		self.flow_id.append(flow_num)
	
	def get_device_name(self):
		return self.device_name
	
	
	def get_available_ports(self):
		return self.available_ports
	
	def set_available_ports(self,ports):
		self.available_ports=ports
	
	def decrease_available_ports(self):
		self.available_ports-=1
	
	def get_dst_ip(self):
		return self.dst_ip
	
	def add_dst_ip(self,ip):
		self.dst_ip.append(ip)
	
	def add_scr_component(self,component):
		self.src_component.append(component)
		
	def add_scr_flow(self,flow_num):
		self.src_flow.append(flow_num)
		
	def get_src_flows(self):
		return self.src_flow
		
	def add_dst_component(self,component):
		self.dst_component.append(component)
		
	def get_dst_components(self):
		return self.dst_component
	
	def get_src_components(self):
		return self.src_component
	
	def get_dst_port(self):
		return self.dst_port
	
	def add_dst_port(self,port):
		self.dst_port.append(port)
	
	def get_instance_name(self):
		return self.instance_name
	

class service:
	def __init__(self,total_components):
		self.total_components=total_components
		self.as_many_as_possible=0
		desired_scale_factor=0
		self.components_list=[]
		self.link_table=[]
		self.check_table=[]
		self.running_instances_table=[]
		self.component_replicas_table=[]
		
	def add_component(self,component):
		self.components_list.append(component)
		
	def get_components_list(self):
		return self.components_list
		
	def get_component(self,name):
		
		for i in range(0,len(self.components_list)):
			if(self.components_list[i].get_name()==name):
				return self.components_list[i]
			
	def get_as_many_as_possible_parameter(self):
		return self.as_many_as_possible
	
	def set_as_many_as_possible_parameter(self,as_many_as_possible):
		self.as_many_as_possible=as_many_as_possible
		
	def set_desired_scale_factor(self,scale_factor):
		self.desired_scale_factor=scale_factor
		
	def get_desired_state_factor(self):
		return self.desired_scale_factor
	
	def find_source_files_directory(self,component_name):
		for i in range(0,len(self.components_list)):
			if(self.components_list[i].get_name()==component_name):
				return self.components_list[i].get_source_files_directory()
			
	def find_image_name(self,component_name):
		for i in range(0,len(self.components_list)):
			if(self.components_list[i].get_name()==component_name):
				return self.components_list[i].get_image_name()
			
	def set_image_name(self,component_name,image_name):
		for i in range(0,len(self.components_list)):
			if(self.components_list[i].get_name()==component_name):
				return self.components_list[i].set_image_name(image_name)
	
	
	#-----------------------------------------------------------------------LINK TABLE [LINK,AFFINITY]-----------------------------------------------------------------------
	def set_link_table(self,link_name,affinity,reliability):
		self.link_table.append([link_name,affinity,reliability])
		
	def get_link_table(self):
		return self.link_table
	
	def print_link_table(self):
		
		print("--------------------------------------------------")
		line= '%11s %15s %12s' % ("LINK","AFFINITY","RELIABILITY")
		print(line)
		for i in range(0,len(self.link_table)):
			line= '%12s  %10s %15s' % (self.link_table[i][0],self.link_table[i][1],self.link_table[i][2])
			print(line)
			
		print("--------------------------------------------------")
			
	#-----------------------------------------------------------------------CHECK TABLE [COMPONENT,CHECK]-----------------------------------------------------------------------

	def set_check_table(self,component_name,check_value):
		self.check_table.append([component_name,check_value])
		
	def get_check_table(self):
		return self.check_table.copy()
	
	#Check if a component is checked
	def is_checked(self,component_name):
		for i in range(0,len(self.check_table)):
			if(self.check_table[i][0]==component_name):
				return(self.check_table[i][1])
		return -1
	
	#Set all entries to -1
	def reset_check_table(self):
		for i in range(0,len(self.check_table)):
			self.check_table[i][1]=0
	
	def set_checked(self,component_name):
		for i in range(0,len(self.check_table)):
			if(self.check_table[i][0]==component_name):
				self.check_table[i][1]=1
				break
			
	def print_check_table(self):
		
		print("--------------------------------------------------")
		line= '%11s  %12s  %12s' % ("COMPONENT","CHECK_VALUE")
		print(line)
		for i in range(0,len(self.check_table)):
			line= '%12s  %10s' % (self.check_table[i][0],self.check_table[i][1])
			print(line)
		print("--------------------------------------------------")
	
	#--------------------------------RUNNING INSTANCES TABLE [DEVICE_NAME,HW_SPECS,POSITION,IP,RUNNING_INSTANCES]--------------------------------
	
	#Create a new entry [DEVICE_NAME,HW_SPECS,POSITION,IP,RUNNING_INSTANCES]
	def set_running_instances_table(self,device_name,hw_specs,position,ip,running_instances):
		self.running_instances_table.append([device_name,hw_specs,position,ip,running_instances])
		
	#Update an existing entry
	def update_running_instances_table(self,device_name,hw_specs,position,ip,running_instances):
		for i in range(0,len(self.running_instances_table)):
			if(self.running_instances_table[i][0]==device_name):
				self.running_instances_table[i][1]=hw_specs
				break
			
			
	def component_exists_in_device(self,component_name,device_name):
		for i in range(0,len(self.running_instances_table)):
			if(device_name==self.running_instances_table[i][0]):
				for j in range(0,len(self.running_instances_table[i][4])):
					if(component_name==self.running_instances_table[i][4][j].get_instance_name()):
						return(1)
					
		return(0)
			
	#Check if the device given as argument exists in the running instances table
	def device_exists(self,device_name):
		for i in range(0,len(self.running_instances_table)):
			if(self.running_instances_table[i][0]==device_name):
				return(1)
		return(0)
	
	#Return the ip address of a specific device
	def get_ip(self,device_name):
		for i in range(0,len(self.running_instances_table)):
			if(device_name==self.running_instances_table[i][0]):
				return self.running_instances_table[i][3]
			
			
	#Return the current running instances for a specific component
	def get_running_instances(self,component_name):
		instances_counter=0
		for i in range(0,len(self.running_instances_table)):
			for j in range(0,len(self.running_instances_table[i][4])):
				if(component_name==self.running_instances_table[i][4][j].get_instance_name()):
					instances_counter+=1
					break
		return instances_counter
	
	#Append a new instance in the running instances list of a specific device
	def add_running_instance(self,component_name,device_name):
		for i in range(0,len(self.running_instances_table)):
			if(device_name==self.running_instances_table[i][0]):
				new_instance=instance(component_name,device_name)
				self.running_instances_table[i][4].append(new_instance)
				
				return new_instance
			
	#Delete an instance of a devices's running instances list
	def delete_running_instance(self,component_name,device_name):
		for i in range(0,len(self.running_instances_table)):
			if(device_name==self.running_instances_table[i][0]):
				for j in range(0,len(self.running_instances_table[i][4])):
					if(component_name==self.running_instances_table[i][4][j].get_instance_name()):
						self.running_instances_table[i][4].remove(self.running_instances_table[i][4][j])
						return()
					
	#Return a running instance object
	def get_running_instance(self,component_name,device_name):
		for i in range(0,len(self.running_instances_table)):
			if(device_name==self.running_instances_table[i][0]):
				for j in range(0,len(self.running_instances_table[i][4])):
					if(component_name==self.running_instances_table[i][4][j].get_instance_name()):
						return(self.running_instances_table[i][4][j])
                    
	def delete_device(self,device_name):
		for i in range(0,len(self.running_instances_table)):
			if(device_name==self.running_instances_table[i][0]):
				self.running_instances_table.remove(self.running_instances_table[i])
				break
	
	#Get a copy of the running_instances_table. ATTENTION Use the copy constructor, otherwise a pointer to this list will be returned.
	def get_running_instances_table(self):
		return self.running_instances_table.copy()
	
	def get_original_running_instances_table(self):
		return self.running_instances_table
	
	def print_running_instances_table(self):
		
		print("-----------------------------------------------------------------------------------------------------------------------------------")
		line= '%19s  %12s  %11s %38s' % ("DEVICE NAME","POSITION","IP","RUNNING INSTANCES")
		print(line)
		for i in range(0,len(self.running_instances_table)):
				
			line= '%20s %10s %20s' % (self.running_instances_table[i][0],self.running_instances_table[i][2],self.running_instances_table[i][3])
			print(line,end='')
			print("            ",end='')
			for j in range(0,len(self.running_instances_table[i][4])):
				print(" "+self.running_instances_table[i][4][j].get_instance_name(),end='')
			print("")
			
		print("-----------------------------------------------------------------------------------------------------------------------------------")
		
		
	def print_HW(self):
		print("-----------------------------------------------------------------------------------------------------------------------------------")

		for i in range(0,len(self.running_instances_table)):
			print("device=",self.running_instances_table[i][0],"available ram=",self.running_instances_table[i][1].get_available_ram(),"available sensors=",self.running_instances_table[i][1].get_sensors())
		print("-----------------------------------------------------------------------------------------------------------------------------------")
		
	
	#-----------------------COMPONENT REPLICAS TABLE [COMPONENT,CURRENT_REPLICAS,PORT,INITIALIZED,COMPATIBLE_DEVICES]-------------------------
	
	def set_component_replicas_table(self,component_name,current_replicas,port,initialized,compatible_devices):
		self.component_replicas_table.append([component_name,current_replicas,port,initialized,compatible_devices])
	
	def get_component_replicas_table(self):
		return self.component_replicas_table.copy()
	
	#Add a new list which contains the compatible devices of a component to this component
	def update_component_replicas_table(self,component_name,compatible_devices):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				for j in range(0,len(compatible_devices)):
					if(compatible_devices[j] not in self.component_replicas_table[i][4]):
						self.component_replicas_table[i][4].append(compatible_devices[j])
				break
	
	def remove_missing_devices_from_component_replicas_table(self,component_name,missing_devices):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				
				for j in range(0,len(missing_devices)):
					
					if(missing_devices[j] in self.component_replicas_table[i][4]):
						self.component_replicas_table[i][4].remove(missing_devices[j])
						
				break
	
			
	#Check if a component exists in the component_replicas_table
	def component_exists(self,component_name):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				return(1)
		return(0)
	
	
	#Return a copy of the compatible devices list for a specific component. ATTENTION Use the copy constructor, otherwise a pointer to this list will be returned.
	def get_compatible_devices(self,component_name):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				return(self.component_replicas_table[i][4].copy())
			
	def get_compatible_devices_without_running_instances(self,component_name):
		
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				free_compatible_devices=self.component_replicas_table[i][4]
				
				for j in range(0,len(self.running_instances_table)):
					if(self.running_instances_table[j][0] in free_compatible_devices):
						for k in range(0,len(self.running_instances_table[j][4])):
							if(component_name==self.running_instances_table[j][4][k].get_instance_name()):
								#self.running_instances_table[j][4].remove(self.running_instances_table[j][4][k])
								
								free_compatible_devices.remove(self.running_instances_table[j][0])
								
								break
						
				break
				
				
		return(free_compatible_devices)
			
	#Return the current_replicas value for the component specified by the first argument
	def get_current_replicas(self,component_name):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				return(self.component_replicas_table[i][1])
			
	#Set the current replicas value for a specific component
	def set_current_replicas(self,component_name,current_replicas):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				self.component_replicas_table[i][1]=current_replicas
				break
			
			
	#Return the port value for the component specified by the first argument
	def get_component_port(self,component_name):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				return(self.component_replicas_table[i][2])
			
	#Set the initialize value for the component specified by the first argument to 1 
	def initialize_component(self,component_name):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				self.component_replicas_table[i][3]=1
				break
	
	def is_initialized(self,component_name):
		for i in range(0,len(self.component_replicas_table)):
			if(self.component_replicas_table[i][0]==component_name):
				return(self.component_replicas_table[i][3])
				
	#Return the current replicas column of the component_replicas_table
	def get_current_replicas_column(self):
		current_replicas=[]
		for i in range(0,len(self.component_replicas_table)):
			current_replicas.append(self.component_replicas_table[i][1])
			
		return current_replicas.copy()
	
	def print_component_replicas_table(self):
		
		print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------------")
		line= '%11s %18s %10s %50s' % ("COMPONENT","CURRENT REPLICAS","PORT","COMPATIBLE DEVICES")
		print(line)
		for i in range(0,len(self.component_replicas_table)):
			line= '%8s %15s %19s %80s' % (self.component_replicas_table[i][0],self.component_replicas_table[i][1],self.component_replicas_table[i][2],self.component_replicas_table[i][4])
			print(line)
			
		print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------------")
	
	#Print the status of each component of the service
	def print_status(self):
		
		for i in range(0,self.total_components):
			print("-------------- Component ",self.components_list[i].get_name()," --------------",sep='')
			self.components_list[i].print_status()
		
		
class component:
	def __init__(self,name):
		self.name=name
		self.source_files_directory=0
		self.position=0
		self.mandatory=0
		self.singular=0
		self.image_name=0
		self.ram=0
		self.cpu_cores=0
		self.ports_inside_container=0
		self.status=0
		self.processor=0
		self.sensors=[]
		
	def set_name(self,name):
		self.name=name
		
	def get_name(self):
		return self.name
		
	def set_source_files_directory(self,source_files_directory):
		self.source_files_directory=source_files_directory
		
	def set_processor(self,processor):
		self.processor=processor
		
	def get_processor(self):
		return(self.processor)
		
	def set_image_name(self,image_name):
		self.image_name=image_name
		
	def get_image_name(self):
		return(self.image_name)
		
	def get_source_files_directory(self):
		return(self.source_files_directory)
		
	def set_position(self,position):
		self.position=position
		
	def get_position(self):
		return self.position
	
	def set_mandatory(self,value):
		self.mandatory=value
		
	def is_mandatory(self):
		return(self.mandatory)
	
	def set_singular(self,value):
		self.singular=value
		
	def is_singular(self):
		return(self.singular)
		
	def set_ram(self,ram):
		self.ram=int(ram)
		
	def get_ram(self):
		return self.ram
		
	def set_cpu_cores(self,cpu_cores):
		self.cpu_cores=cpu_cores
		
	def set_sensors(self,sensors):
		self.sensors=sensors
		
	def get_sensors(self):
		return self.sensors
		
	def set_ports_inside_container(self,ports_inside_container):
		self.ports_inside_container=ports_inside_container
		
	def set_status(self,status):
		self.status=status
		
	def print_status(self):
		print("name =",self.name)
		print("source_files_directory =",self.source_files_directory)
		print("desired_replicas =",self.desired_replicas)
		print("mandatory_replicas =",self.mandatory_replicas)
		print("position =",self.position)
		print("ratio =",self.ratio)
		print("ram =",self.ram)
		print("cpu_cores =",self.cpu_cores)
		print("ports_inside_container =",self.ports_inside_container)
		print("status =",self.status)
		

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
	

		
			
