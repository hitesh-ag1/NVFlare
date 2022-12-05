
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

    Flare_Client_1 -->> Flare_Client_1: trigger events ( system start etc.)
    Note over Flare_Client_1, CC_SDK: register Client 1 policy 
    Flare_Client_1 -->> CC_SDK: register Policy (provide client 1 Id) 
    CC_SDK -->> CC_SDK: create or load policy for client 1  ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> Flare_Client_1: policy registration result for client 1
    

    Flare_Client_2 -->> Flare_Client_2: trigger events ( system start, etc.)
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

    Flare_Server -->> Flare_Server: trigger events ( system start etc.)
    Note over Flare_Server, CC_SDK: register FL Server policy
    Flare_Server -->> CC_SDK: register Policy (provide FL Server Id) 
    CC_SDK -->> CC_SDK: create or load policy for FL Server ( from somewhere (?))
    CC_SDK -->> Attestation_Service: register policy
    Attestation_Service -->> CC_SDK: policy registration result
    CC_SDK -->> Flare_Server: policy registration result for FL Server
 
```

## Local Attestation

### Use Cases
There are following use cases in consideration
* Flare Client Node needs to make sure the Flare Server is trust worthy
* Flare Server Node needs to make sure the Flare Client Nodes are trust worthy
* Flare Console Node ( aka Job Client Node) needs to make sure all Flare Server and Flare Clients are trust worthy
* Flare Client Node needs to make sure other Flare Client nodes are trust worthy, For those Nodes, the Client's job will be deployed (via Flare Server Node) to them.

### Open questions
* if the Flare Server is trusty to Flare Client 1, and Node 1, Node 2 are trust worthy to Flare Server,  can the Flare Client 1 considered Node 1 and Node 2 are also trust worthy ? 
  in other words, is the trust transitive ? 
* The Attestation Service returned token, is it safe to be shared ?  for example,  Flare Server received attestation token from Flare Client 1, is it ok to pass the Flare Client 1 token to Flare Client 2.  


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

* Node get attestation token

```mermaid
sequenceDiagram
   autonumber
    
    participant Flare_Node
    participant CC_SDK
    participant vTMP
    participant Attestation_Service

    Flare_Node --> CC_SDK : verify_evidence(Flare_Node_nonce)
    CC_SDK -->> vTMP : generate_evidence(Flare_Node_nonce)
    vTMP -->> CC_SDK : evidence + nonce 
    CC_SDK -->> Attestation_Service: verify_evidence(evidence + Nonce)
    Attestation_Service -->> Attestation_Service: verify against policy
    Attestation_Service -->> CC_SDK: token
    CC_SDK -->> Flare_Node : token  
```

* Node : authenticate(token)

```mermaid
sequenceDiagram
   autonumber
    
    participant Node
    participant CC_SDK
    participant vTMP
    participant Attestation_Service
    Node -->> CC_SDK: authenticate(token)
    CC_SDK -->> Attestation_Service: authenticate(token)
    Attestation_Service -->> CC_SDK : authenticated
    CC_SDK -->> Node : authenticated
```

* Check/enforce Policy on Node

```mermaid
sequenceDiagram
   autonumber
    
    participant request_node
    participant Node
    participant CC_SDK
    participant Attestation_Service
        
    Note over request_node, CC_SDK: check_policy(node_nonce) on Node
    request_node --> CC_SDK : get_attestation_token(node_nonce)
    CC_SDK -->> request_node : Node token
    Node -->> CC_SDK:  authenticate(node token)  
    CC_SDK -->> request_node : Node authenticated
     
    request_node -->>  CC_SDK: verify_claim  ( what's the arguments (?) )
    CC_SDK -->> Attestation_Service : verify_claim
    Attestation_Service -->> CC_SDK : verify_claim result
    CC_SDK -->> request_node : verify_claim result
```

* Flare Client checks if Flare Server is trust worthy

```mermaid
sequenceDiagram
   autonumber
    
    participant Flare_Client
    participant Flare_Server
    participant CC_SDK
    
    Note over Flare_Client, Flare_Server: check_and_register_client()
    Flare_Client -->> Flare_Server: try to register client
    Flare_Client -->> Flare_Server:  get Flare_Server attestation token 
    Flare_Client -->> CC_SDK: check_policy( Flare_Server token)
    CC_SDK -->> Flare_Client: check result
    alt if  Flare_Server policy is verified
         Flare_Client -->> Flare_Server: register client
    else
        Flare_Client -->> Flare_Client: Flare Server is not trusted, stop
    end
   
```


* Flare Server checks if Flare Clients are trust worthy

```mermaid
sequenceDiagram
   autonumber
     
    participant Flare_Client_1
    participant Flare_Client_2
    participant Flare_Server
    participant CC_SDK
     
    activate Flare_Server
    Note over Flare_Server, CC_SDK: get evidence token
    Flare_Server --> CC_SDK : get_attestation_token(Flare_Server_nonce)
    CC_SDK -->> Flare_Server : token
    deactivate Flare_Server
  
    activate Flare_Client_1
    Flare_Client_1 -->> Flare_Server:  check_and_register_client() 
    deactivate Flare_Client_1
    
    activate Flare_Client_2
    Flare_Client_2 -->> Flare_Server:  check_and_register_client() 
    deactivate Flare_Client_2
    
    activate Flare_Server
    Note right of Flare_Server : verify Flare clients if Flare clients are still live
    Flare_Server -->> CC_SDK : check_policies(Flare_Client_1, Flare_Client_2, Flare_Server)
    CC_SDK -->> Flare_Server : Dict( node -> authenticated)
    par for all client nodes 
            alt if flare client is authenticated
                Flare_Server -->>  Flare_Server:  accept client  
            else
                Flare_Server -->>  Flare_Server:  reject client  
            end
    end
```



* Flare Console ( Job Client ) check if Fare Server, Clients are trust worthy

```mermaid
sequenceDiagram
   autonumber
    
    participant Flare_Job_Client
    participant Flare_Server
    participant CC_SDK
    
    Flare_Job_Client -->> Flare_Server: try submit job
    Note right of Flare_Server: Flare_Server has already gathered all live flare client's tokens
    Flare_Job_Client --> Flare_Server : get_all_attestation_tokens()
    par all tokens
        Flare_Job_Client -->> CC_SDK: authenticate (token) & verify_claims()
    end
    
    alt if all verified
        Flare_Job_Client -->> Flare_Server: submit_job
    else
        Flare_Job_Client -->> Flare_Job_Client: stop
    end
   
```


* Flare Client 1 check if the other FL Clients the job code will be deployed to are trust worthy

  * approach one, Flare Client 1 as Flare Server to do it on behalf of Flare Client 1, is this allowed ? 
  * approach two, Flare Server sends all clients' tokens to Flare Client 1. Flare Client 1 ask CC SDK to check for all the clients. Is token sharable ? 

