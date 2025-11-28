# Adaptive Scheduler GUI Dashboard

## 🎯 Overview

A modern, real-time web-based dashboard for visualizing the Adaptive Scheduler system. Perfect for demonstrating the system to your supervisor!

## ✨ Features

### 1. **Real-Time Break Schedule Display**
- Current work/break intervals
- Live countdown timer
- Visual schedule indicators

### 2. **Cognitive Load Visualization**
- Real-time cognitive load percentage
- Color-coded load indicators (green/yellow/red)
- Load trend explanations

### 3. **Adaptive Recommendations**
- Current recommended work/break intervals
- Algorithm explanation (why this recommendation?)
- Confidence scores
- Safety override indicators

### 4. **Key Metrics Dashboard**
- Algorithm confidence
- Current algorithm (LinUCB/Thompson Sampling)
- Epoch counter (learning progress)
- Reward values

### 5. **Action History**
- Complete history of recommendations
- Reward values for each action
- Timestamp tracking

### 6. **Session Management**
- Start new sessions
- Configure user settings (chronotype, task type, algorithm)
- End sessions gracefully

## 🚀 How to Use

### Step 1: Start the Server
```bash
python run_server.py
```

### Step 2: Open Dashboard
Open your browser and navigate to:
```
http://127.0.0.1:5000/dashboard
```

### Step 3: Start a Session
1. Fill in the session form:
   - User ID (e.g., "demo_user")
   - Task Type (writing, coding, reading, other)
   - Chronotype (morning, evening, neutral)
   - Algorithm (LinUCB or Thompson Sampling)

2. Click "Start Session"

### Step 4: Interact with the System
- **Timer**: Watch the countdown for current work/break interval
- **Get Recommendation**: Click to get updated recommendation
- **End Work/Break**: End current interval and compute reward
- **End Session**: Close the session

## 📊 What to Show Your Supervisor

### 1. **Adaptive Learning in Action**
- Start a session
- Show how recommendations change over time
- Demonstrate that the system learns from rewards

### 2. **Safety Constraints**
- Show safety overrides when cognitive load is high
- Explain why recommendations are adjusted

### 3. **Real-Time Updates**
- Cognitive load updates automatically
- Recommendations refresh periodically
- Action history builds up

### 4. **Algorithm Comparison**
- Start sessions with different algorithms (LinUCB vs Thompson Sampling)
- Compare confidence scores
- Show how different algorithms make different recommendations

### 5. **Metrics Visualization**
- Show confidence scores
- Display reward values
- Track learning progress (epoch counter)

## 🎨 Dashboard Components

### Timer Display
- Large countdown timer
- Current work/break interval values
- Visual indicators

### Cognitive Load Gauge
- Percentage display
- Color-coded bar (green = low, yellow = medium, red = high)
- Real-time updates

### Recommendation Panel
- Recommended intervals
- Algorithm explanation
- Safety override warnings (if applicable)

### Metrics Cards
- Confidence: Algorithm's confidence in recommendation
- Algorithm: Current algorithm being used
- Epoch: Number of learning iterations
- Reward: Last computed reward value

### Action History
- Chronological list of all recommendations
- Reward values for each action
- Timestamps

## 🔧 Technical Details

### Frontend
- Pure HTML/CSS/JavaScript (no frameworks needed)
- Responsive design
- Real-time updates via API polling

### Backend Integration
- Connects to Flask REST API
- Uses existing endpoints:
  - `POST /api/start-session`
  - `GET /api/get-recommendation`
  - `POST /api/end-interval`
  - `POST /api/end-session`

### Auto-Refresh
- Dashboard updates every 5 seconds
- Cognitive load simulated (in real app, would come from keystroke analysis)
- Recommendations refresh automatically

## 📝 For Supervisor Demo

### Quick Demo Script (5 minutes)

1. **Introduction (30 sec)**
   - "This is the Adaptive Scheduler GUI"
   - "It shows real-time break recommendations based on cognitive load"

2. **Start Session (1 min)**
   - Fill in form
   - Show initial recommendation
   - Explain the timer

3. **Show Learning (2 min)**
   - End a work interval
   - Show reward computation
   - Show updated recommendation
   - Explain how it adapts

4. **Show Safety (1 min)**
   - Explain safety constraints
   - Show override mechanism (if triggered)

5. **Show Metrics (30 sec)**
   - Point out confidence scores
   - Show action history
   - Explain learning progress

### Key Points to Emphasize

✅ **Adaptive**: System learns and improves over time  
✅ **Context-Aware**: Recommendations based on cognitive load  
✅ **Safe**: Safety constraints prevent harmful recommendations  
✅ **Transparent**: Shows explanations for recommendations  
✅ **Real-Time**: Updates automatically as user works  

## 🎯 What Makes This Impressive

1. **Visual Feedback**: Supervisor can see the system working in real-time
2. **Transparency**: Shows WHY recommendations are made
3. **Learning Progress**: Demonstrates improvement over time
4. **Professional UI**: Clean, modern interface
5. **Complete System**: Shows all components working together

## 🐛 Troubleshooting

### Dashboard not loading?
- Make sure server is running: `python run_server.py`
- Check URL: `http://127.0.0.1:5000/dashboard`
- Check browser console for errors

### API errors?
- Ensure database is initialized: `python init_database.py`
- Check server logs for errors
- Verify API endpoints are working: `http://127.0.0.1:5000/api/health`

### Timer not updating?
- Check browser console
- Verify session is active
- Refresh the page if needed

## 📁 Files

- `static/dashboard.html` - Main dashboard file
- `src/api/app.py` - Flask route for serving dashboard
- This file - Documentation

---

**Ready to impress your supervisor!** 🚀

