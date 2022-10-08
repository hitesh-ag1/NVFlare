# Socket Programming in Python (Guide)

# Usage Pattern One: 
 FLARE SERVER as Lib, FLARE Client is locally simulated.
 This can be used in interactive Python, Python Notebooks

```mermaid
flowchart LR
    FS[[FALRE_Server main workflow]]--> |local| FC1[FLARE_Client]
    FS --> |local | FC2[FLARE_Client]
    FS --> |local | FC3[FLARE_Client]
         
```
# Usage Pattern Two: 
 FLARE SERVER as Lib, This can be used in interactive Python, Python Notebooks
 FLARE Client will run in remote FLARE Client Service. 
 Tasks
 * Simple FLARE Server Lib with GRPC communication 
 * Key communication points: broadcast (grpc interactions)
 * Main Program is Controller Workflow code
 * broadcast will 
   * serialize sharable, meta info and client code into exec_unit_package  
   * send exec_unit_package to remote client-service, then trigger client run
 * listen to registered event for reply
   * handle reply
   * **Note**  This is like Apache Spark Master vs. Executors
   * The issue with this deploy pattern is The User interaction piece is tie to direct to FLARE Server Implementation
   
Cons: 
   Heavy Client (similar to Apache Spark Driver)
   User experience is strong coupled with each server logics


```mermaid
flowchart LR
    FS[[FALRE_Server main workflow]] --> |remote grpc| FCS1[FLARE_Client in remote Client Service] 
    FS  --> |remote grpc| FCS2[FLARE_Client in remote Client Service] 
    FS  --> |remote grpc| FCS3[FLARE_Client in remote Client Service] 
     
```

# Deploy Pattern Three: 
 FLARE SERVER as Service 
 FLARE Client as Service 
 User interact with Flare Connect API 
 * Similar to current NVFLARE but different
 * Admin API is replaced with Connect API
 * Similar to Apache Spark Connect API patterns
 * Separate Flare Controller changes from the FLARE Connect APIs


```mermaid
flowchart LR
    subgraph FLARE system
    A[[GRPC Service]]--> |interactive communication| FS[FLARE Server in remote Server Service]
  
    FS--> FC1[FLARE_Client in remote Client Service]  
    FS--> FC2[FLARE_Client in remote Client Service]  
    FS--> FC3[FLARE_Client in remote Client Service]  
    end
    
    subgraph Notebook 
       User --> main.py["controller + Executor codes in main.py"]
       main.py --> |broadcast_and_wait| connector[ Connector API ]
       connector --> |code checksum, code serialization| A
       A  ==> |GRPC Streaming Service| connector 
    end                                                                                   

```
### Setup()
```mermaid

sequenceDiagram
    autonumber
    train.py->>Connector: setup(): send setup task to GRPC service
    activate train.py
    Connector ->> GPRC_SERVICE: gprc 
    GPRC_SERVICE  ->> Server_Service: setup coordinator
    Server_Service ->> Client_Service : setup Client's Executor for the job
    Client_Service ->> Client_Executor : prepare Client Executor for the job
    Client_Executor ->> Learner : prepare user facing learner
    
    Learner ->> Client_Executor : ok
    Client_Executor ->> Client_Service : ok
    Client_Service ->> Server_Service : ok
    Server_Service ->> GPRC_SERVICE : ok
    GPRC_SERVICE ->> Connector : ok
    Connector ->> train.py : ok
    deactivate train.py
     

```

### broadcast_and_wait()

```mermaid

sequenceDiagram
    autonumber
   
    train.py ->> Connector: broadcast_and_wait()
    activate train.py 
    Connector ->> GPRC_SERVICE: gprc 
    GPRC_SERVICE  ->> Server_Service: load Coordinator based on the coordinate Id
    Server_Service  ->> Coordinator: : prepare Task, call broadcast_and_way, broad cast to clients
    Coordinator ->> Client_Service : load job executor, and call execute() on Client Executor
    Client_Service ->> Client_Executor : load learner, learner.train method 
    Client_Executor ->> Learner : train()
    
    Learner ->> Client_Executor :  result 
    Client_Executor ->> Client_Service :  result
    Client_Service ->> Coordinator: reeult
    Coordinator ->> Server_Service :  result
    Server_Service ->> GPRC_SERVICE :  result
    GPRC_SERVICE ->> Connector :  result
    Connector ->> train.py :  result
    deactivate train.py
     
      

```

# Usage Pattern Four:
FLARE SERVER as Service
FLARE Client as Service
Sub are submitted via Flare CLI submit_job
Different from today:
* Server Workflow Controller Configuration is defined via python
* Client Executor Configuration is defined via python
* This almost identify to FLARE current deployment pattern.
* Where CLI part is Admin Console

```mermaid
flowchart LR
    CLI[[FALRE CLI]] --> |submit_job| FS[FLARE Server in remote Server Service]
    FS--> FC1[FLARE_Client in remote Client Service]  
    FS--> FC2[FLARE_Client in remote Client Service]  
    FS--> FC3[FLARE_Client in remote Client Service]  
```
