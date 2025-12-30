# Yuvidu - Running Guide

## Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install Python dependencies:
   ```bash
   pip install fastapi uvicorn
   ```

3. Start the backend server:
   ```bash
   uvicorn server:app --reload
   ```
   - The API will be available at: http://localhost:8000
   - API documentation: http://localhost:8000/docs

## Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```
   - This will start both the React development server and Electron app
   - The app should open automatically in a new window

## Development Workflow

1. Keep the backend server running in one terminal
2. Keep the frontend server running in another terminal
3. Make changes to the code and they will hot-reload automatically

## Available Scripts

### Backend
- `uvicorn server:app --reload` - Start development server with auto-reload

### Frontend
- `npm run dev` - Start development server and Electron
- `npm run build` - Build for production
- `npm run lint` - Run linter
- `npm run dist:win` - Build Windows executable
- `npm run dist:mac` - Build macOS application
- `npm run dist:linux` - Build Linux application

## Environment Variables

Create a `.env` file in the frontend directory if you need to configure environment-specific settings.

## Troubleshooting

- If you get port conflicts, check which process is using the port and terminate it
- Make sure all dependencies are installed correctly
- Check the console for any error messages