import pandas as pd
import numpy as np
from mabwiser.mab import MAB, LearningPolicy

np.random.seed(42)

# -------------------------
# 1. Create Dummy Dataset
# -------------------------
n_blocks = 50

df = pd.DataFrame({
    'block_focus': np.random.rand(n_blocks),
    'keystroke_intervals_mean': np.random.normal(200, 50, n_blocks),
    'burstiness': np.random.rand(n_blocks),
    'scroll_rate': np.random.randint(0, 100, n_blocks),
    'idle_time_percent': np.random.rand(n_blocks) * 100,
    'microEMA': np.random.rand(n_blocks),
    'sleep_hours_prev_night': np.random.randint(4, 10, n_blocks),
    'action': np.random.choice(['morning', 'afternoon', 'evening'], n_blocks)
})

df['reward'] = 0.7 * df['block_focus'] + 0.3 * df['microEMA']

context_features = [
    'block_focus', 'keystroke_intervals_mean', 'burstiness',
    'scroll_rate', 'idle_time_percent', 'microEMA', 'sleep_hours_prev_night'
]

arm_mapping = {'morning': 0, 'afternoon': 1, 'evening': 2}
inverse_mapping = {v: k for k, v in arm_mapping.items()}

actions_encoded = df['action'].map(arm_mapping).astype(int)
rewards_array = df['reward'].astype(float).values
context_df = df[context_features].astype(float)

# -------------------------
# 2. Create and Train Bandit
# -------------------------
mab = MAB(
    arms=[0, 1, 2],
    learning_policy=LearningPolicy.LinUCB(alpha=1.25)
)

mab.partial_fit(actions_encoded, rewards_array, context_df)

print("Bandit model initialized and trained.")


# -------------------------
# 3. Predict Function
# -------------------------
def predict_context(context_dict):
    """Accepts a dict and returns prediction label (morning/afternoon/evening)."""
    new_context = pd.DataFrame([context_dict]).astype(float)
    pred_encoded = mab.predict(new_context)  # Remove the [0] since predict returns an int
    return inverse_mapping[pred_encoded]  # Now pred_encoded is the arm index directly
