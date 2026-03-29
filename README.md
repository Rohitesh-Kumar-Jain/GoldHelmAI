# 🔱 GoldHelm AI

**GoldHelm AI** is a production-grade multi-agent financial intelligence platform designed for next-day gold futures forecasting and explainable trading decision support. It bridges the gap between deep machine learning signals and human-readable market context.

---

## 🏗️ System Architecture

GoldHelm follows a decoupled, cloud-native architecture optimized for real-time inference and explainable outputs.

```mermaid
flowchart TD

    User[User]

    subgraph Frontend [Frontend - Vercel]
        UI[React + Vite Dashboard]
    end

    subgraph Backend [Backend - FastAPI on Render]
        
        subgraph Ingestion
            YF[Yahoo Finance API]
            GN[Google News RSS]
        end

        subgraph Services
            IE[Indicator Engine]
            SS[Scoring Service]
            NS[Sentiment Service]
        end

        subgraph Agents
            RA[Reasoning Agent]
            RL[RL Agent]
            CA[Coordinator Agent]
        end

        Payload[Dashboard Payload API]
    end

    User --> UI
    UI -->|REST API| Payload

    Payload --> IE
    Payload --> NS

    YF --> IE
    GN --> NS

    IE --> SS
    NS --> SS

    SS --> RA
    SS --> RL

    RA --> CA
    RL --> CA

    CA --> Payload
```

---

## 🧠 The Intelligence Stack

### 1. Multi-Agent Orchestration
GoldHelm doesn't just return a raw number; it hosts a "Debate" between three distinct AI agents to reach a final consensus:

*   **Reasoning Agent:** A deterministic logical engine that processes technical signals into human-readable rationales.
*   **RL Policy Agent:** A Q-Learning agent trained on rewards (profit/loss) that suggests an optimal trading action based on the current market state.
*   **Coordinator Agent:** The final decision-maker. It evaluates the "Trust Grid"—if the reasoning and RL agents disagree, it dynamically shifts the final decision to **HOLD** to manage risk.

### 2. RL Agent State Machine
The Reinforcement Learning agent transitions through these states based on signal confidence and reward history:

```mermaid
stateDiagram-v2
    [*] --> Neutral

    Neutral --> Bullish : Positive Signals
    Neutral --> Bearish : Negative Signals

    Bullish --> Buy : Strong Confidence
    Bearish --> Sell : Strong Confidence

    Buy --> Hold : Profit Taken
    Sell --> Hold : Position Closed

    Hold --> Neutral : Reset State
```

### 3. The Weighted Scoring Engine (`[-100, 100]`)
Indicator signals are normalized into a continuous score using a Weighted Confluence logic:

| Cluster | Weight | Indicators Included |
| :--- | :--- | :--- |
| **Trend** | 40% | EMA(20), EMA(50), ADX Strength |
| **Momentum** | 30% | RSI(14), MACD Crossovers, Stochastic |
| **Volatility** | 15% | Bollinger Band Width, ATR Volatility |
| **Structure** | 15% | Fibonacci Retracement, On-Balance Volume |

---

## 🌊 Data Architecture

### Data Flow Diagram (DFD)
The movement of data from raw API extraction to final visual rendering.

```mermaid
flowchart LR
    RawData[Market Data + News]
    Processing[Feature Engineering]
    Indicators[Technical Indicators]
    Sentiment[Sentiment Scores]
    Fusion[Signal Fusion Engine]
    Agents[AI Agents]
    Decision[Final Decision]
    UI[Dashboard]

    RawData --> Processing
    Processing --> Indicators
    Processing --> Sentiment

    Indicators --> Fusion
    Sentiment --> Fusion

    Fusion --> Agents
    Agents --> Decision
    Decision --> UI
```

### ML Pipeline (Offline + Online)
GoldHelm maintains a separate pipeline for batch training and real-time inference.

```mermaid
flowchart TD
    subgraph Offline Training
        D1[Historical Data]
        F1[Feature Engineering]
        M1[Model Training]
        E1[Evaluation]
        R1[Model Registry]
    end

    subgraph Online Inference
        D2[Live Market Data]
        F2[Real-time Features]
        M2[Loaded Model]
        P1[Prediction]
    end

    R1 --> M2

    D2 --> F2
    F2 --> M2
    M2 --> P1
```

---

## 🔄 End-to-End Sequence
The sequence of events triggered when a user opens the dashboard.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant YahooAPI
    participant NewsAPI
    participant IndicatorEngine
    participant SentimentService
    participant ScoringService
    participant RLAgent
    participant ReasoningAgent
    participant Coordinator

    User->>Frontend: Open Dashboard
    Frontend->>Backend: GET /dashboard

    Backend->>YahooAPI: Fetch gold price data
    Backend->>NewsAPI: Fetch headlines

    YahooAPI-->>Backend: Market data
    NewsAPI-->>Backend: News data

    Backend->>IndicatorEngine: Compute indicators
    Backend->>SentimentService: Analyze sentiment

    IndicatorEngine-->>Backend: Indicator signals
    SentimentService-->>Backend: Sentiment scores

    Backend->>ScoringService: Generate confluence score

    ScoringService-->>Backend: Score [-100,100]

    Backend->>RLAgent: Predict action
    Backend->>ReasoningAgent: Generate explanation

    RLAgent-->>Backend: Action (Buy/Sell/Hold)
    ReasoningAgent-->>Backend: Rationale

    Backend->>Coordinator: Resolve decision

    Coordinator-->>Backend: Final Decision + Risk

    Backend-->>Frontend: Dashboard Payload
    Frontend-->>User: Render UI (Charts + Debate + Score)
```

---

## 🚀 Setup & Deployment

### Backend (Python 3.11+)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend (React / Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## 🛠️ Infrastructure Overview
```mermaid
flowchart TD
    User[User Browser]

    subgraph Frontend
        Vercel[Vercel CDN + React App]
    end

    subgraph Backend
        Render[FastAPI on Render]
    end

    subgraph DataSources
        Yahoo[Yahoo Finance API]
        News[Google News RSS]
    end

    User --> Vercel
    Vercel --> Render

    Render --> Yahoo
    Render --> News
```
