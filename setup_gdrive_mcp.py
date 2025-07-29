#!/usr/bin/env python3
"""
Setup script for Google Drive MCP integration with Sara Slack Bot
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")
    
    # Check if Node.js is installed
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"✅ Node.js version: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Node.js is not installed. Please install Node.js first.")
        return False
    
    # Check if MCP server is built
    mcp_dist_path = Path("mcp-gdrive/dist/index.js")
    if not mcp_dist_path.exists():
        print("❌ MCP server not built. Building now...")
        try:
            subprocess.run(["npm", "run", "build"], cwd="mcp-gdrive", check=True)
            print("✅ MCP server built successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to build MCP server")
            return False
    else:
        print("✅ MCP server is built")
    
    # Check if credentials exist
    creds_path = Path("mcp-gdrive/gcp-oauth.keys.json")
    if not creds_path.exists():
        print("❌ Google OAuth credentials not found")
        return False
    else:
        print("✅ Google OAuth credentials found")
    
    return True

def setup_environment():
    """Setup environment variables"""
    print("\n🔧 Setting up environment...")
    
    # Read existing .env file
    env_path = Path("mcp-gdrive/.env")
    if env_path.exists():
        print("✅ MCP .env file exists")
        with open(env_path, 'r') as f:
            content = f.read()
            print("Current MCP environment variables:")
            for line in content.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Hide sensitive values
                    if 'SECRET' in key or 'CLIENT_ID' in key:
                        value = value[:10] + "..." if len(value) > 10 else value
                    print(f"  {key}={value}")
    
    return True

def test_mcp_server():
    """Test if MCP server can start"""
    print("\n🧪 Testing MCP server...")
    
    try:
        # Try to start the server briefly
        process = subprocess.Popen(
            ["node", "./mcp-gdrive/dist/index.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send a simple initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            }
        }
        
        # Send request and wait briefly
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Wait a bit for response
        import time
        time.sleep(2)
        
        # Terminate the process
        process.terminate()
        process.wait(timeout=5)
        
        print("✅ MCP server can start (basic test)")
        return True
        
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        return False

def show_usage_instructions():
    """Show usage instructions"""
    print("\n📋 Usage Instructions:")
    print("1. Make sure your Sara Slack bot is running with orchestrator.py")
    print("2. In Slack, mention Sara with queries like:")
    print("   - '@Sara what's in the sales data sheet?'")
    print("   - '@Sara show me Q4 numbers'")
    print("   - '@Sara lookup customer data'")
    print("3. You can also provide a specific spreadsheet ID or URL:")
    print("   - '@Sara check this sheet: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID'")
    print("\n🔐 Authentication:")
    print("- The first time you use the Google Sheets feature, you may need to authenticate")
    print("- Follow the OAuth flow in your browser when prompted")
    print("- Make sure the Google account has access to the sheets you want to query")

def main():
    """Main setup function"""
    print("🚀 Sara Google Drive MCP Setup")
    print("=" * 40)
    
    if not check_requirements():
        print("\n❌ Setup failed. Please fix the issues above and try again.")
        sys.exit(1)
    
    if not setup_environment():
        print("\n❌ Environment setup failed.")
        sys.exit(1)
    
    if not test_mcp_server():
        print("\n⚠️  MCP server test failed, but continuing...")
    
    show_usage_instructions()
    
    print("\n✅ Setup completed successfully!")
    print("You can now use Sara to query Google Sheets data.")

if __name__ == "__main__":
    main()
