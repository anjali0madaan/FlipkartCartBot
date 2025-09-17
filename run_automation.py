#!/usr/bin/env python3
"""
Flipkart iPhone Automation Launcher
This script provides a simple interface to run the Flipkart automation.
"""

import sys
import json
import argparse
import os
from flipkart_automation import FlipkartAutomation
from session_persistence import FlipkartSessionManager

def main():
    parser = argparse.ArgumentParser(description='Flipkart iPhone Automation Tool with Session Persistence')
    parser.add_argument('--yes', '-y', action='store_true', 
                       help='Skip confirmation prompt and run automation')
    parser.add_argument('--config', '-c', default='config.json',
                       help='Configuration file path (default: config.json)')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode (override config)')
    
    # Session management commands
    parser.add_argument('--setup-session', action='store_true',
                       help='Setup a new persistent login session')
    parser.add_argument('--use-session', type=str,
                       help='Use existing session (email/mobile identifier)')
    parser.add_argument('--list-sessions', action='store_true',
                       help='List all available sessions')
    parser.add_argument('--delete-session', type=str,
                       help='Delete a specific session (email/mobile identifier)')
    
    args = parser.parse_args()
    
    # Handle session management commands first
    if args.setup_session or args.list_sessions or args.delete_session:
        session_manager = FlipkartSessionManager()
        
        if args.setup_session:
            print("🔐 Setting up new Flipkart login session...")
            user_id = session_manager.setup_session_login()
            if user_id:
                print(f"\n✅ Session setup completed for {user_id}")
                print("You can now use this session with: --use-session " + user_id)
            else:
                print("\n❌ Session setup failed")
            return
        
        if args.list_sessions:
            sessions = session_manager.list_available_sessions()
            if sessions:
                print("\n📋 Available Sessions:")
                print("-" * 60)
                for session in sessions:
                    status = "✅ Valid" if session['valid'] else "❌ Invalid"
                    print(f"User: {session['user']}")
                    print(f"Created: {session['created']}")
                    print(f"Last Used: {session['last_used']}")
                    print(f"Status: {status}")
                    print("-" * 60)
            else:
                print("📋 No saved sessions found")
                print("Use --setup-session to create a new session")
            return
        
        if args.delete_session:
            success = session_manager.delete_session(args.delete_session)
            if success:
                print(f"✅ Session deleted for {args.delete_session}")
            else:
                print(f"❌ Session not found or failed to delete: {args.delete_session}")
            return
    
    print("🛍️ Flipkart iPhone Automation Tool")
    print("=" * 50)
    
    # Display current configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
        
        # Override headless mode if specified
        if args.headless:
            config['automation_settings']['headless_mode'] = True
        
        print("Current Configuration:")
        print(f"Product: {config['search_settings']['product_name']}")
        print(f"Search Query: {config['search_settings']['search_query']}")
        print(f"Price Range: ₹{config['search_settings']['min_price']:,} - ₹{config['search_settings']['max_price']:,}")
        print(f"Brand Filter: {config.get('filters', {}).get('brand', 'None')}")
        print(f"Sort By: {config.get('filters', {}).get('sort_by', 'price_low_to_high')}")
        print(f"Headless Mode: {config['automation_settings']['headless_mode']}")
        print(f"Max Retries: {config['automation_settings']['max_retries']}")
        print()
        
        # Check for auto-confirmation via environment variable or flag
        auto_confirm = args.yes or os.getenv('AUTO_CONFIRM', '').lower() in ['true', '1', 'yes']
        
        if not auto_confirm:
            response = input("Do you want to run the automation with these settings? (y/n): ")
            if response.lower() != 'y':
                print("Automation cancelled.")
                return
        
        print("🚀 Starting automation...")
        print("Note: This automation should be used responsibly and in compliance with website terms of service.")
        print()
        
        # Run automation with session if specified
        if args.use_session:
            print(f"🔐 Using session: {args.use_session}")
            automation = FlipkartAutomation(args.config, use_session=args.use_session)
        else:
            automation = FlipkartAutomation(args.config)
            
        success = automation.run()
        
        if success:
            print("✅ Automation completed successfully!")
            sys.exit(0)
        else:
            print("❌ Automation completed with errors. Check logs for details.")
            sys.exit(1)
        
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {args.config}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()