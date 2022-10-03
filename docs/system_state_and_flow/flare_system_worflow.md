# NVFLARE CLIENT SERVER STATE

## FL Server

### FL Server Start State
![diagram](./flare_system_worflow-1.svg)
### FL Server Stop State
![diagram](./flare_system_worflow-2.svg)
## FL CLIENT 

### FL Client Start 
![diagram](./flare_system_worflow-3.svg)
### FL Client Stop

Todo


## FL Server: Server Start
![diagram](./flare_system_worflow-4.svg)
## FL Server: ServerDeployer.deploy()
![diagram](./flare_system_worflow-5.svg)
# JOB Workflow

## Submit Job: Admin Client
![diagram](./flare_system_worflow-6.svg)
## Submit Job: Server Side
![diagram](./flare_system_worflow-7.svg)
## Dispatch Job: JobRunner.run()
 * check, schedule and run jobs
![diagram](./flare_system_worflow-8.svg)
# Run Job: JobRunner._start_run()
* run job
![diagram](./flare_system_worflow-9.svg)
## FL Server: Federated Server Process
![diagram](./flare_system_worflow-10.svg)
## FL Server: Job Child Process
![diagram](./flare_system_worflow-11.svg)
## FL Client Job Process
![diagram](./flare_system_worflow-12.svg)
## FL Client Job Worker Process
![diagram](./flare_system_worflow-13.svg)
## ClientRuner.run()
![diagram](./flare_system_worflow-14.svg)
## ClientRunner.fetch_and_run_one_task()
![diagram](./flare_system_worflow-15.svg)
## ClientRunner._process_task()
![diagram](./flare_system_worflow-16.svg)