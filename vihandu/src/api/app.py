"""Flask API application for Adaptive Scheduler"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import uuid
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from src.database.models import init_db, get_db, Session, Action, Reward, ContextVector
from src.context_logger.context_logger import ContextLogger
from src.feature_extractor.feature_extractor import FeatureExtractor
from src.bandit_engine.adaptive_scheduler import AdaptiveScheduler
from src.reward_handler.reward_calculator import RewardCalculator, DelayedRewardTracker
from src.api.metrics_endpoint import metrics_bp
from config.config import API_HOST, API_PORT, API_DEBUG

# Get project root for static files
PROJECT_ROOT = Path(__file__).parent.parent.parent
STATIC_DIR = PROJECT_ROOT / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR))
CORS(app)

# Register metrics blueprint
app.register_blueprint(metrics_bp)

# Initialize database
init_db()

# Global state (in production, use proper session management)
active_sessions: Dict[str, Dict] = {}
schedulers: Dict[str, AdaptiveScheduler] = {}
context_loggers: Dict[str, ContextLogger] = {}
feature_extractors: Dict[str, FeatureExtractor] = {}
reward_calculators: Dict[str, RewardCalculator] = {}
delayed_trackers: Dict[str, DelayedRewardTracker] = {}


@app.route('/', methods=['GET'])
def root():
    """Root endpoint - API information"""
    return jsonify({
        'name': 'Adaptive Scheduler API',
        'version': '1.0.0',
        'description': 'Contextual bandit-based adaptive study timer',
        'endpoints': {
            'root': '/',
            'api_base': '/api',
            'health': '/api/health',
            'start_session': '/api/start-session (POST)',
            'get_recommendation': '/api/get-recommendation (GET)',
            'end_interval': '/api/end-interval (POST)',
            'submit_feedback': '/api/submit-feedback (POST)',
            'end_session': '/api/end-session (POST)',
            'metrics': '/api/metrics (GET)'
        },
        'documentation': 'See README.md and GUIDE.md for detailed API documentation'
    }), 200


@app.route('/api', methods=['GET'])
def api_root():
    """API root endpoint - lists all available endpoints"""
    return jsonify({
        'message': 'Adaptive Scheduler API',
        'available_endpoints': [
            {
                'path': '/api/health',
                'method': 'GET',
                'description': 'Health check endpoint'
            },
            {
                'path': '/api/start-session',
                'method': 'POST',
                'description': 'Start a new study session',
                'required_params': ['user_id'],
                'optional_params': ['task_type', 'chronotype', 'algorithm']
            },
            {
                'path': '/api/get-recommendation',
                'method': 'GET',
                'description': 'Get work/break recommendation',
                'required_params': ['session_id']
            },
            {
                'path': '/api/end-interval',
                'method': 'POST',
                'description': 'End a work or break interval and compute reward',
                'required_params': ['session_id', 'interval_type'],
                'optional_params': ['metrics']
            },
            {
                'path': '/api/submit-feedback',
                'method': 'POST',
                'description': 'Submit micro-EMA feedback',
                'required_params': ['session_id', 'fatigue_level', 'focus_level', 'satisfaction']
            },
            {
                'path': '/api/end-session',
                'method': 'POST',
                'description': 'End a study session',
                'required_params': ['session_id']
            },
            {
                'path': '/api/metrics',
                'method': 'GET',
                'description': 'Get computed metrics (PG, RPH, AHL, etc.)',
                'required_params': ['user_id'],
                'optional_params': ['start_date', 'end_date']
            }
        ]
    }), 200


@app.route('/api/start-session', methods=['POST'])
def start_session():
    """Start a new study session"""
    data = request.json
    user_id = data.get('user_id')
    task_type = data.get('task_type', 'other')
    chronotype = data.get('chronotype', 'neutral')
    algorithm = data.get('algorithm', 'LinUCB')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    # Initialize context logger
    context_logger = ContextLogger(user_id, chronotype, task_type)
    session_metadata = context_logger.start_session()
    session_id = session_metadata.session_id
    
    # Initialize feature extractor
    feature_extractor = FeatureExtractor(session_id)
    
    # Initialize scheduler
    scheduler = AdaptiveScheduler(algorithm=algorithm)
    
    # Initialize reward calculator
    reward_calculator = RewardCalculator()
    delayed_tracker = DelayedRewardTracker()
    
    # Store in global state
    active_sessions[session_id] = {
        'user_id': user_id,
        'start_time': session_metadata.start_time.isoformat(),
        'task_type': task_type,
        'chronotype': chronotype,
        'algorithm': algorithm,
        'epoch': 0
    }
    context_loggers[session_id] = context_logger
    feature_extractors[session_id] = feature_extractor
    schedulers[session_id] = scheduler
    reward_calculators[session_id] = reward_calculator
    delayed_trackers[session_id] = delayed_tracker
    
    # Get initial recommendation
    context_features = feature_extractor.extract_features()
    action, metadata = scheduler.get_recommendation(context_features)
    
    # Save initial action to database (epoch 0)
    db = next(get_db())
    initial_action = Action(
        session_id=session_id,
        epoch=0,
        work_interval=action[0],
        break_duration=action[1],
        context_vector_id=None,
        bandit_algorithm=metadata['algorithm'],
        safety_override=metadata['was_overridden'],
        override_reason=metadata.get('override_reason')
    )
    db.add(initial_action)
    db.commit()
    
    return jsonify({
        'session_id': session_id,
        'initial_action': {
            'work_interval': action[0],
            'break_duration': action[1]
        },
        'metadata': metadata
    }), 200


@app.route('/api/get-recommendation', methods=['GET'])
def get_recommendation():
    """Get work/break recommendation"""
    session_id = request.args.get('session_id')
    
    if not session_id or session_id not in active_sessions:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    feature_extractor = feature_extractors[session_id]
    scheduler = schedulers[session_id]
    
    # Extract current context
    context_features = feature_extractor.extract_features()
    feature_extractor.save_features_to_db(context_features)
    
    # Get recommendation
    action, metadata = scheduler.get_recommendation(context_features)
    
    # Log recommendation for debugging
    print(f"[get-recommendation] Session {session_id[:8]}... | Load: {context_features.cognitive_load:.2f} | "
          f"Recommendation: {action[0]}min work, {action[1]}min break")
    
    return jsonify({
        'work_interval': action[0],
        'break_duration': action[1],
        'explanation': metadata.get('override_reason', 
            f'Recommended by {metadata["algorithm"]} based on cognitive load: {metadata["cognitive_load"]:.2f}'),
        'confidence': metadata['confidence'],
        'was_overridden': metadata['was_overridden'],
        'algorithm': metadata.get('algorithm', 'Unknown'),
        'cognitive_load': metadata.get('cognitive_load', 0.5)
    }), 200


@app.route('/api/end-interval', methods=['POST'])
def end_interval():
    """End a work or break interval and compute reward"""
    data = request.json
    session_id = data.get('session_id')
    interval_type = data.get('interval_type')  # 'work' or 'break'
    metrics = data.get('metrics', {})
    
    if not session_id or session_id not in active_sessions:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    if interval_type not in ['work', 'break']:
        return jsonify({'error': 'interval_type must be "work" or "break"'}), 400
    
    session_info = active_sessions[session_id]
    scheduler = schedulers[session_id]
    reward_calculator = reward_calculators[session_id]
    feature_extractor = feature_extractors[session_id]
    delayed_tracker = delayed_trackers[session_id]
    
    # Get last action
    db = next(get_db())
    last_action = db.query(Action).filter_by(
        session_id=session_id
    ).order_by(Action.epoch.desc()).first()
    
    if not last_action:
        return jsonify({'error': 'No action found for session'}), 400
    
    # Extract current context
    context_features = feature_extractor.extract_features()
    
    # Override cognitive load with the one from metrics (more accurate for demo)
    if metrics.get('cognitive_load_post_break') is not None:
        context_features.cognitive_load = metrics['cognitive_load_post_break']
    elif metrics.get('cognitive_load_pre_break') is not None:
        context_features.cognitive_load = metrics['cognitive_load_pre_break']
    
    # Update session duration based on elapsed time
    session_info = active_sessions[session_id]
    from datetime import datetime, timedelta
    start_time = datetime.fromisoformat(session_info['start_time'])
    elapsed_minutes = (datetime.utcnow() - start_time).total_seconds() / 60.0
    context_features.session_duration = elapsed_minutes
    
    # Save updated context features to database (including cognitive load)
    feature_extractor.save_features_to_db(context_features)
    
    # Compute reward
    user_data = {
        'chars_typed': metrics.get('chars_typed', 0),
        'keystrokes': [],  # Would need to fetch from DB
        'cognitive_load_pre_break': metrics.get('cognitive_load_pre_break', 0.5),
        'cognitive_load_post_break': metrics.get('cognitive_load_post_break'),
        'user_reported_improved_focus': metrics.get('improved_focus', False),
        'deep_work_interrupted': metrics.get('deep_work_interrupted', False)
    }
    
    # Log cognitive load for debugging
    print(f"[end-interval] Session {session_id[:8]}... | Load: {context_features.cognitive_load:.2f} | "
          f"Work: {last_action.work_interval}min | Break: {last_action.break_duration}min")
    
    reward_components = reward_calculator.compute_reward(
        last_action.work_interval,
        last_action.break_duration,
        user_data
    )
    
    # Store immediate reward
    epoch_id = f"{session_id}_{session_info['epoch']}"
    delayed_tracker.add_immediate_reward(
        epoch_id,
        reward_components.immediate_reward,
        user_data
    )
    
    # Save reward to database
    reward = Reward(
        action_id=last_action.action_id,
        immediate_reward=reward_components.immediate_reward,
        r_progress=reward_components.r_progress,
        r_relief=reward_components.r_relief,
        final_reward=reward_components.immediate_reward  # Will update with delayed
    )
    db.add(reward)
    db.commit()
    
    # Update bandit (using immediate reward for now)
    scheduler.update(
        (last_action.work_interval, last_action.break_duration),
        context_features,
        reward_components.immediate_reward
    )
    
    # Get next recommendation (using updated context with new cognitive load)
    next_action, next_metadata = scheduler.get_recommendation(context_features)
    
    # Log next recommendation
    print(f"[end-interval] Next recommendation: {next_action[0]}min work, {next_action[1]}min break | "
          f"Load: {context_features.cognitive_load:.2f} | Reward: {reward_components.immediate_reward:.3f}")
    
    # Save next action
    session_info['epoch'] += 1
    next_db_action = Action(
        session_id=session_id,
        epoch=session_info['epoch'],
        work_interval=next_action[0],
        break_duration=next_action[1],
        context_vector_id=None,  # Would link to context vector
        bandit_algorithm=next_metadata['algorithm'],
        safety_override=next_metadata['was_overridden'],
        override_reason=next_metadata.get('override_reason')
    )
    db.add(next_db_action)
    db.commit()
    
    return jsonify({
        'next_action': {
            'work_interval': next_action[0],
            'break_duration': next_action[1]
        },
        'reward_computed': {
            'immediate_reward': reward_components.immediate_reward,
            'r_progress': reward_components.r_progress,
            'r_relief': reward_components.r_relief
        },
        'metadata': next_metadata
    }), 200


@app.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    """Submit micro-EMA feedback"""
    data = request.json
    session_id = data.get('session_id')
    fatigue_level = data.get('fatigue_level')
    focus_level = data.get('focus_level')
    satisfaction = data.get('satisfaction')
    
    if not session_id or session_id not in active_sessions:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    # Save to database
    db = next(get_db())
    from src.database.models import MicroEMA
    
    ema = MicroEMA(
        session_id=session_id,
        fatigue_level=fatigue_level,
        focus_level=focus_level,
        satisfaction=satisfaction
    )
    db.add(ema)
    db.commit()
    
    return jsonify({
        'acknowledged': True,
        'policy_updated': True  # Could trigger policy update here
    }), 200


@app.route('/api/end-session', methods=['POST'])
def end_session():
    """End a study session"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or session_id not in active_sessions:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    # End context logger
    context_logger = context_loggers[session_id]
    session_metadata = context_logger.end_session()
    
    # Update session in database
    db = next(get_db())
    db_session = db.query(Session).filter_by(session_id=session_id).first()
    if db_session:
        db_session.end_time = datetime.utcnow()
        db.commit()
    
    # Cleanup
    del active_sessions[session_id]
    del context_loggers[session_id]
    del feature_extractors[session_id]
    del schedulers[session_id]
    del reward_calculators[session_id]
    del delayed_trackers[session_id]
    
    return jsonify({
        'session_ended': True,
        'duration_minutes': session_metadata.duration_minutes if session_metadata else 0
    }), 200


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'active_sessions': len(active_sessions)}), 200


@app.route('/dashboard')
def dashboard():
    """Serve the dashboard HTML"""
    return send_from_directory(str(STATIC_DIR), 'dashboard.html')


if __name__ == '__main__':
    app.run(host=API_HOST, port=API_PORT, debug=API_DEBUG)

