"""Example usage of Adaptive Scheduler"""
import time
import requests
from src.database.models import init_db

# Initialize database
init_db()

# API base URL
BASE_URL = "http://127.0.0.1:5000/api"

def example_session():
    """Example of a complete study session"""
    
    print("=== Starting Adaptive Scheduler Example ===\n")
    
    # 1. Start a session
    print("1. Starting session...")
    response = requests.post(f"{BASE_URL}/start-session", json={
        "user_id": "user123",
        "task_type": "writing",
        "chronotype": "morning",
        "algorithm": "LinUCB"
    })
    
    if response.status_code != 200:
        print(f"Error starting session: {response.text}")
        return
    
    session_data = response.json()
    session_id = session_data['session_id']
    initial_action = session_data['initial_action']
    
    print(f"Session started: {session_id}")
    print(f"Initial recommendation: Work {initial_action['work_interval']} min, "
          f"Break {initial_action['break_duration']} min\n")
    
    # 2. Simulate work interval
    work_duration = initial_action['work_interval']
    print(f"2. Working for {work_duration} minutes...")
    print("   (In real usage, keystrokes would be logged automatically)")
    time.sleep(2)  # Simulate work (shortened for demo)
    
    # 3. End work interval and get break recommendation
    print("\n3. Work interval ended. Computing reward...")
    response = requests.post(f"{BASE_URL}/end-interval", json={
        "session_id": session_id,
        "interval_type": "work",
        "metrics": {
            "chars_typed": 500,  # Simulated
            "cognitive_load_pre_break": 0.7,
            "improved_focus": False,
            "deep_work_interrupted": False
        }
    })
    
    if response.status_code == 200:
        interval_data = response.json()
        next_action = interval_data['next_action']
        reward = interval_data['reward_computed']
        
        print(f"Reward computed: {reward['immediate_reward']:.3f}")
        print(f"Next recommendation: Work {next_action['work_interval']} min, "
              f"Break {next_action['break_duration']} min\n")
    
    # 4. Simulate break
    break_duration = next_action['break_duration']
    print(f"4. Taking break for {break_duration} minutes...")
    time.sleep(1)  # Simulate break (shortened for demo)
    
    # 5. Submit feedback
    print("\n5. Submitting micro-EMA feedback...")
    response = requests.post(f"{BASE_URL}/submit-feedback", json={
        "session_id": session_id,
        "fatigue_level": 2,  # 1-5 scale
        "focus_level": 4,    # 1-5 scale
        "satisfaction": 4    # 1-5 scale
    })
    
    if response.status_code == 200:
        print("Feedback submitted successfully\n")
    
    # 6. Get another recommendation
    print("6. Getting updated recommendation...")
    response = requests.get(f"{BASE_URL}/get-recommendation", params={
        "session_id": session_id
    })
    
    if response.status_code == 200:
        rec_data = response.json()
        print(f"Recommendation: Work {rec_data['work_interval']} min, "
              f"Break {rec_data['break_duration']} min")
        print(f"Explanation: {rec_data['explanation']}\n")
    
    # 7. End session
    print("7. Ending session...")
    response = requests.post(f"{BASE_URL}/end-session", json={
        "session_id": session_id
    })
    
    if response.status_code == 200:
        end_data = response.json()
        print(f"Session ended. Duration: {end_data['duration_minutes']:.1f} minutes")
    
    # 8. Get metrics
    print("\n8. Computing metrics...")
    response = requests.get(f"{BASE_URL}/metrics", params={
        "user_id": "user123"
    })
    
    if response.status_code == 200:
        metrics_data = response.json()
        print("Metrics computed:")
        metrics = metrics_data['metrics']
        for key, value in metrics.items():
            if value is not None:
                print(f"  {key}: {value:.4f}")
        
        print("\nInterpretations:")
        interpretations = metrics_data['interpretation']
        for key, value in interpretations.items():
            print(f"  {key}: {value}")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    print("Note: Make sure the API server is running:")
    print("  python -m src.api.app")
    print("\nStarting example in 3 seconds...\n")
    time.sleep(3)
    
    try:
        example_session()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API server.")
        print("Please start the server first: python -m src.api.app")

