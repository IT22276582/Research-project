"""Inter-keystroke Interval (IKI) calculation"""
import numpy as np
from typing import List, Tuple
from config.config import IKI_MIN, IKI_MAX


def compute_iki(keystroke_events: List[Tuple[float, str]]) -> List[float]:
    """
    Compute Inter-Keystroke Intervals (IKI) from keystroke events
    
    Args:
        keystroke_events: List of (timestamp, event_type) tuples
                          event_type is 'down' or 'up'
    
    Returns:
        List of IKI values in seconds
    """
    intervals = []
    
    # Track last key up time
    last_up_time = None
    
    for timestamp, event_type in keystroke_events:
        if event_type == 'up':
            last_up_time = timestamp
        elif event_type == 'down' and last_up_time is not None:
            iki = timestamp - last_up_time
            # Filter outliers
            if IKI_MIN < iki < IKI_MAX:
                intervals.append(iki)
            last_up_time = None
    
    return intervals


def compute_iki_statistics(iki_list: List[float]) -> dict:
    """
    Compute IKI statistics
    
    Args:
        iki_list: List of IKI values
    
    Returns:
        Dictionary with mean_iki, std_iki, median_iki, min_iki, max_iki
    """
    if not iki_list:
        return {
            'mean_iki': 0.0,
            'std_iki': 0.0,
            'median_iki': 0.0,
            'min_iki': 0.0,
            'max_iki': 0.0
        }
    
    iki_array = np.array(iki_list)
    return {
        'mean_iki': float(np.mean(iki_array)),
        'std_iki': float(np.std(iki_array)),
        'median_iki': float(np.median(iki_array)),
        'min_iki': float(np.min(iki_array)),
        'max_iki': float(np.max(iki_array))
    }

