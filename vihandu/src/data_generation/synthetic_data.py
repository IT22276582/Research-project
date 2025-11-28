"""Generate synthetic data for testing and simulation"""
import numpy as np
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass
from src.database.models import (
    Session, KeystrokeEvent, ContextVector, Action, Reward, MicroEMA,
    SessionLocal, init_db
)
from config.config import WORK_INTERVALS, BREAK_DURATIONS


@dataclass
class SyntheticUser:
    """Synthetic user profile"""
    user_id: str
    chronotype: str  # 'morning', 'evening', 'neutral'
    typing_speed_base: float  # Base typing speed (chars/min)
    cognitive_load_base: float  # Base cognitive load
    optimal_work_interval: int  # Optimal work duration
    optimal_break_duration: int  # Optimal break duration


class SyntheticDataGenerator:
    """Generate synthetic keystroke and session data for testing"""
    
    def __init__(self):
        self.db_session = SessionLocal()
    
    def generate_user_profile(self, user_id: str = None) -> SyntheticUser:
        """Generate a synthetic user profile"""
        if user_id is None:
            user_id = f"user_{random.randint(1000, 9999)}"
        
        chronotype = random.choice(['morning', 'evening', 'neutral'])
        typing_speed_base = random.uniform(80, 150)  # chars/min
        cognitive_load_base = random.uniform(0.3, 0.7)
        optimal_work_interval = random.choice(WORK_INTERVALS)
        optimal_break_duration = random.choice(BREAK_DURATIONS)
        
        return SyntheticUser(
            user_id=user_id,
            chronotype=chronotype,
            typing_speed_base=typing_speed_base,
            cognitive_load_base=cognitive_load_base,
            optimal_work_interval=optimal_work_interval,
            optimal_break_duration=optimal_break_duration
        )
    
    def generate_keystroke_events(self, session_id: str, duration_minutes: float,
                                  typing_speed: float, cognitive_load: float) -> List[KeystrokeEvent]:
        """
        Generate synthetic keystroke events
        
        Args:
            session_id: Session identifier
            duration_minutes: Duration of session in minutes
            typing_speed: Target typing speed (chars/min)
            cognitive_load: Cognitive load (affects IKI variance)
        
        Returns:
            List of KeystrokeEvent objects
        """
        events = []
        duration_seconds = duration_minutes * 60
        
        # Compute IKI based on typing speed
        # IKI = 60 / (typing_speed * chars_per_keystroke)
        # Assuming ~5 chars per keystroke on average
        chars_per_keystroke = 5.0
        mean_iki = 60.0 / (typing_speed * chars_per_keystroke)
        
        # Cognitive load affects IKI variance (higher load = more variance)
        iki_std = mean_iki * (0.2 + cognitive_load * 0.3)
        
        current_time = datetime.utcnow().timestamp()
        last_key_time = current_time
        
        # Generate events for duration
        while (current_time - datetime.utcnow().timestamp()) < duration_seconds:
            # Sample IKI from normal distribution
            iki = np.random.normal(mean_iki, iki_std)
            iki = max(0.01, min(iki, 5.0))  # Clamp to valid range
            
            # Key down
            key_code = random.randint(32, 126)  # Printable ASCII
            events.append(KeystrokeEvent(
                session_id=session_id,
                timestamp=last_key_time,
                key_code=key_code,
                event_type='down'
            ))
            
            # Key up (after short duration)
            key_hold = random.uniform(0.05, 0.15)
            events.append(KeystrokeEvent(
                session_id=session_id,
                timestamp=last_key_time + key_hold,
                key_code=key_code,
                event_type='up'
            ))
            
            last_key_time += iki
            current_time = last_key_time
        
        return events
    
    def generate_session(self, user: SyntheticUser, num_intervals: int = 5,
                        start_time: datetime = None) -> Session:
        """
        Generate a complete synthetic study session
        
        Args:
            user: Synthetic user profile
            num_intervals: Number of work-break intervals
            start_time: Session start time (default: now)
        
        Returns:
            Session object
        """
        if start_time is None:
            start_time = datetime.utcnow()
        
        session_id = f"session_{random.randint(10000, 99999)}"
        
        # Create session
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            start_time=start_time,
            chronotype=user.chronotype,
            task_type=random.choice(['writing', 'coding', 'reading', 'other'])
        )
        self.db_session.add(session)
        self.db_session.commit()
        
        current_time = start_time.timestamp()
        cognitive_load = user.cognitive_load_base
        
        for epoch in range(num_intervals):
            # Work interval
            work_interval = random.choice(WORK_INTERVALS)
            work_duration = work_interval / 60.0  # Convert to hours for calculation
            
            # Typing speed decreases with cognitive load
            typing_speed = user.typing_speed_base * (1.0 - cognitive_load * 0.3)
            
            # Generate keystroke events for work interval
            keystrokes = self.generate_keystroke_events(
                session_id, work_interval, typing_speed, cognitive_load
            )
            
            # Save keystroke events
            for event in keystrokes:
                db_event = KeystrokeEvent(
                    session_id=session_id,
                    timestamp=event.timestamp,
                    key_code=event.key_code,
                    event_type=event.event_type
                )
                self.db_session.add(db_event)
            
            # Cognitive load increases during work
            cognitive_load = min(1.0, cognitive_load + random.uniform(0.1, 0.2))
            
            # Create context vector
            context = ContextVector(
                session_id=session_id,
                timestamp=datetime.fromtimestamp(current_time),
                mean_iki=random.uniform(0.1, 0.3),
                std_iki=random.uniform(0.05, 0.15),
                typing_speed=typing_speed,
                correction_ratio=random.uniform(0.05, 0.15),
                pause_count=random.randint(2, 8),
                session_duration=work_interval,
                time_of_day=0 if start_time.hour < 12 else (1 if start_time.hour < 18 else 2),
                cognitive_load=cognitive_load
            )
            self.db_session.add(context)
            
            # Create action
            break_duration = random.choice(BREAK_DURATIONS)
            action = Action(
                session_id=session_id,
                epoch=epoch,
                work_interval=work_interval,
                break_duration=break_duration,
                context_vector_id=context.vector_id,
                bandit_algorithm='LinUCB',
                safety_override=False
            )
            self.db_session.add(action)
            
            # Compute reward (higher if action matches user's optimal)
            if work_interval == user.optimal_work_interval and break_duration == user.optimal_break_duration:
                base_reward = random.uniform(0.7, 0.9)
            else:
                base_reward = random.uniform(0.3, 0.6)
            
            # Reward decreases with high cognitive load
            reward_adjustment = 1.0 - (cognitive_load - 0.5) * 0.5
            final_reward = base_reward * reward_adjustment
            final_reward = max(0.0, min(1.0, final_reward))
            
            # Create reward
            reward = Reward(
                action_id=action.action_id,
                immediate_reward=final_reward,
                delayed_reward=final_reward + random.uniform(-0.1, 0.1),
                final_reward=final_reward,
                r_progress=random.uniform(0.4, 0.8),
                r_relief=random.uniform(0.2, 0.6)
            )
            self.db_session.add(reward)
            
            # Cognitive load decreases after break
            cognitive_load = max(0.2, cognitive_load - (break_duration / 12.0) * 0.3)
            
            # Update time
            current_time += (work_interval + break_duration) * 60
            
            # Add micro-EMA occasionally
            if random.random() < 0.3:  # 30% chance
                ema = MicroEMA(
                    session_id=session_id,
                    timestamp=datetime.fromtimestamp(current_time),
                    fatigue_level=random.randint(1, 5),
                    focus_level=random.randint(1, 5),
                    satisfaction=random.randint(1, 5)
                )
                self.db_session.add(ema)
        
        # End session
        session.end_time = datetime.fromtimestamp(current_time)
        self.db_session.commit()
        
        return session
    
    def generate_multiple_users(self, num_users: int = 10, sessions_per_user: int = 5) -> List[str]:
        """
        Generate synthetic data for multiple users
        
        Args:
            num_users: Number of users to generate
            sessions_per_user: Number of sessions per user
        
        Returns:
            List of user IDs
        """
        user_ids = []
        
        for i in range(num_users):
            user = self.generate_user_profile()
            user_ids.append(user.user_id)
            
            print(f"Generating data for user {user.user_id}...")
            
            for j in range(sessions_per_user):
                # Vary start times
                days_ago = random.randint(0, 30)
                start_time = datetime.utcnow() - timedelta(days=days_ago)
                start_time = start_time.replace(
                    hour=random.randint(6, 22),
                    minute=random.randint(0, 59)
                )
                
                self.generate_session(user, num_intervals=random.randint(3, 8), start_time=start_time)
            
            print(f"  Generated {sessions_per_user} sessions")
        
        return user_ids
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'db_session'):
            self.db_session.close()


def generate_test_data(num_users: int = 5, sessions_per_user: int = 3):
    """
    Convenience function to generate test data
    
    Args:
        num_users: Number of synthetic users
        sessions_per_user: Sessions per user
    """
    print("Generating synthetic test data...")
    print("=" * 50)
    
    generator = SyntheticDataGenerator()
    user_ids = generator.generate_multiple_users(num_users, sessions_per_user)
    
    print("=" * 50)
    print(f"Generated data for {len(user_ids)} users")
    print(f"Total sessions: {len(user_ids) * sessions_per_user}")
    print("\nUser IDs:")
    for uid in user_ids:
        print(f"  - {uid}")
    
    return user_ids


if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Generate test data
    generate_test_data(num_users=5, sessions_per_user=3)

