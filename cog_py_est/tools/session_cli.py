"""CLI tool for session management."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from ..config import AppConfig
from ..session_manager import SessionManager


async def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Session Management CLI")
    parser.add_argument("--config", type=Path, help="Configuration file path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start session
    start_parser = subparsers.add_parser("start", help="Start a new session")
    start_parser.add_argument("--load", type=float, required=True, help="Initial cognitive load")
    start_parser.add_argument("--notes", help="Session notes")
    start_parser.add_argument("--tags", nargs="*", help="Session tags")
    
    # End session
    end_parser = subparsers.add_parser("end", help="End current session")
    end_parser.add_argument("--load", type=float, required=True, help="Final cognitive load")
    end_parser.add_argument("--success", type=float, help="Success score (0-1)")
    end_parser.add_argument("--productivity", type=int, choices=range(1, 6), help="Productivity rating (1-5)")
    end_parser.add_argument("--difficulty", type=int, choices=range(1, 6), help="Difficulty rating (1-5)")
    end_parser.add_argument("--satisfaction", type=int, choices=range(1, 6), help="Satisfaction rating (1-5)")
    end_parser.add_argument("--notes", help="Session notes")
    
    # List sessions
    list_parser = subparsers.add_parser("list", help="List sessions")
    list_parser.add_argument("--limit", type=int, default=10, help="Number of sessions to show")
    list_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    list_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    
    # Show session
    show_parser = subparsers.add_parser("show", help="Show session details")
    show_parser.add_argument("uuid", help="Session UUID")
    
    # Current session
    subparsers.add_parser("current", help="Show current session")
    
    # Delete session
    delete_parser = subparsers.add_parser("delete", help="Delete a session")
    delete_parser.add_argument("uuid", help="Session UUID")
    delete_parser.add_argument("--confirm", action="store_true", help="Confirm deletion")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    config = AppConfig.load(args.config)
    session_manager = SessionManager(config.session_tracking.storage_path)
    await session_manager.initialize()
    
    try:
        if args.command == "start":
            session_uuid = await session_manager.start_session(
                cognitive_load=args.load,
                notes=args.notes,
                tags=args.tags
            )
            print(f"Session started: {session_uuid}")
            
        elif args.command == "end":
            session_uuid = await session_manager.end_session(
                cognitive_load=args.load,
                success_score=args.success,
                productivity_rating=args.productivity,
                difficulty_rating=args.difficulty,
                satisfaction_rating=args.satisfaction,
                notes=args.notes
            )
            if session_uuid:
                print(f"Session ended: {session_uuid}")
            else:
                print("No active session to end")
                
        elif args.command == "list":
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None
            
            sessions = await session_manager.list_sessions(
                limit=args.limit,
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"\nFound {len(sessions)} sessions:")
            print("-" * 80)
            for session in sessions:
                start_time = datetime.fromisoformat(session['start_time'])
                length = session.get('session_length_seconds', 0)
                avg_load = session.get('average_cognitive_load', 0)
                
                print(f"UUID: {session['session_uuid']}")
                print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Length: {length/60:.1f} minutes")
                print(f"Avg Load: {avg_load:.2f}")
                if session['notes']:
                    print(f"Notes: {session['notes']}")
                print("-" * 80)
                
        elif args.command == "show":
            summary = await session_manager.get_session_summary(args.uuid)
            if not summary:
                print(f"Session {args.uuid} not found")
                return
            
            session = summary['session']
            events = summary['events']
            milestones = summary['milestones']
            
            print(f"\nSession Details: {session['session_uuid']}")
            print("=" * 50)
            
            start_time = datetime.fromisoformat(session['start_time'])
            end_time = datetime.fromisoformat(session['end_time']) if session['end_time'] else None
            
            print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if end_time:
                print(f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Length: {session['session_length_seconds']/60:.1f} minutes")
            
            print(f"Start Load: {session['cognitive_load_at_start']:.2f}")
            print(f"End Load: {session['cognitive_load_at_end']:.2f}")
            print(f"Average Load: {session['average_cognitive_load']:.2f}")
            print(f"Peak Load: {session['peak_cognitive_load']:.2f}")
            
            if session['success_score'] is not None:
                print(f"Success Score: {session['success_score']:.2f}")
            if session['productivity_rating']:
                print(f"Productivity: {session['productivity_rating']}/5")
            if session['difficulty_rating']:
                print(f"Difficulty: {session['difficulty_rating']}/5")
            if session['satisfaction_rating']:
                print(f"Satisfaction: {session['satisfaction_rating']}/5")
            
            if session['notes']:
                print(f"Notes: {session['notes']}")
            if session['tags']:
                print(f"Tags: {', '.join(session['tags'])}")
            
            print(f"\nEvents: {len(events)}")
            for event in events[-5:]:  # Show last 5 events
                timestamp = datetime.fromisoformat(event['timestamp'])
                load = event['cognitive_load'] if event['cognitive_load'] else "N/A"
                print(f"  {timestamp.strftime('%H:%M:%S')} - {event['event_type']} (Load: {load})")
            
            print(f"\nMilestones: {len(milestones)}")
            for milestone in milestones:
                timestamp = datetime.fromisoformat(milestone['timestamp'])
                load = milestone['cognitive_load'] if milestone['cognitive_load'] else "N/A"
                print(f"  {timestamp.strftime('%H:%M:%S')} - {milestone['milestone_type']}")
                if milestone['description']:
                    print(f"    {milestone['description']}")
                print(f"    Load: {load}")
                
        elif args.command == "current":
            current = await session_manager.get_current_session_info()
            if current:
                start_time = datetime.fromisoformat(current['start_time'])
                print(f"Current Session: {current['session_uuid']}")
                print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Initial Load: {current['cognitive_load_at_start']:.2f}")
                if current['notes']:
                    print(f"Notes: {current['notes']}")
            else:
                print("No active session")
                
        elif args.command == "delete":
            if not args.confirm:
                print("Please use --confirm to delete the session")
                return
            
            await session_manager.delete_session(args.uuid)
            print(f"Session {args.uuid} deleted")
            
    finally:
        await session_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
