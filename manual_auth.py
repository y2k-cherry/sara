#!/usr/bin/env python3
"""
Manual authentication setup for Google Drive MCP
"""

import os
import json
import webbrowser
from pathlib import Path
from urllib.parse import urlencode
import http.server
import socketserver
import threading
import time

# OAuth configuration
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "your-client-id-here")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "your-client-secret-here")
REDIRECT_URI = "http://localhost:3001/oauth2callback"
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets"
]

class AuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/oauth2callback'):
            # Extract authorization code from URL
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' in query_params:
                auth_code = query_params['code'][0]
                print(f"✅ Received authorization code: {auth_code[:20]}...")
                
                # Exchange code for tokens
                self.exchange_code_for_tokens(auth_code)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <body>
                <h1>Authentication Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
                ''')
            else:
                # Send error response
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <body>
                <h1>Authentication Failed</h1>
                <p>No authorization code received.</p>
                </body>
                </html>
                ''')
    
    def exchange_code_for_tokens(self, auth_code):
        """Exchange authorization code for access and refresh tokens"""
        import requests
        
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI
        }
        
        try:
            response = requests.post(token_url, data=token_data)
            if response.status_code == 200:
                tokens = response.json()
                
                # Save tokens to the credentials file
                creds_path = Path("mcp-gdrive/.gdrive-server-credentials.json")
                creds_path.parent.mkdir(exist_ok=True)
                
                # Format tokens for the MCP server
                credentials = {
                    "access_token": tokens.get("access_token"),
                    "refresh_token": tokens.get("refresh_token"),
                    "scope": " ".join(SCOPES),
                    "token_type": tokens.get("token_type", "Bearer"),
                    "expiry_date": int(time.time() * 1000) + (tokens.get("expires_in", 3600) * 1000)
                }
                
                with open(creds_path, 'w') as f:
                    json.dump(credentials, f, indent=2)
                
                print(f"✅ Tokens saved to {creds_path}")
                global auth_success
                auth_success = True
            else:
                print(f"❌ Token exchange failed: {response.status_code} {response.text}")
        except Exception as e:
            print(f"❌ Error exchanging tokens: {e}")
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_auth_server():
    """Start the OAuth callback server"""
    global httpd
    httpd = socketserver.TCPServer(("", 3001), AuthHandler)
    print("🌐 Started OAuth callback server on http://localhost:3001")
    httpd.serve_forever()

def main():
    """Main authentication function"""
    print("🔐 Manual Google Drive Authentication")
    print("=" * 50)
    
    # Check if credentials already exist
    creds_path = Path("mcp-gdrive/.gdrive-server-credentials.json")
    if creds_path.exists():
        print("✅ Existing credentials found")
        response = input("Do you want to re-authenticate? (y/N): ").lower()
        if response != 'y':
            print("Using existing credentials")
            return
        else:
            creds_path.unlink()
            print("🗑️  Removed existing credentials")
    
    # Start the callback server in a separate thread
    global auth_success, httpd
    auth_success = False
    
    server_thread = threading.Thread(target=start_auth_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    
    # Build the authorization URL
    auth_params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(SCOPES),
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(auth_params)}"
    
    print("\n🚀 Opening browser for authentication...")
    print(f"If the browser doesn't open automatically, visit this URL:")
    print(f"{auth_url}")
    print()
    
    # Open browser
    webbrowser.open(auth_url)
    
    # Wait for authentication to complete
    print("⏳ Waiting for authentication to complete...")
    print("   Please complete the OAuth flow in your browser")
    
    # Wait up to 120 seconds for authentication
    for i in range(120):
        if auth_success:
            print("✅ Authentication completed successfully!")
            break
        time.sleep(1)
        if i % 20 == 0 and i > 0:
            print(f"   Still waiting... ({120-i} seconds remaining)")
    
    # Stop the server
    if 'httpd' in globals():
        httpd.shutdown()
    
    if auth_success:
        print("\n🎉 Setup successful! You can now use Sara to access Google Sheets.")
        print("\nTest with: python3 test_specific_sheet.py")
    else:
        print("\n❌ Authentication timed out or failed.")
        print("Please try again or check your Google Cloud Console settings.")

if __name__ == "__main__":
    main()
