"""API endpoint for metrics computation"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from src.metrics.metrics_calculator import MetricsCalculator

metrics_bp = Blueprint('metrics', __name__)


@metrics_bp.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Get computed metrics for user"""
    user_id = request.args.get('user_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    # Parse time range
    time_range = None
    if start_date and end_date:
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            time_range = (start, end)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
    
    # Compute metrics
    calculator = MetricsCalculator(user_id=user_id)
    metrics = calculator.compute_all_metrics(time_range=time_range)
    
    # Save to database
    calculator.save_metrics_to_db(metrics, user_id)
    
    # Helper function to convert Infinity to None for JSON serialization
    def sanitize_for_json(value):
        """Convert Infinity/NaN to None for JSON compatibility"""
        if value is None:
            return None
        if isinstance(value, float):
            if value == float('inf') or value == float('-inf'):
                return None
            if value != value:  # NaN check
                return None
        return value
    
    return jsonify({
        'user_id': user_id,
        'metrics': {
            'PG': sanitize_for_json(metrics.PG),
            'RPH': sanitize_for_json(metrics.RPH),
            'AHL': sanitize_for_json(metrics.AHL),
            'EOI': sanitize_for_json(metrics.EOI),
            'AUC_BUC': sanitize_for_json(metrics.AUC_BUC),
            'CTU': sanitize_for_json(metrics.CTU),
            'SPF_variance': sanitize_for_json(metrics.SPF_variance),
            'SVR': sanitize_for_json(metrics.SVR)
        },
        'interpretation': {
            'PG': _interpret_pg(metrics.PG),
            'RPH': _interpret_rph(metrics.RPH),
            'AHL': _interpret_ahl(metrics.AHL),
            'EOI': _interpret_eoi(metrics.EOI),
            'SVR': _interpret_svr(metrics.SVR)
        }
    }), 200


def _interpret_pg(pg: float) -> str:
    """Interpret Personalization Gain"""
    if pg is None:
        return "Not computed"
    if pg > 0.15:
        return f"Excellent personalization ({pg:.1%} improvement over baseline)"
    elif pg > 0.0:
        return f"Good personalization ({pg:.1%} improvement)"
    elif pg > -0.1:
        return f"Neutral ({pg:.1%} change)"
    else:
        return f"Needs improvement ({pg:.1%} worse than baseline)"


def _interpret_rph(rph: float) -> str:
    """Interpret Regret-per-Hour"""
    if rph is None:
        return "Not computed"
    if rph < 0.1:
        return f"Excellent efficiency (RPH: {rph:.3f})"
    elif rph < 0.3:
        return f"Good efficiency (RPH: {rph:.3f})"
    else:
        return f"Needs improvement (RPH: {rph:.3f})"


def _interpret_ahl(ahl: float) -> str:
    """Interpret Adaptation Half-Life"""
    if ahl is None or ahl == float('inf'):
        return "No context shift detected or insufficient data"
    if ahl < 5:
        return f"Fast adaptation ({ahl:.1f} sessions)"
    elif ahl < 10:
        return f"Moderate adaptation ({ahl:.1f} sessions)"
    else:
        return f"Slow adaptation ({ahl:.1f} sessions)"


def _interpret_eoi(eoi: float) -> str:
    """Interpret Exploration Overhead Index"""
    if eoi is None:
        return "Not computed"
    if eoi < 0.1:
        return f"Low exploration cost ({eoi:.1%})"
    elif eoi < 0.3:
        return f"Moderate exploration cost ({eoi:.1%})"
    else:
        return f"High exploration cost ({eoi:.1%})"


def _interpret_svr(svr: float) -> str:
    """Interpret Safety-Violation Rate"""
    if svr is None:
        return "Not computed"
    if svr < 0.05:
        return f"Low safety override rate ({svr:.1%})"
    elif svr < 0.15:
        return f"Moderate safety override rate ({svr:.1%})"
    else:
        return f"High safety override rate ({svr:.1%})"

