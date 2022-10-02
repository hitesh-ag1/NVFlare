# NVFLARE CLIENT SERVER STATE

## FL Server

### FL Server Start State

```mermaid
stateDiagram-v2
    FL_Server: FL Server
    server_train: launch scripts
    [*] --> server_train
    note right of server_train
        load fed_server_config.json
    end note
    server_train --> server_deployer
  
                  
    state FL_Server {
        server_train --> Admin_Server
        Admin_Server --> Start
        note right of Admin_Server
           ServerEngine is associated with admin_server
        end note
        
        server_deployer --> FedServer : create_fl_server    
        server_deployer --> JobRunner
        server_deployer --> RunManager
        server_deployer --> Workspace
        note right of Workspace
            workspace is used by RunManager
        end note
        state FedServer_Runtime_stack {
            note left of FedServer
                heart_beat_timeout = 600
            end note
            RunManager
            Workspace
            Admin_Server
            
            FedServer --> ServerEngine:_create_server_engine
            FedServer --> grpc_server: deploy
            FedServer --> overseer_agent: deploy
            note left of ServerEngine
                   ServerEngine set parameters (run_manager, job_runner, job_manager)
            end note
            ServerEngine --> JobRunner:setter
            JobRunner --> Start: job_runner_thread
            overseer_agent --> Start
            grpc_server --> Start
        }
   
       
    }
```

### FL Server Stop State

```mermaid
stateDiagram-v2
    FL_Server: FL Server
    [Started] --> FL_Server: stop_fl.sh
    Admin_Console --> Admin_Server: shutdown
    state join_state <<join>>
    state FL_Server {
        Admin_Server --> join_state: stop
        Admin_Server --> ServerEngine: close
        
        grpc_server --> join_state 
        fed_server --> ServerEngine:shutdown_server
        fed_server --> grpc_server:close
        ServerEngine --> join_state 
    
       
    }
    join_state --> [*]
```
## FL CLIENT 

### FL Client Start 

```mermaid
stateDiagram-v2
    FL_Client: FL Client
    Client_train: client_train.py ( client launch scripts )
    [*] --> Client_train: start.sh
    note left of Client_train
        FLClientStarterConfiger.config()
    end note
    Client_train --> deployer: deployer = conf.base_deployer
    Client_train --> Admin_agent: create_admin_agent()
    Client_train --> Client_Engine: create_admin_agent()
    Fed_Client --> FL_Sever: register
     
    state FL_Client {
            deployer --> Fed_Client: create_fed_client
            state Fed_Clent_Runtime_Stack { 
                Fed_Client --> Communicator
                Fed_Client --> Overseer_agent
                Client_Engine --> Fed_Client: Fed Client is attribute
                Client_Engine --> Admin_agent: Admin_Agent is attribute
                
                note left of Fed_Client
                    start heart beat
                end note
                Overseer_agent --> Start
                Admin_agent --> Start
        }
    }
```



### FL Client Stop

Todo


## FL Server: Server Start

```mermaid
sequenceDiagram
    participant server_train.py
    participant FLServerStarterConfiger
    participant ServerDeployer
    participant Workspace
    participant FedAdminServer
    
    server_train.py ->> Workspace: create server workspace
    server_train.py ->> FLServerStarterConfiger: configure()
    server_train.py ->> ServerDeployer: deployer = conf.deployer
    note over ServerDeployer : ServerCommandModules is registed 
    ServerDeployer ->>  ServerDeployer: fed_server = deployer.deploy(args)
    server_train.py ->> server_train.py: FedAdminServer = create_admin_server(fed_server, ...)
    server_train.py --> FedAdminServer: FedAdminServer.start()
```

## FL Server: ServerDeployer.deploy()

```mermaid
sequenceDiagram
    participant ServerDeployer
    participant FederatedServer
    participant GRPC_Server
    participant cleanup_thread
    participant JobRunner
    participant Thread
 
    ServerDeployer ->>  ServerDeployer: FederatedServer = create_fl_server(args)
    ServerDeployer ->>  FederatedServer: FederatedServer.deploy()
    FederatedServer ->> GRPC_Server: create grpc server if not exists: grpc.server.start()
    FederatedServer ->> cleanup_thread: cleanup_thread.start
    ServerDeployer ->> JobRunner: create Job Runner
    ServerDeployer ->> Workspace: create workspace 
    ServerDeployer ->> RunManager: create run_manager
    ServerDeployer ->> job_manager: get job_manager
    ServerDeployer ->> FederatedServer: set run_manager, job_manager
    ServerDeployer ->> RunManager: set JobRunner
    ServerDeployer ->> Thread: JobRunner.start()
     
```


# JOB Workflow

## Submit Job: Admin Client

```mermaid
sequenceDiagram
    participant AdminClient(cmd.CMD)
    participant AdminAPI 
    participant FileTransferModule
    Note over FileTransferModule: CommandModules were pre-registed, each CommandModule has a command name map to a handler function. FileTransferModule is one of CommandModule   
   
    participant Socket 
    
    aAdminClient(cmd.CMD)->> AdminClient(cmd.CMD) : do_default(line) (in nvflare.fuel.hci.client.cli.py)
    AdminClient(cmd.CMD)->> AdminAPI : resp = api.do_command(line)
    alt cmd type is client
        AdminAPI ->> AdminAPI: _do_client_command
        AdminAPI ->> FileTransferModule: handler(args, ctx): submit_job's handler is FileTransferModule.upload_folder()
        FileTransferModule ->> FileTransferModule: upload_folder(), extrat command, zip job folder and base64 encode
        FileTransferModule ->> AdminAPI: server_execute(command)
        AdminAPI ->> Socket: _send_to_sock
        Socket -->> FileTransferModule: result
        FileTransferModule -->> AdminAPI: result
        
    else
        AdminAPI ->> AdminAPI: server_execute
        note over AdminAPI, Socket : steps omitted 
        AdminAPI ->> Socket: _send_to_sock
    end
```

## Submit Job: Server Side

```mermaid
sequenceDiagram
    participant FedAdminServer
    note over FedAdminServer:  subclass of AdminServer and AdminServer(socketserver.ThreadingTCPServer):
    participant _MsgHandler
    note over _MsgHandler:  _MsgHandler(socketserver.BaseRequestHandler) in fuel.hci.seer.hci.py handles Socket message
    participant ServerCommandRegister
    participant JobCommandModule
    participant Connection
    participant ServerEngine
    participant SimpleJobDefManager
    participant FilesystemStorage
    
    
    FedAdminServer ->> ServerCommandRegister: _do_command()  
    ServerCommandRegister ->> ServerCommandRegister: JobCommandModule.handler(handler(conn, args)
    ServerCommandRegister ->> JobCommandModule: submit_job(): unzip folder, 
    JobCommandModule ->> Connection :  engine = conn.app_ctx
    JobCommandModule ->> ServerEngine: job_def_manager = engine.job_def_manager
    JobCommandModule ->> SimpleJobDefManager: meta = job_def_manager.create(meta, data_bytes, fl_ctx)
    SimpleJobDefManager ->>  SimpleJobDefManager : store = get_job_store(fl_ctx):
    SimpleJobDefManager ->> FilesystemStorage :  create_object( job_data)
     
```
## Dispatch Job: JobRunner.run()
 * check, schedule and run jobs

```mermaid
sequenceDiagram
    participant JobRunner
    participant Engine
    participant Thread
    participant DefaultJobScheduler
    participant FedAdminServer
    participant ServerEngine
    
    loop over not ask_to_stop
        JobRunner ->> JobRunner : run
        JobRunner ->> Thread : start()
        JobRunner ->> Engine : getComponent(JOB_MANAGER)
        JobRunner ->> SimpleJobDefManager: job_manager.get_jobs_by_status(RunStatus.SUBMITTED, fl_ctx)
        SimpleJobDefManager ->> SimpleJobDefManager: _scan(filter, job_store)
        SimpleJobDefManager -->> JobRunner: approved_jobs
        JobRunner ->> DefaultJobScheduler: schedule_job(approved_jobs)
        loop over job_candidates
            DefaultJobScheduler ->> DefaultJobScheduler: _try_job(job, fl_ctx): map sites to app; 
        end
        loop over available_sites
            DefaultJobScheduler ->> DefaultJobScheduler: _check_client_resources(resource_reqs, fl_ctx)
        end 
        
        JobRunner ->> JobRunner: _deploy_job(ready_job, sites, fl_ctx)
        loop over app and sites: 
            JobRunner ->> AppDeployer: deploy to server if site is server 
            JobRunner ->> JobRunner: prepare client_deploy_requests
        end
        JobRunner ->> FedAdminServer: send_requests_and_get_reply_dict(client_deploy_requests)

        loop over client_deploy_requests: 
            JobRunner ->> JobRunner : check reply message
        end
        
        JobRunner ->> JobRunner: _start_run(job_id,ready_job,deployable_clients,fl_ctx)
        JobRunner ->> ServerEngine : start_app_on_server()
        JobRunner ->> JobRunner:  time.sleep(1.0)
    end
    
    
```

## FL Server: Federated Server Process

```mermaid
sequenceDiagram
    participant Fed_Server
    participant Workspace
    participant RunManager
    participant ServerEngine 
    participant ServerRunner 
     
    Fed_Server->> Workspace: create server workspace
    Fed_Server->> RunManager: create & Set runner manager, and set event handler,set server_runner 
    Fed_Server->> ServerEngine: set runner manager, set FLContext
    Fed_Server->> ServerRunner: set server engine and server configuration
    ServerEngine ->> Child_Process : start_app_on_server() -> ... -> Popen("runner_process")
     
```

## FL Server: Job Child Process


```mermaid
sequenceDiagram
    participant ServerEngine 
    ServerEngine ->> Child_Process : start_app_on_server() -> ... -> Popen("runner_process")

    participant Child_Process
    participant Job_Fed_Server
    participant Job_ServerEngine 
    participant ServerCommandAgent
    participant ServerAppRunner
    participant Job_Workspace
    participant Job_RunManager
    participant Job_ServerRunner 
    participant Workflow 
    
    Child_Process ->> Job_Fed_Server: deployer.create_fl_server()
    Job_Fed_Server->> Job_ServerEngine: set runner manager, set FLContext
    Child_Process ->> ServerCommandAgent: Listen to engine exe command
    Child_Process ->> ServerAppRunner: start_server_app() -> set_up_run_config
    ServerAppRunner ->> Job_Fed_Server: start_run()
    
    Job_Fed_Server->> Job_Workspace: create server workspace
    Job_Fed_Server->> Job_RunManager: create & Set runner manager, and set event handler,set server_runner 
    
    Job_Fed_Server->> Job_ServerRunner: run() 
    loop over workflows
       Job_ServerRunner->>Workflow: initialize_run
       Job_ServerRunner->>Workflow: control_flow
       Job_ServerRunner->>Workflow: finalize_run
    end
    
```
## FL Client Job Process

```mermaid
sequenceDiagram
    participant StartJobProcessor 
    participant ClientEngine 
    participant ProcessExecutor   
    participant Client_worker_process   
    
    StartJobProcessor ->>ClientEngine: process() -> engine.start_app()
    ClientEngine ->> ProcessExecutor:start_app()
    ProcessExecutor ->> Client_worker_process: Popen( python -m worker_process) : workspace, startup, token, ssid, job_id,client_name, port, target server, client config      
```

## FL Client Job Worker Process

```mermaid
sequenceDiagram
    participant Client_worker_process   
    participant Thread
    participant FLClientStarterConfiger
    participant Deployer
    participant FederatedClient
    participant ClientAppRunner
    participant ClientRunner

    Client_worker_process ->> Thread: check_parent_alive
    Client_worker_process ->>FLClientStarterConfiger:config()
    FLClientStarterConfiger ->>Deployer: conf.base_deployer()
    Deployer ->> FederatedClient: deployer.create_fed_client()
    Client_worker_process ->> ClientAppRunner: start_run(app_root, args, config_folder, federated_client, secure_train)
    ClientAppRunner ->> ClientRunner: create_client_runner()
    ClientRunner ->>ClientRunner: create_client_runner(): configuration,workspace, privacy_manager, ClientRunManager, create new fl_ctx,  configuration,workspace, privacy_manager, create ClientRunManager, create new fl_ctx, CommandAgent.start()
    ClientRunner  ->> ClientRunner: ClientRunner.run(app_root, args)
```

## ClientRuner.run()

```mermaid
sequenceDiagram
    participant ClientRunner
        ClientRunner  ->> ClientRunner: init_run(app_root, args)
        loop over ClientRunner (while not ask to stop)
            ClientRunner  ->> ClientRunner: init_run(app_root, args)
            ClientRunner  ->> ClientEngine: new fl_ctx
            ClientRunner  ->> ClientRunner: task_fetch_interval= fetch_and_run_one_task(fl_ctx)
            note right of ClientRunner: task_fetch_interval is default to 0.1 seconds (version 2.2) and 5 seconds (version 2.1)
            note right of ClientRunner: user can configure task_fetch_interval via controller in version 2.2
            ClientRunner  ->> ClientRunner: time.sleep(task_fetch_interval) 
        end
   
```
## ClientRunner.fetch_and_run_one_task()

```mermaid
sequenceDiagram
    participant ClientRunner
    participant ClientEngine
    participant ClientRunManager
    participant FederatedClient
    participant Communicator
    participant Server
 
                ClientRunner  ->> ClientRunManager:get_task_assignment(fl_ctx)
                ClientRunManager  ->> FederatedClient:FederatedClient.fetch_task() -> pull_task() -> fetch_execute_task()
                FederatedClient  ->> Communicator:getTask()
                Communicator ->> Server : getTask() over grpc
                Server -->> ClientRunner: Task
                ClientRunner ->> ClientRunner: reply = _process_task(Task)
                ClientRunner ->> ClientRunManager: send_task_result
                ClientRunManager ->> FederatedClient: push_results
                FederatedClient ->> Communicator: submitUpdate
                Communicator -) Server: grpc 
  
```

## ClientRunner._process_task()

```mermaid
sequenceDiagram
    participant ClientRunner
    participant Task_Data_Filters
    participant Executor
    participant Task_Result_Filters
  
    ClientRunner ->> ClientRunner: executor = self.task_table.get(task.name)
    loop over Task_Data_Filters 
            ClientRunner ->> Task_Data_Filters: process(data)
    end
    ClientRunner ->> Executor: executor.execute(task.name, task.data, fl_ctx, self.task_abort_signal)
    Executor ->> ClientRunner: reply 
    loop over Task_Result_Filters 
        ClientRunner ->> Task_Result_Filters: process(reply)
    end
     
  
```
