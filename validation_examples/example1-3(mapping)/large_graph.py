


def main():
	
	f = open("validation_config_large_graph.txt", "w")
	affinity=1000000
	number_of_components=5001
	singular=0
	
	f.write("----global configuration----\ncomponents: ")
	for i in range(1,number_of_components):
		if(i!=number_of_components-1):
			f.write("F"+str(i)+",")
		else:
			f.write("F"+str(i))
		 
	f.write("\nscale: as_many_as_possible\n\n")
	
	for i in range(1,number_of_components):
		if(singular==0):
			if(i==number_of_components-1):
				f.write(
				"component: F"+str(i)+"\n----general info----\nsource_files_directory: F"+str(i)+
				"\n\n----deployment info----\nposition: end/edge\nmandatory: yes\nsingular: no\n----constraints----\nram: 1\ncpu_cores: 2\nprocessor: aarch64/x86_64\n\n----networking----\nports_inside_container: 7000\nstatus: static\n\n----Links----\nend_component\n\n\n"
				)
			else:
			
				f.write(
					"component: F"+str(i)+"\n----general info----\nsource_files_directory: F"+str(i)+
					"\n\n----deployment info----\nposition: end/edge\nmandatory: yes\nsingular: no\n----constraints----\nram: 1\ncpu_cores: 2\nprocessor: aarch64/x86_64\n\n----networking----\nports_inside_container: 7000\nstatus: static\n\n----Links----\n"+"F"+str(i)+"->"+"F"+str(i+1)+","+str(affinity)+",unreliable\nend_component\n\n\n"
				)
		else:
			if(i==number_of_components-1):
				f.write(
				"component: F"+str(i)+"\n----general info----\nsource_files_directory: F"+str(i)+
				"\n\n----deployment info----\nposition: end/edge\nmandatory: yes\nsingular: no\n----constraints----\nram: 1\ncpu_cores: 2\nprocessor: aarch64/x86_64\n\n----networking----\nports_inside_container: 7000\nstatus: static\n\n----Links----\nend_component\n\n\n"
				)
			else:
			
				f.write(
					"component: F"+str(i)+"\n----general info----\nsource_files_directory: F"+str(i)+
					"\n\n----deployment info----\nposition: end/edge\nmandatory: yes\nsingular: no\n----constraints----\nram: 1\ncpu_cores: 2\nprocessor: aarch64/x86_64\n\n----networking----\nports_inside_container: 7000\nstatus: static\n\n----Links----\n"+"F"+str(i)+"->"+"F"+str(i+1)+","+str(affinity)+",unreliable\nend_component\n\n\n"
				)
				
		
		if(i%2==0):
			if(singular==0):
				singular=1
			else:
				singular=0
		affinity-=1
	f.close()
    

if __name__=="__main__":
	
	main()
