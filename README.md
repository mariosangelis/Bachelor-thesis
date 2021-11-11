This Thesis introduces a more flexible way to design and deploy such an application, by adopting a combination of component­based and data­flow­oriented programming. The application is described by a graph that consists of nodes, each one representing a compo­nent, and from unidirectional links used for data exchange between the components. We have simplified the graph representation process by enabling the developer to describe the compo­nents and their interconnections using a specially formatted configuration file. Furthermore, we have designed and implemented a cluster registration service for the dynamic control of a fleet consisting of heterogeneous devices positioned on the cloud­fog­edge system as well as a system responsible for deploying the component­based application based on user deployment preferences and requirements. We provide support for placement preferences, hardware and sensor requirements, link affinities, and other useful features for the desired deployment. At deployment time, the components are instantiated on the target hosts, along with automatically generated connector logic that takes care of component binding and com­munication over the network. We provide a network API that takes care of the connections’ establishment, termination, and control as well as the data transfer between the components, eliminating the complexity of each component’s interface programming process. Last but not least, we provide scaling and migration functionalities for improving performance and reducing the communication latency between components.
