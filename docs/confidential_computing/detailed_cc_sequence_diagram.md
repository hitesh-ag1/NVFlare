
# FLARE, CC SDK, Attestation Service Interaction

## Preparation

### Preparation Actions: Client register policy

```mermaid
sequenceDiagram
   autonumber
    participant FLClient_1
    participant FLClient_2
    participant CC_SDK
    participant Attestation_Service

    FLClient_1 -->> FLClient_1: trigger events ( system start etc.)
    FLClient_1 -->> CC_SDK: register Policy (provide client 1 Id) 
    CC_SDK -->> CC_SDK: create or load policy for client 1  ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> FLClient_1: policy registration result for client 1
    FLClient_1 -->> FLClient_1: determine to stop or continue 

    FLClient_2 -->> FLClient_2: trigger events ( system start etc.)
    FLClient_2 -->> CC_SDK: register Policy (provide client 2 Id)
    CC_SDK -->> CC_SDK: create or load policy for client 2  ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> FLClient_2: policy registration result for client 2
    FLClient_2 -->> FLClient_1: determine to stop or continue 
```

### Preparation Actions: Client register policy

```mermaid
sequenceDiagram
   autonumber
    participant FLServer
    participant CC_SDK
    participant Attestation_Service

    FLServer -->> FLServer: trigger events ( system start etc.)
    FLServer -->> CC_SDK: register Policy (provide client 1 Id) 
    CC_SDK -->> CC_SDK: create or load policy for client 1  ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> FLServer: policy registration result for client 1
    FLServer -->> FLServer: determine to stop or continue 
 
```


### Preparation Actions: Cross Clients policy validation -- required (?)

```mermaid
sequenceDiagram
   autonumber
    participant FLClient_1
    participant FLClient_2
    participant FLServer
    participant CC_SDK
    participant Attestation_Service
 
    FLClient_1 -->> FLServer: register client 1 at FL Server
    FLClient_2 -->> FLServer: register client 2 at FL Server
    FLServer -->> CC_SDK : cross clients policy validation (not sure this is required) 
    CC_SDK -->> Attestation_Service : cross clients policy validation with client_policy_ids 
 
    Attestation_Service -->> CC_SDK : cross clients policy validation results 
    CC_SDK -->> FLServer : cross clients policy validation results
    FLServer -->> FLServer: determine to stop or continue
   
```

## Local Attestation


### Preparation Actions: FL Clients and FL Server -- orchestration

```mermaid
sequenceDiagram
   autonumber
    participant FLClient_1
    participant FLClient_2
    participant FLServer
 
    FLClient_1 -->> FLServer: registration client 1 with server
    Note left of FLServer: a nonce is an arbitrary number that can be used just once in a cryptographic communication. 
    FLServer -->> FLClient_1 : nonce
    FLClient_2 -->> FLServer: registration client 2 with server
    FLServer -->> FLClient_2 : nonce

   
```
