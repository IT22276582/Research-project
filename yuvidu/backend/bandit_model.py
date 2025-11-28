import pandas as pd
import numpy as np
from mabwiser.mab import MAB, LearningPolicy

# Load dataset
df2 = pd.read_csv(r"D:\Research-project\yuvidu\backend\large_contextual_bandit_dataset.csv")

# Features used for context
context_features = [
    'block_focus',
    'keystroke_intervals_mean',
    'burstiness',
    'scroll_rate',
    'idle_time_percent',
    'microEMA',
    'sleep_hours_prev_night'
]

# Action mapping
arm_mapping = {'morning': 0, 'afternoon': 1, 'evening': 2}
inverse_mapping = {v: k for k, v in arm_mapping.items()}

# Extract data
actions_encoded = df2['action'].map(arm_mapping).astype(int)
rewards_array = df2['reward'].astype(float).values
context_df = df2[context_features].astype(float)

# Train model
mab = MAB(
    arms=[0, 1, 2],
    learning_policy=LearningPolicy.LinUCB(alpha=1.25)
)

mab.partial_fit(actions_encoded, rewards_array, context_df.values)
print("Bandit model initialized and trained.")

# Compute average context and predict once
avg_context = context_df.mean().values.reshape(1, -1)
best_arm = mab.predict(avg_context)

def predict_context():
    """Returns the best predicted time of day as a string."""
    return inverse_mapping[int(best_arm)]


import numpy as np

def predict_all_percentages():
    """
    Returns predicted percentages for morning/afternoon/evening.
    """
    context = avg_context  # using your average context
    scores = {}
    for arm in mab.arms:
        # LinUCB gives score = theta^T x + alpha * sqrt(x^T A^-1 x)
        theta = mab.learning_policy.theta[arm]
        A_inv = mab.learning_policy.A_inv[arm]
        p = theta.dot(context.T) + mab.learning_policy.alpha * np.sqrt(context.dot(A_inv).dot(context.T))
        scores[arm] = float(p)

    total = sum(scores.values())
    percentages = {inverse_mapping[a]: (scores[a] / total) * 100 for a in scores}
    best_arm = max(scores, key=scores.get)
    return inverse_mapping[best_arm], percentages
