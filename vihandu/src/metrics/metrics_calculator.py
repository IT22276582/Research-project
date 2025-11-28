"""Metrics computation for adaptive scheduler evaluation"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from src.database.models import Session, Action, Reward, ContextVector, MicroEMA, Metrics, SessionLocal
from config.config import WORK_INTERVALS, BREAK_DURATIONS


@dataclass
class MetricResults:
    """Container for computed metrics"""
    PG: Optional[float] = None  # Personalization Gain
    RPH: Optional[float] = None  # Regret-per-Hour
    AHL: Optional[float] = None  # Adaptation Half-Life
    EOI: Optional[float] = None  # Exploration Overhead Index
    AUC_BUC: Optional[float] = None  # Area Under Break Utility Curve
    CTU: Optional[float] = None  # Counterfactual Targeting Uplift
    SPF_variance: Optional[float] = None  # Stability-Productivity Frontier variance
    SVR: Optional[float] = None  # Safety-Violation Rate


class MetricsCalculator:
    """Computes productivity-specific metrics for adaptive scheduler"""
    
    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize metrics calculator
        
        Args:
            user_id: Optional user ID to filter metrics for specific user
        """
        self.user_id = user_id
        self.db_session = SessionLocal()
    
    def compute_all_metrics(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> MetricResults:
        """
        Compute all metrics
        
        Args:
            time_range: Optional (start_time, end_time) tuple to filter data
        
        Returns:
            MetricResults object with all computed metrics
        """
        results = MetricResults()
        
        try:
            results.PG = self.compute_personalization_gain(time_range)
            results.RPH = self.compute_regret_per_hour(time_range)
            results.AHL = self.compute_adaptation_half_life(time_range)
            results.EOI = self.compute_exploration_overhead_index(time_range)
            results.AUC_BUC = self.compute_auc_buc(time_range)
            results.CTU = self.compute_counterfactual_targeting_uplift(time_range)
            results.SPF_variance = self.compute_spf_variance(time_range)
            results.SVR = self.compute_safety_violation_rate(time_range)
        except Exception as e:
            print(f"Error computing metrics: {e}")
        
        return results
    
    def compute_personalization_gain(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> float:
        """
        Compute Personalization Gain (PG)
        
        PG measures per-user improvement over Pomodoro baseline (25/5 minutes)
        
        Formula: PG_u = (μ_bandit - μ_baseline) / μ_baseline
        """
        # Get user sessions
        sessions = self._get_sessions(time_range)
        if not sessions:
            return 0.0
        
        # Get all actions and rewards for bandit policy
        bandit_rewards = []
        baseline_rewards = []
        
        for session in sessions:
            actions = self.db_session.query(Action).filter_by(session_id=session.session_id).all()
            
            for action in actions:
                reward = self.db_session.query(Reward).filter_by(action_id=action.action_id).first()
                if reward and reward.final_reward is not None:
                    bandit_rewards.append(reward.final_reward)
                    
                    # Simulate Pomodoro baseline (25/5) for same context
                    # Use average reward for 25/5 action as proxy
                    baseline_reward = self._estimate_baseline_reward(session.session_id, action.epoch)
                    if baseline_reward is not None:
                        baseline_rewards.append(baseline_reward)
        
        if not bandit_rewards or not baseline_rewards:
            return 0.0
        
        μ_bandit = np.mean(bandit_rewards)
        μ_baseline = np.mean(baseline_rewards)
        
        if μ_baseline == 0:
            return 0.0
        
        PG = (μ_bandit - μ_baseline) / μ_baseline
        return float(PG)
    
    def compute_regret_per_hour(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> float:
        """
        Compute Regret-per-Hour (RPH)
        
        RPH = (1/H_total) * Σ(r* - r)
        where r* is optimal reward (oracle/hindsight), r is actual reward
        """
        sessions = self._get_sessions(time_range)
        if not sessions:
            return 0.0
        
        total_regret = 0.0
        total_hours = 0.0
        
        for session in sessions:
            actions = self.db_session.query(Action).filter_by(session_id=session.session_id).all()
            
            for action in actions:
                reward = self.db_session.query(Reward).filter_by(action_id=action.action_id).first()
                if reward and reward.final_reward is not None:
                    # Use best fixed policy (Pomodoro 25/5) as proxy for oracle
                    optimal_reward = self._estimate_optimal_reward(action)
                    regret = optimal_reward - reward.final_reward
                    total_regret += max(0, regret)  # Only positive regret
                    
                    # Add work interval hours
                    total_hours += action.work_interval / 60.0
        
        if total_hours == 0:
            return 0.0
        
        RPH = total_regret / total_hours
        return float(RPH)
    
    def compute_adaptation_half_life(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> float:
        """
        Compute Adaptation Half-Life (AHL)
        
        AHL = min {t : R(t) ≥ R_pre + 0.5 * (R_post - R_pre)}
        Time to recover half of performance gap after context shift
        """
        sessions = self._get_sessions(time_range)
        if not sessions or len(sessions) < 2:
            return float('inf')
        
        # Detect context shifts (simplified: use session boundaries or reward drops)
        rewards_by_epoch = []
        for session in sessions:
            actions = self.db_session.query(Action).filter_by(
                session_id=session.session_id
            ).order_by(Action.epoch).all()
            
            for action in actions:
                reward = self.db_session.query(Reward).filter_by(action_id=action.action_id).first()
                if reward and reward.final_reward is not None:
                    rewards_by_epoch.append(reward.final_reward)
        
        if len(rewards_by_epoch) < 20:
            return float('inf')
        
        # Detect context shift (simplified: significant drop in rewards)
        window_size = 10
        for i in range(window_size, len(rewards_by_epoch) - window_size):
            pre_window = rewards_by_epoch[i-window_size:i]
            post_window = rewards_by_epoch[i+window_size:i+2*window_size]
            
            R_pre = np.mean(pre_window)
            R_post = np.mean(post_window)
            
            # If significant drop, compute AHL
            if R_post < R_pre - 0.2:  # Threshold for context shift
                # Find half-life
                target = R_pre + 0.5 * (R_post - R_pre)
                
                for j in range(i, min(i + 30, len(rewards_by_epoch))):
                    if rewards_by_epoch[j] >= target:
                        AHL = j - i
                        return float(AHL)
        
        return float('inf')  # No context shift detected
    
    def compute_exploration_overhead_index(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> float:
        """
        Compute Exploration Overhead Index (EOI)
        
        EOI = (1/|E|) * Σ(R_exploit - R_explore)
        where E is set of exploration epochs
        """
        sessions = self._get_sessions(time_range)
        if not sessions:
            return 0.0
        
        exploration_rewards = []
        exploitation_rewards = []
        
        for session in sessions:
            actions = self.db_session.query(Action).filter_by(
                session_id=session.session_id
            ).order_by(Action.epoch).all()
            
            for i, action in enumerate(actions):
                reward = self.db_session.query(Reward).filter_by(action_id=action.action_id).first()
                if reward and reward.final_reward is not None:
                    # Classify as exploration if action differs from recent best
                    is_exploration = self._is_exploration_action(action, actions[:i])
                    
                    if is_exploration:
                        exploration_rewards.append(reward.final_reward)
                    else:
                        exploitation_rewards.append(reward.final_reward)
        
        if not exploration_rewards or not exploitation_rewards:
            return 0.0
        
        μ_explore = np.mean(exploration_rewards)
        μ_exploit = np.mean(exploitation_rewards)
        
        EOI = μ_exploit - μ_explore
        return float(max(0, EOI))  # Only positive overhead
    
    def compute_auc_buc(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> float:
        """
        Compute Area Under Break Utility Curve (AUC-BUC)
        
        BUC(b) = E[Δ_load | break_length = b]
        AUC-BUC = ∫[b=3 to 12] BUC(b) db
        """
        sessions = self._get_sessions(time_range)
        if not sessions:
            return 0.0
        
        # Collect break utility data
        break_utilities = {b: [] for b in BREAK_DURATIONS}
        
        for session in sessions:
            actions = self.db_session.query(Action).filter_by(session_id=session.session_id).all()
            
            for action in actions:
                break_duration = action.break_duration
                
                # Get cognitive load change
                context_pre = self._get_context_before_break(action)
                context_post = self._get_context_after_break(action)
                
                if context_pre and context_post:
                    delta_load = context_pre.cognitive_load - context_post.cognitive_load
                    break_utilities[break_duration].append(delta_load)
        
        # Compute BUC for each break length
        BUC = {}
        for b in BREAK_DURATIONS:
            if break_utilities[b]:
                BUC[b] = np.mean(break_utilities[b])
            else:
                BUC[b] = 0.0
        
        # Compute AUC using trapezoidal rule
        sorted_breaks = sorted(BREAK_DURATIONS)
        auc = 0.0
        
        for i in range(len(sorted_breaks) - 1):
            b1, b2 = sorted_breaks[i], sorted_breaks[i + 1]
            auc += (BUC[b1] + BUC[b2]) * (b2 - b1) / 2.0
        
        return float(auc)
    
    def compute_counterfactual_targeting_uplift(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> float:
        """
        Compute Counterfactual Targeting Uplift (CTU)
        
        CTU(x) = E[Y | do(break=1), x] - E[Y | do(break=0), x]
        Uses inverse propensity scoring for estimation
        """
        sessions = self._get_sessions(time_range)
        if not sessions:
            return 0.0
        
        # Collect data for IPS estimation
        outcomes_with_break = []
        outcomes_without_break = []
        
        for session in sessions:
            actions = self.db_session.query(Action).filter_by(session_id=session.session_id).all()
            
            for action in actions:
                reward = self.db_session.query(Reward).filter_by(action_id=action.action_id).first()
                if reward and reward.final_reward is not None:
                    # Estimate propensity (simplified: use bandit confidence)
                    # In practice, would use actual propensity scores from bandit
                    context = self._get_action_context(action)
                    if context:
                        # Simplified: break given if cognitive load > threshold
                        had_break = action.break_duration > 0
                        outcome = reward.final_reward
                        
                        if had_break:
                            outcomes_with_break.append(outcome)
                        else:
                            outcomes_without_break.append(outcome)
        
        if not outcomes_with_break or not outcomes_without_break:
            return 0.0
        
        E_Y_break = np.mean(outcomes_with_break)
        E_Y_no_break = np.mean(outcomes_without_break)
        
        CTU = E_Y_break - E_Y_no_break
        return float(CTU)
    
    def compute_spf_variance(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> float:
        """
        Compute Stability-Productivity Frontier variance (SPF)
        
        SPF variance = Var[R | policy]
        Measures stability of rewards
        """
        sessions = self._get_sessions(time_range)
        if not sessions:
            return 0.0
        
        all_rewards = []
        
        for session in sessions:
            actions = self.db_session.query(Action).filter_by(session_id=session.session_id).all()
            
            for action in actions:
                reward = self.db_session.query(Reward).filter_by(action_id=action.action_id).first()
                if reward and reward.final_reward is not None:
                    all_rewards.append(reward.final_reward)
        
        if len(all_rewards) < 2:
            return 0.0
        
        variance = np.var(all_rewards)
        return float(variance)
    
    def compute_safety_violation_rate(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> float:
        """
        Compute Safety-Violation Rate (SVR)
        
        SVR = (# safety_overrides) / (# total_decisions)
        """
        sessions = self._get_sessions(time_range)
        if not sessions:
            return 0.0
        
        total_decisions = 0
        safety_overrides = 0
        
        for session in sessions:
            actions = self.db_session.query(Action).filter_by(session_id=session.session_id).all()
            
            for action in actions:
                total_decisions += 1
                if action.safety_override:
                    safety_overrides += 1
        
        if total_decisions == 0:
            return 0.0
        
        SVR = safety_overrides / total_decisions
        return float(SVR)
    
    # Helper methods
    
    def _get_sessions(self, time_range: Optional[Tuple[datetime, datetime]] = None):
        """Get sessions for user, optionally filtered by time range"""
        query = self.db_session.query(Session)
        
        if self.user_id:
            query = query.filter_by(user_id=self.user_id)
        
        if time_range:
            start_time, end_time = time_range
            query = query.filter(Session.start_time >= start_time, Session.start_time <= end_time)
        
        return query.all()
    
    def _estimate_baseline_reward(self, session_id: str, epoch: int) -> Optional[float]:
        """Estimate reward for Pomodoro baseline (25/5)"""
        # Use average reward for similar contexts with 25/5 action
        similar_actions = self.db_session.query(Action).filter(
            Action.work_interval == 25,
            Action.break_duration == 5
        ).limit(10).all()
        
        rewards = []
        for action in similar_actions:
            reward = self.db_session.query(Reward).filter_by(action_id=action.action_id).first()
            if reward and reward.final_reward is not None:
                rewards.append(reward.final_reward)
        
        return np.mean(rewards) if rewards else None
    
    def _estimate_optimal_reward(self, action: Action) -> float:
        """Estimate optimal reward (proxy: best fixed policy)"""
        # Use best performing action as proxy
        all_actions = self.db_session.query(Action).limit(100).all()
        action_rewards = {}
        
        for a in all_actions:
            reward = self.db_session.query(Reward).filter_by(action_id=a.action_id).first()
            if reward and reward.final_reward is not None:
                key = (a.work_interval, a.break_duration)
                if key not in action_rewards:
                    action_rewards[key] = []
                action_rewards[key].append(reward.final_reward)
        
        if action_rewards:
            best_action = max(action_rewards.items(), key=lambda x: np.mean(x[1]))
            return np.mean(best_action[1])
        
        return 0.5  # Default
    
    def _is_exploration_action(self, action: Action, previous_actions: List[Action]) -> bool:
        """Determine if action is exploration (differs from recent best)"""
        if not previous_actions:
            return True  # First action is exploration
        
        # Find most common action in recent history
        recent = previous_actions[-10:] if len(previous_actions) >= 10 else previous_actions
        action_counts = {}
        
        for a in recent:
            key = (a.work_interval, a.break_duration)
            action_counts[key] = action_counts.get(key, 0) + 1
        
        if action_counts:
            best_action = max(action_counts.items(), key=lambda x: x[1])[0]
            current_action = (action.work_interval, action.break_duration)
            return current_action != best_action
        
        return True
    
    def _get_context_before_break(self, action: Action) -> Optional[ContextVector]:
        """Get context vector before break"""
        # Get context from previous action or same epoch
        context = self.db_session.query(ContextVector).filter_by(
            session_id=action.session_id
        ).order_by(ContextVector.timestamp.desc()).first()
        
        return context
    
    def _get_context_after_break(self, action: Action) -> Optional[ContextVector]:
        """Get context vector after break"""
        # Get context from next action
        next_action = self.db_session.query(Action).filter(
            Action.session_id == action.session_id,
            Action.epoch > action.epoch
        ).order_by(Action.epoch).first()
        
        if next_action and next_action.context_vector_id:
            return self.db_session.query(ContextVector).filter_by(
                vector_id=next_action.context_vector_id
            ).first()
        
        return None
    
    def _get_action_context(self, action: Action) -> Optional[ContextVector]:
        """Get context vector for action"""
        if action.context_vector_id:
            return self.db_session.query(ContextVector).filter_by(
                vector_id=action.context_vector_id
            ).first()
        return None
    
    def save_metrics_to_db(self, metrics: MetricResults, user_id: str):
        """Save computed metrics to database"""
        db_metrics = Metrics(
            user_id=user_id,
            date=datetime.utcnow(),
            PG=metrics.PG,
            RPH=metrics.RPH,
            AHL=metrics.AHL,
            EOI=metrics.EOI,
            AUC_BUC=metrics.AUC_BUC,
            CTU=metrics.CTU,
            SPF_variance=metrics.SPF_variance,
            SVR=metrics.SVR
        )
        self.db_session.add(db_metrics)
        self.db_session.commit()
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'db_session'):
            self.db_session.close()

