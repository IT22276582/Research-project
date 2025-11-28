"""Run the Adaptive Scheduler API server"""
from src.api.app import app
from src.database.models import init_db
from config.config import API_HOST, API_PORT

if __name__ == "__main__":
    # Initialize database
    print("Initializing database...")
    init_db()
    print("Database initialized!")
    
    # Start server
    print(f"Starting API server on {API_HOST}:{API_PORT}...")
    app.run(host=API_HOST, port=API_PORT, debug=True)

