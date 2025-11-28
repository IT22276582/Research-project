"""Generate synthetic test data for the Adaptive Scheduler"""
from src.data_generation.synthetic_data import generate_test_data
from src.database.models import init_db

if __name__ == "__main__":
    print("=" * 60)
    print("Adaptive Scheduler - Synthetic Data Generator")
    print("=" * 60)
    print()
    print("This will generate synthetic user sessions for testing.")
    print("The data includes:")
    print("  - Keystroke events (privacy-preserving)")
    print("  - Context vectors (features)")
    print("  - Actions (work/break intervals)")
    print("  - Rewards")
    print("  - Micro-EMA feedback")
    print()
    
    # Initialize database
    print("Initializing database...")
    init_db()
    print("Database ready!")
    print()
    
    # Get parameters
    try:
        num_users = int(input("Number of users to generate (default: 5): ") or "5")
        sessions_per_user = int(input("Sessions per user (default: 3): ") or "3")
    except ValueError:
        print("Using defaults: 5 users, 3 sessions each")
        num_users = 5
        sessions_per_user = 3
    
    print()
    print("Generating data...")
    print()
    
    # Generate data
    user_ids = generate_test_data(num_users, sessions_per_user)
    
    print()
    print("=" * 60)
    print("Data generation complete!")
    print("=" * 60)
    print()
    print("You can now:")
    print("  1. Test the API with these user IDs")
    print("  2. Compute metrics: GET /api/metrics?user_id=<user_id>")
    print("  3. Use for algorithm evaluation")
    print()

