
# FLARE, CC SDK, Attestation Service Interaction

## Preparation
* Question
    * do we need to register two type of policies:
        1) what policy that this device will accept ? 
        2) what policy ( claim(?) ) that this device has ?
      
### Preparation Actions: Client register policy



```mermaid
sequenceDiagram
   autonumber
    participant FLClient_1
    participant FLClient_2
    participant CC_SDK
    participant Attestation_Service

    FLClient_1 -->> FLClient_1: trigger events ( system start etc.)
    Note over FLClient_1, CC_SDK: register Client 1 policy 
    FLClient_1 -->> CC_SDK: register Policy (provide client 1 Id) 
    CC_SDK -->> CC_SDK: create or load policy for client 1  ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> FLClient_1: policy registration result for client 1
    

    FLClient_2 -->> FLClient_2: trigger events ( system start etc.)
    Note over FLClient_1, CC_SDK: register Client 2 policy
    FLClient_2 -->> CC_SDK: register Policy (provide client 2 Id)
    CC_SDK -->> CC_SDK: create or load policy for client 2  ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> FLClient_2: policy registration result for client 2
     
```

### Preparation Actions: FL Server register policy

```mermaid
sequenceDiagram
   autonumber
    participant FLServer
    participant CC_SDK
    participant Attestation_Service

    FLServer -->> FLServer: trigger events ( system start etc.)
    Note over FLServer, CC_SDK: register FL Server policy
    FLServer -->> CC_SDK: register Policy (provide FL Server Id) 
    CC_SDK -->> CC_SDK: create or load policy for FL Server ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> FLServer: policy registration result for FL Server
 
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

### Local Attestation: register devices (FL Clients and FL Server)
```mermaid
sequenceDiagram
   autonumber
    participant FLClient_1
    participant FLClient_2
    participant FLServer
    participant CC_SDK
 
    FLClient_1 -->> FLServer: registration client 1 with FL server
    Note left of FLServer: a nonce is an arbitrary number that can be used just once in a cryptographic communication.
    FLServer -->> CC_SDK : createNonce() 
    CC_SDK -->> FLServer : nonce
    FLServer -->> FLClient_1 : nonce
    
    FLClient_2 -->> FLServer: registration client 2 with FL server
    FLServer -->> CC_SDK : createNonce() 
    CC_SDK -->> FLServer : nonce
    FLServer -->> FLClient_2 : nonce
    
    Note left of FLServer: create Nonce for FLServer itself
    FLServer -->> CC_SDK : createNonce() for FLServer 
    CC_SDK -->> FLServer : nonce
       
```

### Local Attestation: verify evidence

```mermaid
sequenceDiagram
   autonumber
    participant FLClient_1
    participant FLClient_2
    participant CC_SDK
    participant vTMP
    participant Attestation_Service
    participant FLServer
    
    Note over FLClient_2, CC_SDK : verify FLClient_1
    
    FLClient_1 --> CC_SDK : verify_evidence(client_1_nonce)
    CC_SDK -->> vTMP : generate_evidence(client_1_nonce)
    vTMP -->> CC_SDK : evidence + nonce 
    CC_SDK -->> Attestation_Service: verify_evidence(evidence + Nonce)
    Attestation_Service -->> Attestation_Service: verify against policy
    Attestation_Service -->> CC_SDK: token
    CC_SDK -->> FLClient_1 : token
    FLClient_1 -->> FLServer : token

    Note over FLClient_2, CC_SDK : verify FLClient_2

    FLClient_2 --> CC_SDK : verify_evidence(client_2_nonce)
    CC_SDK -->> vTMP : generate_evidence(client_2_nonce)
    vTMP -->> CC_SDK : evidence + nonce 
    CC_SDK -->> Attestation_Service: verify_evidence(evidence + Nonce)
    Attestation_Service -->> Attestation_Service: verify against policy
    Attestation_Service -->> CC_SDK: token
    CC_SDK -->> FLClient_2 : token
    FLClient_2 -->> FLServer : token
    
    Note over FLServer, CC_SDK : verify FL Server
    
    FLServer --> CC_SDK : verify_evidence(FLServer_Nonce)
    CC_SDK -->> vTMP : generate_evidence(FLServer_Nonce)
    vTMP -->> CC_SDK : evidence + nonce 
    CC_SDK -->> Attestation_Service: verify_evidence(evidence + Nonce)
    Attestation_Service -->> Attestation_Service: verify against policy
    Attestation_Service -->> CC_SDK: token
    CC_SDK -->> FLServer : token
    
    FLServer --> FLServer : Orchestrator: make decision 
   
```

## Policy Enforcement

### TODO
