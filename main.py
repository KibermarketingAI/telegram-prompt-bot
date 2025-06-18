
#!/usr/bin/env python3
"""
Main application entry point
"""

from app.bot import main as bot_main

def main():
    print("Starting Telegram bot...")
    bot_main()
    
if __name__ == "__main__":
    main()
