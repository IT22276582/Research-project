"""Tests for feature extraction"""
import pytest
from src.feature_extractor.iki_calculator import compute_iki, compute_iki_statistics


def test_iki_computation():
    """Test IKI computation"""
    import time
    base_time = time.time()
    
    # Simulate keystroke events
    events = [
        (base_time, 'down'),
        (base_time + 0.1, 'up'),
        (base_time + 0.2, 'down'),
        (base_time + 0.3, 'up'),
    ]
    
    iki_list = compute_iki(events)
    assert len(iki_list) > 0
    
    stats = compute_iki_statistics(iki_list)
    assert 'mean_iki' in stats
    assert 'std_iki' in stats
    assert stats['mean_iki'] > 0

