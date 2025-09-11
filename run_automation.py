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

def main():
    parser = argparse.ArgumentParser(description='Flipkart iPhone Automation Tool')
    parser.add_argument('--yes', '-y', action='store_true', 
                       help='Skip confirmation prompt and run automation')
    parser.add_argument('--config', '-c', default='config.json',
                       help='Configuration file path (default: config.json)')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode (override config)')
    
    args = parser.parse_args()
    
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
        
        # Run automation
        automation = FlipkartAutomation(args.config)
        success = automation.run_automation()
        
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