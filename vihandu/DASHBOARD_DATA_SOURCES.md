# Dashboard Data Sources - Real vs Simulated

## 📊 What the Dashboard Shows

### ✅ **REAL DATA (Connected to API & Database)**

#### 1. **Break Schedule / Recommendations**
- **Source**: Real API calls to `/api/start-session` and `/api/get-recommendation`
- **Data**: Actual bandit algorithm recommendations
- **What it shows**:
  - Work interval (20/30/45/60 min) - **REAL**
  - Break duration (3/5/8/12 min) - **REAL**
  - Algorithm explanation - **REAL**
  - Confidence score - **REAL** (from bandit algorithm)
  - Safety override status - **REAL**
  - Override reason - **REAL**

#### 2. **Session Management**
- **Source**: Real API calls
- **Data**: Actual session IDs, user IDs, algorithm selection
- **What it shows**:
  - Session ID - **REAL**
  - User ID - **REAL**
  - Algorithm (LinUCB/Thompson Sampling) - **REAL**
  - Task type, chronotype - **REAL**

#### 3. **Rewards**
- **Source**: Real API call to `/api/end-interval`
- **Data**: Actual computed rewards from `RewardCalculator`
- **What it shows**:
  - Immediate reward - **REAL** (computed from task progress + load relief)
  - Reward components (r_progress, r_relief) - **REAL**
  - Final reward - **REAL**

#### 4. **Action History**
- **Source**: Real actions taken during session
- **Data**: Actual work/break intervals selected
- **What it shows**:
  - Each recommendation - **REAL**
  - Reward for each action - **REAL**
  - Timestamps - **REAL**

#### 5. **Algorithm Metadata**
- **Source**: Real bandit algorithm output
- **Data**: Actual algorithm state
- **What it shows**:
  - Algorithm name (LinUCB/Thompson Sampling) - **REAL**
  - Confidence score - **REAL**
  - Epoch counter - **REAL** (increments with each action)
  - Was overridden flag - **REAL**

### ⚠️ **SIMULATED DATA (Dummy/Placeholder)**

#### 1. **Cognitive Load**
- **Source**: Simulated random values
- **Current**: `0.3 + Math.random() * 0.4` (30-70% range)
- **Why**: In real system, this would come from:
  - Keystroke analysis (IKI, typing speed, corrections)
  - Micro-EMA feedback
  - Feature extractor processing
- **What to show**: Currently shows random values for demo purposes
- **Real implementation**: Would call feature extractor API endpoint

#### 2. **Metrics for End Interval**
- **Source**: Partially simulated
- **What's simulated**:
  - `chars_typed`: Random between 200-700 - **SIMULATED**
  - `improved_focus`: Always `true` - **SIMULATED**
  - `deep_work_interrupted`: Always `false` - **SIMULATED**
- **What's real**:
  - `cognitive_load_pre_break`: Uses current displayed load - **DERIVED FROM SIMULATED**
  - `cognitive_load_post_break`: Calculated from pre-break - **DERIVED**

#### 3. **Auto-Refresh Cognitive Load**
- **Source**: Simulated every 5 seconds
- **Current**: Random values between 30-70%
- **Real implementation**: Would poll feature extractor or use WebSocket

---

## 🔌 API Connections

### Connected Endpoints:

1. **`POST /api/start-session`** ✅
   - Sends: user_id, task_type, chronotype, algorithm
   - Receives: session_id, initial_action, metadata
   - **Status**: Fully connected, real data

2. **`GET /api/get-recommendation`** ✅
   - Sends: session_id
   - Receives: work_interval, break_duration, explanation, confidence, was_overridden
   - **Status**: Fully connected, real data

3. **`POST /api/end-interval`** ✅
   - Sends: session_id, interval_type, metrics (partially simulated)
   - Receives: next_action, reward_computed, metadata
   - **Status**: Connected, but metrics input is simulated

4. **`POST /api/end-session`** ✅
   - Sends: session_id
   - Receives: session_ended, duration_minutes
   - **Status**: Fully connected, real data

### Not Connected (Could Be Added):

- **`GET /api/metrics`** ❌
  - Could show PG, RPH, AHL, EOI, AUC-BUC, CTU, SPF, SVR
  - Currently not displayed in dashboard
  - Would need additional UI component

- **Cognitive Load API** ❌
  - No endpoint exists to get real-time cognitive load
  - Would need: `GET /api/cognitive-load?session_id=...`
  - Currently simulated

---

## 🎯 What This Means for Your Supervisor Demo

### ✅ **What's Impressive (Real Data)**:
1. **Adaptive Learning**: Real bandit algorithm making decisions
2. **Safety Constraints**: Real safety overrides when needed
3. **Reward Computation**: Real reward calculation from your system
4. **Algorithm Comparison**: Can switch between LinUCB and Thompson Sampling
5. **Learning Progress**: Real epoch counter showing learning iterations

### ⚠️ **What's Simulated (For Demo)**:
1. **Cognitive Load**: Random values (30-70%) instead of real keystroke analysis
2. **Typing Metrics**: Random chars_typed instead of actual keystroke counting
3. **User Feedback**: Always positive (improved_focus = true)

---

## 🔧 How to Make It Fully Real

### Option 1: Add Cognitive Load Endpoint
```python
# In src/api/app.py
@app.route('/api/cognitive-load', methods=['GET'])
def get_cognitive_load():
    session_id = request.args.get('session_id')
    feature_extractor = feature_extractors[session_id]
    features = feature_extractor.extract_features()
    return jsonify({
        'cognitive_load': features.cognitive_load,
        'typing_speed': features.typing_speed,
        'mean_iki': features.mean_iki
    })
```

### Option 2: Use Real Keystroke Data
- Connect keystroke listener
- Use actual typing patterns
- Compute real cognitive load from IKI analysis

### Option 3: Add Metrics Display
- Add section to show all 8 metrics
- Call `/api/metrics` endpoint
- Display PG, RPH, AHL, etc.

---

## 📋 Summary Table

| Component | Data Source | Real/Simulated | Notes |
|-----------|------------|----------------|-------|
| Work/Break Recommendations | API `/api/get-recommendation` | ✅ **REAL** | Actual bandit decisions |
| Confidence Score | API response | ✅ **REAL** | From bandit algorithm |
| Algorithm Name | API response | ✅ **REAL** | LinUCB or Thompson Sampling |
| Safety Overrides | API response | ✅ **REAL** | Actual safety constraint checks |
| Rewards | API `/api/end-interval` | ✅ **REAL** | Computed by RewardCalculator |
| Action History | Session actions | ✅ **REAL** | Actual recommendations made |
| Epoch Counter | Session state | ✅ **REAL** | Increments with each action |
| Cognitive Load | JavaScript random | ⚠️ **SIMULATED** | Random 30-70% for demo |
| Typing Metrics | JavaScript random | ⚠️ **SIMULATED** | Random chars_typed |
| User Feedback | Hardcoded | ⚠️ **SIMULATED** | Always positive |
| All 8 Metrics | Not displayed | ❌ **NOT SHOWN** | Could add metrics panel |

---

## 💡 For Your Supervisor

**What to Say:**
- "The recommendations, rewards, and learning are all real - using actual bandit algorithms"
- "The cognitive load is currently simulated for demo purposes, but the system is designed to use real keystroke analysis"
- "You can see the system learning in real-time as rewards update the bandit parameters"
- "Safety constraints are actively working - you'll see overrides when cognitive load gets too high"

**What's Impressive:**
- Real adaptive learning happening
- Real safety constraints working
- Real algorithm comparison (LinUCB vs Thompson Sampling)
- Real reward computation
- Professional UI showing all key components

---

**Bottom Line**: The core adaptive scheduler functionality is **100% real**. Only the input metrics (cognitive load, typing speed) are simulated for demo purposes. The bandit algorithms, recommendations, rewards, and learning are all authentic.

