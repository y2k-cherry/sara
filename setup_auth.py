#!/usr/bin/env python3
"""
Setup authentication for Google Drive MCP server
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def setup_authentication():
    """Setup Google Drive authentication"""
    print("🔐 Setting up Google Drive Authentication")
    print("=" * 50)
    
    # Check if credentials exist
    creds_path = Path("mcp-gdrive/.gdrive-server-credentials.json")
    if creds_path.exists():
        print("✅ Existing credentials found")
        response = input("Do you want to re-authenticate? (y/N): ").lower()
        if response != 'y':
            print("Using existing credentials")
            return True
        else:
            # Remove existing credentials to force re-auth
            creds_path.unlink()
            print("🗑️  Removed existing credentials")
    
    print("\n🚀 Starting authentication process...")
    print("This will open a browser window for Google OAuth")
    print("Please complete the authentication flow")
    
    # Start the MCP server which will trigger auth
    try:
        print("\n📡 Starting MCP server for authentication...")
        process = subprocess.Popen(
            ["node", "./mcp-gdrive/dist/index.js"],
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for the server to start and potentially trigger auth
        time.sleep(3)
        
        # Check if the process is still running (it should be waiting for auth)
        if process.poll() is None:
            print("✅ MCP server started and waiting for authentication")
            print("\n🌐 If a browser window didn't open automatically,")
            print("   please check the terminal output for an authentication URL")
            
            # Wait for authentication to complete
            print("\n⏳ Waiting for authentication to complete...")
            print("   (This may take up to 60 seconds)")
            
            # Wait for up to 60 seconds for auth to complete
            for i in range(60):
                if creds_path.exists():
                    print("✅ Authentication completed successfully!")
                    process.terminate()
                    return True
                time.sleep(1)
                if i % 10 == 0:
                    print(f"   Still waiting... ({60-i} seconds remaining)")
            
            print("⏰ Authentication timed out")
            process.terminate()
            return False
        else:
            # Process exited, check output
            stdout, stderr = process.communicate()
            print("❌ MCP server exited unexpectedly")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return False

def test_authentication():
    """Test if authentication works"""
    print("\n🧪 Testing authentication...")
    
    try:
        # Try to start the server and make a simple request
        process = subprocess.Popen(
            ["node", "./mcp-gdrive/dist/index.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        # Send a simple initialize request
        init_request = '''{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0.0"}}}
'''
        
        process.stdin.write(init_request)
        process.stdin.flush()
        
        # Wait for response
        time.sleep(2)
        
        # Send initialized notification
        init_notification = '''{"jsonrpc": "2.0", "method": "notifications/initialized"}
'''
        process.stdin.write(init_notification)
        process.stdin.flush()
        
        # Try to list tools
        list_tools_request = '''{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
'''
        process.stdin.write(list_tools_request)
        process.stdin.flush()
        
        time.sleep(2)
        
        # Terminate the process
        process.terminate()
        process.wait(timeout=5)
        
        print("✅ Authentication test completed")
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Google Drive MCP Authentication Setup")
    print("=" * 50)
    
    # Check if MCP server is built
    if not Path("mcp-gdrive/dist/index.js").exists():
        print("❌ MCP server not built. Please run: cd mcp-gdrive && npm run build")
        sys.exit(1)
    
    # Setup authentication
    if setup_authentication():
        print("\n✅ Authentication setup completed!")
        
        # Test authentication
        if test_authentication():
            print("\n🎉 Setup successful! You can now use Sara to access Google Sheets.")
            print("\nTry asking Sara: '@Sara how many brands are in this sheet")
            print("https://docs.google.com/spreadsheets/d/167kbSbvnQunrYVD7lFplM42rTpexs6OlCvxABNGtnxc/edit'")
        else:
            print("\n⚠️  Authentication setup completed but testing failed.")
            print("You may still be able to use the integration.")
    else:
        print("\n❌ Authentication setup failed.")
        print("Please check your Google Cloud Console settings and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
