
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
    participant Flare_Client_1
    participant Flare_Client_2
    participant CC_SDK
    participant Attestation_Service

    Flare_Client_1 -->> Flare_Client_1: trigger events ( system start, submit_job etc.)
    Note over Flare_Client_1, CC_SDK: register Client 1 policy 
    Flare_Client_1 -->> CC_SDK: register Policy (provide client 1 Id) 
    CC_SDK -->> CC_SDK: create or load policy for client 1  ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> Flare_Client_1: policy registration result for client 1
    

    Flare_Client_2 -->> Flare_Client_2: trigger events ( system start, Submit_job, etc.)
    Note over Flare_Client_1, CC_SDK: register Client 2 policy
    Flare_Client_2 -->> CC_SDK: register Policy (provide client 2 Id)
    CC_SDK -->> CC_SDK: create or load policy for client 2  ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> Flare_Client_2: policy registration result for client 2
     
```

### Preparation Actions: FL Server register policy

```mermaid
sequenceDiagram
   autonumber
    participant Flare_Server
    participant CC_SDK
    participant Attestation_Service

    Flare_Server -->> Flare_Server: trigger events ( system start, Submit_job etc.)
    Note over Flare_Server, CC_SDK: register FL Server policy
    Flare_Server -->> CC_SDK: register Policy (provide FL Server Id) 
    CC_SDK -->> CC_SDK: create or load policy for FL Server ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> Flare_Server: policy registration result for FL Server
 
```


### Preparation Actions: Cross Clients policy validation -- required (?)

```mermaid
sequenceDiagram
   autonumber
    participant Flare_Client_1
    participant Flare_Client_2
    participant Flare_Server
    participant CC_SDK
    participant Attestation_Service
 
    Flare_Client_1 -->> Flare_Server: register client 1 at FL Server
    Flare_Client_2 -->> Flare_Server: register client 2 at FL Server
    Flare_Server -->> CC_SDK : cross clients policy validation (not sure this is required) 
    CC_SDK -->> Attestation_Service : cross clients policy validation with client_policy_ids 
 
    Attestation_Service -->> CC_SDK : cross clients policy validation results 
    CC_SDK -->> Flare_Server : cross clients policy validation results
    Flare_Server -->> Flare_Server: determine to stop or continue
   
```

## Local Attestation

### Local Attestation: register devices (FL Clients and FL Server)
```mermaid
sequenceDiagram
   autonumber
    participant Flare_Client_1
    participant Flare_Client_2
    participant Flare_Server
    participant CC_SDK
 
    Flare_Client_1 -->> Flare_Server: registration client 1 with FL server
    Note left of Flare_Server: a nonce is an arbitrary number that can be used just once in a cryptographic communication.
    Flare_Server -->> CC_SDK : createNonce() 
    CC_SDK -->> Flare_Server : nonce
    Flare_Server -->> Flare_Client_1 : nonce
    
    Flare_Client_2 -->> Flare_Server: registration client 2 with FL server
    Flare_Server -->> CC_SDK : createNonce() 
    CC_SDK -->> Flare_Server : nonce
    Flare_Server -->> Flare_Client_2 : nonce
    
    Note left of Flare_Server: create Nonce for Flare_Server itself
    Flare_Server -->> CC_SDK : createNonce() for Flare_Server 
    CC_SDK -->> Flare_Server : nonce
       
```

### Local Attestation: verify evidence & policy enforcement

```mermaid
sequenceDiagram
   autonumber
    
    participant Flare_Job_Client
    participant Flare_Server
    participant Flare_Client_1
    participant Flare_Client_2
    participant CC_SDK
    participant vTMP
    participant Attestation_Service
    
    Flare_Job_Client -->> Flare_Server: request_job 
    
    activate Flare_Server

    Note over Flare_Server, CC_SDK: get evidence token
    Flare_Server --> CC_SDK : verify_evidence(Flare_Server_nonce)
    CC_SDK -->> vTMP : generate_evidence(Flare_Server_nonce)
    vTMP -->> CC_SDK : evidence + nonce 
    CC_SDK -->> Attestation_Service: verify_evidence(evidence + Nonce)
    Attestation_Service -->> Attestation_Service: verify against policy
    Attestation_Service -->> CC_SDK: token
    CC_SDK -->> Flare_Server : token
    deactivate Flare_Server
  
    activate Flare_Client_1
    Note over Flare_Server, Flare_Client_1: first verify the Flare_Server itself to Clients
    Flare_Server -->> Flare_Client_1:  Client pull from Server : get task + Flare_Server token 
    Flare_Client_1 -->> CC_SDK: authenticate token
    CC_SDK -->> Attestation_Service: authenticate token
    Attestation_Service -->> CC_SDK : authenticated
    CC_SDK -->> Flare_Client_1 : authenticated
 
    alt if  Flare_Server token is verified
        Note over Flare_Server, Flare_Client_1: verify Flare_Client_1 to Flare_Server
        Flare_Client_1 -->> CC_SDK : verify_evidence(client_1_nonce)
        CC_SDK -->> vTMP : generate_evidence(client_1_nonce)
        vTMP -->> CC_SDK : evidence + nonce 
        CC_SDK -->> Attestation_Service: verify_evidence(evidence + Nonce)
        Attestation_Service -->> Attestation_Service: verify against policy
        Attestation_Service -->> CC_SDK: token
        CC_SDK -->> Flare_Client_1 : token
        Flare_Client_1 -->> Flare_Server : token
    else
        Flare_Client_1 -->> Flare_Client_1 : stop self 
    end
    deactivate Flare_Client_1
    
    
    activate Flare_Client_2
    Note over Flare_Server, Flare_Client_2: verify Flare_Client_2 to Flare_Server
    Flare_Server -->>  Flare_Client_2:  Client pull from Server : get task + Flare_Server token
    Flare_Client_2 -->> CC_SDK: authenticate token
    CC_SDK -->> Attestation_Service: authenticate token
    Attestation_Service -->> CC_SDK : authenticated
    CC_SDK -->> Flare_Client_2 : authenticated
    alt if  Flare_Server token is verified
        Flare_Client_2 -->> CC_SDK : verify_evidence(client_2_nonce)
        CC_SDK -->> vTMP : generate_evidence(client_2_nonce)
        vTMP -->> CC_SDK : evidence + nonce 
        CC_SDK -->> Attestation_Service: verify_evidence(evidence + Nonce)
        Attestation_Service -->> Attestation_Service: verify against policy
        Attestation_Service -->> CC_SDK: token
        CC_SDK -->> Flare_Client_2 : token
        Flare_Client_2 -->> Flare_Server : token
    else
        Flare_Client_2 -->> Flare_Client_2 : stop self
    end
    deactivate Flare_Client_2
    
    Note over Flare_Server, Flare_Server : make decision
    Flare_Server -->> Flare_Server : make decision on which Flare Client to accept
    
    Flare_Server --> Flare_Job_Client : get tokens ( Flare_Client_1, Flare_Client_2, Flare_Server)
    
    Flare_Job_Client -->> CC_SDK: authenticate token
    CC_SDK -->> Attestation_Service: authenticate token
    Attestation_Service -->> CC_SDK : authenticated
    CC_SDK -->> Flare_Job_Client : authenticated
    
    alt if authenticated
        Flare_Job_Client -->>  CC_SDK: verify_claim  ( what's the arguments (?) )
        Attestation_Service -->> CC_SDK : verify_claim
        CC_SDK -->> Flare_Job_Client : verify_claim
        alt if claim verified
            Flare_Job_Client -->> Flare_Server: submit_job
        else
            Flare_Job_Client -->> Flare_Job_Client: stop
        end
         
    else
        Flare_Job_Client -->> Flare_Job_Client: stop
    end
     
   
```

