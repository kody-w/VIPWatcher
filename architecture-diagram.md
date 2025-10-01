# Copilot Agent 365 - System Architecture Diagram

## Enterprise Architecture Overview

```mermaid
graph TB
    subgraph "End User Layer"
        A[Microsoft Teams User]
        B[Web Browser Client]
        C[Mobile App]
    end
    
    subgraph "Microsoft Copilot Studio"
        D[Copilot Studio Agent]
        E[Conversation Flow]
        F[Topic Triggers]
    end
    
    subgraph "Azure API Gateway"
        G[Azure API Management]
        H[Authentication & Authorization]
    end
    
    subgraph "Azure Functions - Consumption Plan"
        I[HTTP Trigger Function<br/>businessinsightbot_function]
        J[Function Runtime<br/>Python 3.11]
        K[CORS Handler]
    end
    
    subgraph "Agent Orchestration Layer"
        L[Assistant Class]
        M[Agent Loader]
        N[Response Parser]
    end
    
    subgraph "AI Agent System"
        O[Context Memory Agent]
        P[Manage Memory Agent]
        Q[Email Drafting Agent]
        R[Adaptive Card Agent]
        S[Custom Agents<br/>Dynamic Loading]
    end
    
    subgraph "Azure OpenAI Service"
        T[GPT-4/GPT-4o Deployment]
        U[Chat Completions API]
        V[Function Calling]
    end
    
    subgraph "Azure Storage Account"
        W[Azure File Share<br/>Persistent Memory]
        X[Shared Memories<br/>Cross-User Context]
        Y[User-Specific Memories<br/>GUID-based Storage]
        Z[Agent Files<br/>Dynamic Agent Storage]
    end
    
    subgraph "Monitoring & Logging"
        AA[Application Insights]
        AB[Function Metrics]
        AC[Error Tracking]
    end
    
    %% User Interactions
    A -->|1. User Message| D
    B -->|1. HTTP Request| G
    C -->|1. Mobile Request| G
    
    %% Copilot Studio to Function
    D -->|2. Action Trigger| G
    E -->|Route to Custom Action| G
    F -->|Topic Match| G
    
    %% API Gateway to Function
    G -->|3. Authenticated Request| H
    H -->|4. Forward with Token| I
    
    %% Function Processing
    I -->|5. Request Validation| K
    K -->|6. Parse JSON Payload| J
    J -->|7. Initialize Assistant| L
    
    %% Agent Orchestration
    L -->|8. Load Available Agents| M
    M -->|9. Scan Agent Files| S
    M -->|10. Import from Storage| Z
    L -->|11. Retrieve Context| O
    
    %% Memory Retrieval
    O -->|12. Fetch Shared Memory| X
    O -->|13. Fetch User Memory| Y
    
    %% OpenAI Processing
    L -->|14. Prepare Messages<br/>System + Context + History| U
    U -->|15. Send Chat Request| T
    T -->|16. Analyze Intent| V
    V -->|17. Function Call Decision| L
    
    %% Agent Execution
    L -->|18. Execute Agent| P
    P -->|19. Store Memory| W
    L -->|18. Execute Agent| Q
    L -->|18. Execute Agent| R
    
    %% Memory Updates
    P -->|20. Update Shared Context| X
    P -->|21. Update User Context| Y
    
    %% Response Flow
    T -->|22. Generate Response| U
    U -->|23. Formatted + Voice Response| L
    L -->|24. Parse Response Parts| N
    N -->|25. Split Formatted/Voice| J
    
    %% Return to User
    J -->|26. JSON Response<br/>{assistant_response, voice_response}| I
    I -->|27. Add CORS Headers| K
    K -->|28. HTTP 200 Response| G
    G -->|29. Return to Client| D
    D -->|30. Display in Teams| A
    G -->|30. Display in Browser| B
    G -->|30. Display in App| C
    
    %% Monitoring
    I -.->|Logs & Metrics| AA
    L -.->|Agent Execution Logs| AB
    J -.->|Errors & Exceptions| AC
    T -.->|Token Usage| AA
    
    %% Styling
    classDef azure fill:#0078D4,stroke:#fff,stroke-width:2px,color:#fff
    classDef openai fill:#10A37F,stroke:#fff,stroke-width:2px,color:#fff
    classDef storage fill:#FFB900,stroke:#fff,stroke-width:2px,color:#000
    classDef agent fill:#8B5CF6,stroke:#fff,stroke-width:2px,color:#fff
    classDef user fill:#50E6FF,stroke:#fff,stroke-width:2px,color:#000
    classDef copilot fill:#7F5AF0,stroke:#fff,stroke-width:2px,color:#fff
    
    class A,B,C user
    class D,E,F copilot
    class G,H,I,J,K azure
    class L,M,N,O,P,Q,R,S agent
    class T,U,V openai
    class W,X,Y,Z storage
    class AA,AB,AC azure
```

## Data Flow Sequence

```mermaid
sequenceDiagram
    participant User as Teams User
    participant CS as Copilot Studio
    participant APIM as API Management
    participant Func as Azure Function
    participant Asst as Assistant Class
    participant Mem as Memory Agents
    participant Store as Azure Storage
    participant AI as Azure OpenAI
    
    User->>CS: Send message via Teams
    CS->>APIM: Trigger custom action
    APIM->>Func: POST /api/businessinsightbot_function
    Note over Func: Validate request & CORS
    
    Func->>Asst: Initialize with user_input
    Asst->>Mem: Load agents from folder
    Mem->>Store: Check for dynamic agents
    Store-->>Mem: Return agent files
    
    Asst->>Mem: Retrieve context memory
    Mem->>Store: Read shared_memories/memory.json
    Store-->>Mem: Shared context
    Mem->>Store: Read user_guid/memory.json
    Store-->>Mem: User-specific context
    Mem-->>Asst: Combined memory context
    
    Asst->>AI: Send messages + functions metadata
    Note over AI: System prompt includes<br/>shared + user memories
    
    AI-->>Asst: Response with function_call
    
    alt Function call required
        Asst->>Mem: Execute agent (e.g., ManageMemory)
        Mem->>Store: Store new memory entry
        Store-->>Mem: Success confirmation
        Mem-->>Asst: Agent execution result
        Asst->>AI: Send function result
        AI-->>Asst: Final formatted response
    else Direct response
        AI-->>Asst: Text response only
    end
    
    Asst->>Asst: Parse formatted + voice parts
    Note over Asst: Split by |||VOICE|||
    
    Asst-->>Func: Return JSON response
    Func-->>APIM: HTTP 200 with CORS headers
    APIM-->>CS: Response data
    CS-->>User: Display in Teams chat
```

## Component Architecture

```mermaid
graph LR
    subgraph "Azure Resource Group"
        subgraph "Compute"
            F1[Function App<br/>Consumption Y1]
            F2[App Service Plan<br/>Linux Python 3.11]
        end
        
        subgraph "AI Services"
            O1[Azure OpenAI<br/>S0 SKU]
            O2[GPT-4o Deployment<br/>10K TPM]
        end
        
        subgraph "Data Storage"
            S1[Storage Account<br/>Standard LRS]
            S2[File Share<br/>5120 GB Quota]
            S3[Blob Storage<br/>Function Code]
        end
        
        subgraph "Monitoring"
            M1[Application Insights<br/>Log Analytics]
        end
        
        subgraph "Security"
            K1[Function Keys<br/>Host & Function Level]
            K2[Managed Identity<br/>System Assigned]
        end
    end
    
    F1 --> O1
    F1 --> S1
    S1 --> S2
    S1 --> S3
    F1 --> M1
    F1 --> K2
    
    classDef compute fill:#0078D4,stroke:#fff,stroke-width:2px,color:#fff
    classDef ai fill:#10A37F,stroke:#fff,stroke-width:2px,color:#fff
    classDef storage fill:#FFB900,stroke:#fff,stroke-width:2px,color:#000
    classDef monitor fill:#E85D04,stroke:#fff,stroke-width:2px,color:#fff
    classDef security fill:#DC143C,stroke:#fff,stroke-width:2px,color:#fff
    
    class F1,F2 compute
    class O1,O2 ai
    class S1,S2,S3 storage
    class M1 monitor
    class K1,K2 security
```

## Agent Execution Flow

```mermaid
flowchart TD
    Start[User Request Received] --> Parse[Parse Request Body]
    Parse --> LoadAgents[Load Agents from Folder]
    LoadAgents --> LoadDynamic[Load Dynamic Agents<br/>from Azure File Share]
    LoadDynamic --> InitMem[Initialize Memory Context]
    
    InitMem --> CheckGUID{User GUID<br/>Provided?}
    CheckGUID -->|Yes| LoadUserMem[Load User-Specific Memory]
    CheckGUID -->|No| UseDefault[Use Default GUID]
    LoadUserMem --> LoadShared[Load Shared Memory]
    UseDefault --> LoadShared
    
    LoadShared --> PrepMsg[Prepare Messages<br/>System + History + User Input]
    PrepMsg --> CallAI[Call Azure OpenAI]
    
    CallAI --> HasFunc{Function<br/>Call?}
    
    HasFunc -->|Yes| ExecAgent[Execute Agent]
    ExecAgent --> AgentType{Agent Type}
    
    AgentType -->|Memory| StoreCtx[Store Context to File Share]
    AgentType -->|Email| DraftEmail[Generate Email Draft]
    AgentType -->|Card| CreateCard[Create Adaptive Card]
    AgentType -->|Custom| CustomLogic[Execute Custom Logic]
    
    StoreCtx --> AddResult[Add Function Result to Messages]
    DraftEmail --> AddResult
    CreateCard --> AddResult
    CustomLogic --> AddResult
    
    AddResult --> NeedMore{Requires<br/>Additional<br/>Action?}
    NeedMore -->|Yes| CallAI
    NeedMore -->|No| FinalCall[Get Final Response from AI]
    
    HasFunc -->|No| ParseResp[Parse Response]
    FinalCall --> ParseResp
    
    ParseResp --> SplitResp[Split Formatted + Voice Response]
    SplitResp --> ReturnJSON[Return JSON with Both Parts]
    ReturnJSON --> End[Send to Client]
    
    style Start fill:#50E6FF,stroke:#fff,stroke-width:2px,color:#000
    style End fill:#10A37F,stroke:#fff,stroke-width:2px,color:#fff
    style ExecAgent fill:#8B5CF6,stroke:#fff,stroke-width:2px,color:#fff
    style CallAI fill:#10A37F,stroke:#fff,stroke-width:2px,color:#fff
    style StoreCtx fill:#FFB900,stroke:#fff,stroke-width:2px,color:#000
```

## Memory Architecture

```mermaid
graph TB
    subgraph "Azure File Share Structure"
        Root[/ Root Share /]
        
        subgraph "Shared Memory"
            SM[shared_memories/]
            SMF[memory.json<br/>Cross-user context]
        end
        
        subgraph "User-Specific Memory"
            U1[user_guid_1/]
            U1F[memory.json<br/>User 1 context]
            U2[user_guid_2/]
            U2F[memory.json<br/>User 2 context]
            UD[default_guid/]
            UDF[memory.json<br/>Default context]
        end
        
        subgraph "Agent Storage"
            AG[agents/]
            AGF1[custom_agent.py]
            AGF2[domain_agent.py]
            MA[multi_agents/]
            MAF1[orchestrator_agent.py]
        end
    end
    
    Root --> SM
    Root --> U1
    Root --> U2
    Root --> UD
    Root --> AG
    Root --> MA
    
    SM --> SMF
    U1 --> U1F
    U2 --> U2F
    UD --> UDF
    AG --> AGF1
    AG --> AGF2
    MA --> MAF1
    
    subgraph "Memory Context Flow"
        Req[Incoming Request]
        Ctx[Context Memory Agent]
        Load[Load Memories]
        Merge[Merge Contexts]
        Prompt[Add to System Prompt]
    end
    
    Req --> Ctx
    Ctx --> Load
    Load --> SMF
    Load --> U1F
    Load --> Merge
    Merge --> Prompt
    
    classDef shared fill:#FFB900,stroke:#fff,stroke-width:2px,color:#000
    classDef user fill:#8B5CF6,stroke:#fff,stroke-width:2px,color:#fff
    classDef agent fill:#0078D4,stroke:#fff,stroke-width:2px,color:#fff
    classDef flow fill:#50E6FF,stroke:#fff,stroke-width:2px,color:#000
    
    class SM,SMF shared
    class U1,U1F,U2,U2F,UD,UDF user
    class AG,AGF1,AGF2,MA,MAF1 agent
    class Req,Ctx,Load,Merge,Prompt flow
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Development"
        Dev[Local Development]
        Git[GitHub Repository]
        Test[Local Testing<br/>func start]
    end
    
    subgraph "Azure Deployment"
        ARM[ARM Template<br/>azuredeploy.json]
        Portal[Azure Portal<br/>Deploy to Azure Button]
    end
    
    subgraph "Provisioned Resources"
        RG[Resource Group]
        
        OAI[Azure OpenAI<br/>+ GPT Deployment]
        FA[Function App<br/>+ Runtime Config]
        ST[Storage Account<br/>+ File Share]
        AI[Application Insights]
        ASP[App Service Plan]
    end
    
    subgraph "Configuration"
        Env[Environment Variables]
        Keys[API Keys & Secrets]
        CORS[CORS Settings]
    end
    
    subgraph "Code Deployment"
        Script[Setup Script<br/>Generated with Keys]
        Clone[Clone Repository]
        Install[Install Dependencies]
        Local[local.settings.json<br/>Auto-created]
        Deploy[Deploy to Azure<br/>Optional via CLI]
    end
    
    Dev --> Git
    Git --> Portal
    Portal --> ARM
    ARM --> RG
    
    RG --> OAI
    RG --> FA
    RG --> ST
    RG --> AI
    RG --> ASP
    
    FA --> Env
    FA --> Keys
    FA --> CORS
    
    ARM --> Script
    Script --> Clone
    Clone --> Install
    Install --> Local
    Local --> Test
    Local --> Deploy
    Deploy --> FA
    
    classDef dev fill:#50E6FF,stroke:#fff,stroke-width:2px,color:#000
    classDef azure fill:#0078D4,stroke:#fff,stroke-width:2px,color:#fff
    classDef config fill:#FFB900,stroke:#fff,stroke-width:2px,color:#000
    classDef code fill:#8B5CF6,stroke:#fff,stroke-width:2px,color:#fff
    
    class Dev,Git,Test dev
    class ARM,Portal,RG,OAI,FA,ST,AI,ASP azure
    class Env,Keys,CORS config
    class Script,Clone,Install,Local,Deploy code
```

## Integration with Microsoft Copilot Studio

```mermaid
graph LR
    subgraph "Copilot Studio Configuration"
        CS1[Create Custom Action]
        CS2[Configure Endpoint<br/>+ Function Key]
        CS3[Define Input Schema<br/>user_input, conversation_history]
        CS4[Define Output Schema<br/>assistant_response, voice_response]
        CS5[Map to Topics]
    end
    
    subgraph "Topic Flow"
        T1[User Trigger]
        T2[Extract Variables]
        T3[Call Custom Action]
        T4[Parse Response]
        T5[Display Formatted Text]
        T6[Optional: Voice Output]
    end
    
    subgraph "Azure Function"
        F1[Receive POST Request]
        F2[Process with AI]
        F3[Return Dual Response]
    end
    
    CS1 --> CS2
    CS2 --> CS3
    CS3 --> CS4
    CS4 --> CS5
    
    CS5 --> T1
    T1 --> T2
    T2 --> T3
    T3 --> F1
    F1 --> F2
    F2 --> F3
    F3 --> T4
    T4 --> T5
    T4 --> T6
    
    classDef studio fill:#7F5AF0,stroke:#fff,stroke-width:2px,color:#fff
    classDef topic fill:#50E6FF,stroke:#fff,stroke-width:2px,color:#000
    classDef function fill:#0078D4,stroke:#fff,stroke-width:2px,color:#fff
    
    class CS1,CS2,CS3,CS4,CS5 studio
    class T1,T2,T3,T4,T5,T6 topic
    class F1,F2,F3 function
```

## Key Features

### 🔐 Security
- Function-level authentication with key-based access
- System-assigned managed identity
- HTTPS-only traffic with TLS 1.2+
- CORS configuration for web clients

### ⚡ Scalability
- Serverless consumption plan (auto-scaling)
- Stateless function design
- Persistent context via Azure Storage
- Up to 200 concurrent instances

### 🧠 AI Capabilities
- GPT-4o latest models with 10K TPM
- Function calling for agent orchestration
- Dual response format (formatted + voice)
- Context-aware memory system

### 💾 Memory System
- Shared cross-user knowledge base
- User-specific GUID-based memory
- Persistent storage in Azure File Share
- Full recall and filtered retrieval

### 🔧 Extensibility
- Dynamic agent loading from storage
- Custom agent creation support
- Multi-agent orchestration
- Modular architecture

## Technical Stack

| Layer | Technology |
|-------|------------|
| **Platform** | Azure Functions (Consumption Plan) |
| **Runtime** | Python 3.11 |
| **AI** | Azure OpenAI GPT-4o |
| **Storage** | Azure File Share |
| **Monitoring** | Application Insights |
| **Frontend** | Microsoft Teams via Copilot Studio |
| **API** | REST with JSON |
| **Authentication** | Function Keys + Managed Identity |

## Cost Optimization

- **Consumption Plan**: Pay only for execution time
- **Storage**: Standard LRS for cost efficiency
- **OpenAI**: Token-based pricing (~$0.01/1K tokens)
- **Monthly Estimate**: ~$5-10 + token usage

