
# Basic CC Sequence Diagrams

## Preparation
* Question
    * do we need to register two types of policies:
        1) what policy that this device will accept ? 
        2) what policy ( claim(?) ) that this device has ?
      
### Preparation Actions: register_policy()

* We use FL Server, FL Client to indicate the Client nodes and Server in Federated Computing setting
* For non-High Availability Case, FLARE will have one (1) FL server + Many (N) FL Clients
* For High Availability Case, FLARE will have two (2) FL server + One (1) overseer + Many (N) FL Clients
* Node here represent individual node (FL Server, FL Client, FL Overseer, FL job Client)

```mermaid
sequenceDiagram
   autonumber
    participant Node
    participant CC_SDK
    participant CC_Orchestrator
    participant Attestation_Service

    Note over Node, Attestation_Service: register_policy() 
    Node -->> CC_SDK: register Policy (node name)  
    CC_SDK -->> CC_SDK: create or load policy for Node  ( from somewhere (?))
    CC_SDK -->> CC_Orchestrator: register policy
    CC_Orchestrator -->> CC_Orchestrator: verify policy correctness ( how ?) 
    CC_Orchestrator -->> Attestation_Service: register policy
    Attestation_Service -->> CC_Orchestrator: policy registration result
    CC_Orchestrator -->> CC_SDK: policy registration result
    
    CC_SDK -->> Node: policy registration result for Flare_Node
    
```
 
## Local Attestation

Every Node needs to attest for itself.

### Local Attestation

* Node registration_node()

```mermaid
sequenceDiagram
   autonumber
    participant Node
    participant CC_SDK
    participant CC_Orchestrator    
 
    Node -->> CC_SDK: registration_node() with CC Orchestor
    Note left of CC_SDK: a nonce is an arbitrary number that can be used just once in a cryptographic communication.
    CC_SDK -->> CC_Orchestrator : registration_node() 
    CC_Orchestrator -->> CC_SDK : createNonce() 
    CC_SDK -->> Node : nonce
      
```

* Node verify_evidence()

```mermaid
sequenceDiagram
   autonumber
    
    participant Node
    participant CC_SDK
    participant vTMP
    participant Attestation_Service
    participant CC_Orchestrator
       
    note over Node, CC_SDK: combine severall calls into single verify_evidence() call (different from original diagram)
    Node --> CC_SDK : verify_evidence(Node_nonce)
    CC_SDK -->> vTMP : generate_evidence(Node_nonce) -> TMPQuote
    vTMP -->> CC_SDK : evidence + nonce
    
    Note over CC_SDK,Attestation_Service : calling  verify_evidence() directly ( different from original diagram)
    CC_SDK -->> Attestation_Service: verify_evidence(evidence + Nonce), provide evidence
    Attestation_Service -->> Attestation_Service: verify against policy
    Attestation_Service -->> CC_SDK: token
    CC_SDK -->> Node : token  
    
    note over Node, CC_Orchestrator : provide_evidence via CC SDK ( different from original diagram)
    Node -->> CC_SDK : token + provide_evidence(token)
    CC_SDK -->> CC_Orchestrator : token + provide_evidence(token)
    
    note right of CC_Orchestrator : add save() function
    CC_Orchestrator -->> CC_Orchestrator: save dict(tokem, evendidence)
```


## Enforce Policy

### check_authentication( participant token)
 
```mermaid
sequenceDiagram
   autonumber
    
    participant Request_Node
    participant CC_SDK
    participant Attestation_Service
    Request_Node -->> CC_SDK: authenticate( participant token)
    CC_SDK -->> Attestation_Service: authenticate(participant token)
    Attestation_Service -->> CC_SDK : participant token authenticated
    CC_SDK -->> Request_Node : participant token authenticated
```

### enforce policy: enforce_policy()

```mermaid
sequenceDiagram
   autonumber
    
    participant Node
    participant CC_SDK
    participant CC_Orchestrator
        
    Node -->> CC_SDK : send_token_to_orchestrator(node attestation token)
    CC_SDK -->> CC_Orchestrator:  send_token_to_orchestrator(node's attestation token)
    Node -->> CC_SDK : get_participant_tokens() from CC orchestrator
    CC_SDK -->> CC_Orchestrator : get_participant_tokens()
    CC_Orchestrator -->> CC_SDK : participant tokens 
    CC_SDK -->> Node :  participant tokens 
    loop all participant tokens
        Node -->> CC_SDK : check_authentication(participate token) (details omitted) -- check participant token authenticity
        CC_SDK -->> Node : authentication result
        alt if authenticated
            Node -->>  CC_SDK: verify_claim  ( what's the arguments (?) )
            CC_SDK -->> Attestation_Service : verify_claim
            Attestation_Service -->> CC_SDK : verify_claim result
            CC_SDK -->> Node : verify_claim result
    end
    Node -->> Node : make decision for participants
```

# FLARE system preparation, local attestation and policy enforcement

with above basic diagrams, now we apply above to Flare System.

#### Assumptions
* CC Orchestrator will be hosted by FL Server's Node
* communication between CC SDK and CC Orchestrator is considered trust worthy
* Flare Job Client = Flare Console Node, or node running Flare Notebook

## Flare nodes prepare
* based on system start event or initial handshake ( in case of notebook admin API runner)

```mermaid
sequenceDiagram
   autonumber
    participant FL_Node
    participant CC_SDK
    participant CC_Orchestrator
    note right of FL_Node : all FL_Node preparements are done independently, not necessarily at the same time
    par for node in [ FL_Server(s), Overseer, FL_Clients]
        FL_Node -->> FL_Node: trigger event (system start) 
        FL_Node -->> CC_SDK: register_policy(node)
        FL_Node -->> CC_Orchestrator: register_policy(node)
    end     
    Note right of CC_Orchestrator: CC_Orchestrator has no knowledge of FLARE concepts
    CC_Orchestrator -->> CC_Orchestrator: check at least 1 node has policy 
    
```

## Flare nodes local attestation

### system start event

```mermaid
sequenceDiagram
   autonumber
    participant FL_Node
    participant CC_SDK
    participant CC_Orchestrator
    note right of FL_Node : all FL_Node attestation are done independently, not necessarily at the same time
    par for node in [ FL_Server(s), Overseer, FL_Clients]
        FL_Node -->> FL_Node: trigger event (system start)
        note over FL_Node, CC_SDK: sdk.attest(node) 
        FL_Node -->> CC_SDK: registration_node(node)
        CC_SDK -->> CC_Orchestrator: registration_node(node)
        FL_Node -->> CC_SDK: verify_evidence(node)
        CC_SDK -->> CC_Orchestrator: verify_evidence(node)
    end     
    
```

### submit job event


```mermaid
sequenceDiagram
   autonumber
    participant FL_Job_Client
    participant FL_Server
    participant CC_SDK
    participant CC_Orchestrator
    
    FL_Job_Client -->> FL_Server: triggered by submit Job
    FL_Server -->> FL_Server: call CC prepare() 
    FL_Server -->> CC_SDK: registration_node(FL_server node)
    CC_SDK -->> CC_Orchestrator: registration_node(FL_server node)
    FL_Server -->> CC_SDK: verify_evidence(FL_server node)
    CC_SDK -->> CC_Orchestrator: verify_evidence(FL_server node)
    
```

### connect to Oversee event

#### Flare Job Client = Flare Console Node, or node running Flare Notebook

```mermaid
sequenceDiagram
   autonumber
    participant FL_Job_Client
    participant FL_Overseer
    participant CC_SDK
    participant CC_Orchestrator
    
    FL_Job_Client -->> FL_Overseer: triggered by seach for SP connection
    FL_Overseer -->> FL_Overseer: call CC prepare() 
    FL_Overseer -->> CC_SDK: registration_node(FL_Overseer node)
    CC_SDK -->> CC_Orchestrator: registration_node(FL_Overseer node)
    FL_Overseer -->> CC_SDK: verify_evidence(FL_Overseer node)
    CC_SDK -->> CC_Orchestrator: verify_evidence(FL_Overseer node)
    
```

### FL Server deploy app to clients event
 
```mermaid
sequenceDiagram
   autonumber
    participant FL_Server
    participant FL_Client
    participant CC_SDK
    participant CC_Orchestrator
    
    FL_Server -->> FL_Client: triggered by deploy app event
    FL_Client -->> FL_Client: call CC prepare() 
    FL_Client -->> CC_SDK: registration_node(FL_Client node)
    CC_SDK -->> CC_Orchestrator: registration_node(FL_Client node)
    FL_Client -->> CC_SDK: verify_evidence(FL_Client node)
    CC_SDK -->> CC_Orchestrator: verify_evidence(FL_Client node)
    
```


## Flare nodes policy enforcements

#### Use Cases
There are following use cases in consideration
* Flare Server Node needs to make sure all participants are trust worthy, i.e Overseer, All FL Clients
* Flare Client Node needs to make sure all participants are trust worthy, i.e FL Server1,2, Overseer, other FL Clients
* Flare Job Client needs to make sure all FL Servers, overseer and all FL Clients are trust worthy
 
### Use Case 1: **Flare Server** Node needs to make sure all participants are trust worthy, i.e Overseer, All FL Clients

```mermaid
sequenceDiagram
   autonumber
    
    participant FL_Job_Client
    participant FL_Server
    participant FL_Overseer
    participant FL_Client
    participant CC_SDK
    FL_Job_Client -->>  FL_Server: try to submit Job 
    FL_Server -->>  FL_Server: deploy job to FL Clients
    FL_Server -->>  FL_Server: trigger event for CC policy enforcements
    
    FL_Server --> CC_SDK : enforce_policy(): get participant tokens from CC_orchestrator for FL Overseer, FL Clients 
    CC_SDK -->> FL_Server : policy result
    alt if policy not verified for overseer
        FL_Server --> FL_Server : deny Overseer for future communication
    end
    loop over FL Clients
        alt if policy is not veriied for client
            FL_Server --> FL_Server : deny FL client participation
        else
            FL_Server --> FL_Server : FL Client accepted
        end
    end
    
     FL_Server --> FL_Server : check min Fl_client before proceed
     FL_Server --> FL_Server : deploy_app() continues
     FL_Server --> FL_Server : submit_job() continues
    
```

 
### Use Case 2: **Flare Client** node needs to make sure all participants are trust worthy, i.e FL Server(s), Overseer, other FL Clients

* get task() event

```mermaid
sequenceDiagram
   autonumber

    participant Flare_Client
    participant Flare_Server
    participant CC_SDK
    
    Flare_Client -->> Flare_Server: try to pull task from FL Server, trigger event to check CC policy
    Flare_Client -->> Flare_Client:  enforce_policy()
    Flare_Client --> CC_SDK : enforce_policy(): get participant tokens from CC_orchestrator for FL Overseer, FL Server and other FL Clients 
    CC_SDK -->> Flare_Client : policy result
    alt if policy not verified for overseer
        Flare_Client --> FL_Server : deny Overseer for future communication
    end

    alt if policy not verified for FL Server
        Flare_Client --> stop : can't continue
    else
        loop over other FL Clients
            alt if policy is not veriied for any clients
                Flare_Client --> Flare_Client: stop job, ask user to change deploy_map configuration
            else
                Flare_Client --> FL_Server : get task () continues
            end
        end
    end
   
```

### Use Case 3: Flare Job Client needs to make sure all FL Servers, overseer and all FL Clients are trust worthy

```mermaid
sequenceDiagram
   autonumber
    
    participant Flare_Job_Client
    participant Flare_Server
    participant Flare_Client
    participant CC_SDK
    
    Flare_Job_Client -->> Flare_Server: submit job
    Flare_Job_Client -->> Flare_Job_Client: trigger local attestation 
    Flare_Job_Client -->> CC_SDK: attest(Flare_Job_Client)
    Flare_Job_Client -->> CC_SDK: enforce_policy(): 
    CC_SDK --> Flare_Job_Client: policy enforncement results
    
    alt if all verified
        Flare_Job_Client -->> Flare_Server: submit_job
    else
        Flare_Job_Client -->> Flare_Job_Client: stop
    end
   
```
 