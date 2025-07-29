import os
import json
import asyncio
import re
from typing import Optional
from openai import OpenAI
from mcp_client import mcp_client

# Initialize OpenAI client lazily to avoid import-time errors
openai_client = None

def get_openai_client():
    global openai_client
    if openai_client is None:
        try:
            openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            print(f"⚠️  OpenAI client initialization failed in sheets_service: {e}")
            # Try with minimal parameters
            try:
                openai_client = OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    timeout=30.0
                )
            except Exception as e2:
                print(f"⚠️  OpenAI client fallback initialization failed: {e2}")
                raise e2
    return openai_client

class SheetsService:
    def __init__(self):
        self.mcp_initialized = False
        
    async def _ensure_mcp_connection(self):
        """Ensure MCP server is connected"""
        if not self.mcp_initialized:
            success = await mcp_client.start_server()
            if success:
                self.mcp_initialized = True
            return success
        return True
    
    def extract_spreadsheet_id(self, text: str) -> Optional[str]:
        """Extract spreadsheet ID from text (URL or direct ID)"""
        # Pattern for Google Sheets URL
        url_pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(url_pattern, text)
        if match:
            return match.group(1)
        
        # Pattern for direct spreadsheet ID (44 characters, alphanumeric with hyphens and underscores)
        id_pattern = r'\b([a-zA-Z0-9-_]{44})\b'
        match = re.search(id_pattern, text)
        if match:
            return match.group(1)
        
        return None
    
    def extract_spreadsheet_id_from_search(self, search_results: str) -> Optional[str]:
        """Extract spreadsheet ID from search results JSON"""
        try:
            results = json.loads(search_results)
            if isinstance(results, list) and len(results) > 0:
                # Take the first result
                first_result = results[0]
                return first_result.get("id")
        except:
            pass
        return None
    
    def generate_natural_response(self, user_query: str, sheet_data: str) -> str:
        """Generate a natural language response based on the sheet data"""
        try:
            prompt = f"""
You are Sara, a helpful AI assistant. A user asked: "{user_query}"

Here's the data from the Google Sheet:
{sheet_data}

Please analyze this data and provide a helpful, natural language response to the user's query. 
Be specific and reference the actual data from the sheet. If the data doesn't contain information 
relevant to the user's query, let them know what information is available instead.

Keep your response conversational and helpful, as if you're speaking in a Slack channel.
"""

            client = get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are Sara, a helpful AI assistant that analyzes Google Sheets data and provides natural language responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"I found the data but had trouble analyzing it: {str(e)}"
    
    async def lookup_data_in_sheets_async(self, user_query: str) -> str:
        """Main async function to lookup data in Google Sheets and return natural language response"""
        try:
            # Ensure MCP connection
            if not await self._ensure_mcp_connection():
                return "I couldn't connect to Google Drive. Please run the authentication setup: `python3 setup_auth.py`"
            
            # First, try to extract spreadsheet ID from query if provided
            spreadsheet_id = self.extract_spreadsheet_id(user_query)
            
            if not spreadsheet_id:
                # Search for relevant sheets (requires authentication)
                try:
                    search_results = await mcp_client.search_sheets(user_query)
                    if not search_results:
                        return "I couldn't find any relevant Google Sheets for your query. Please provide a specific spreadsheet URL or ID."
                    
                    # Extract spreadsheet ID from search results
                    spreadsheet_id = self.extract_spreadsheet_id_from_search(search_results)
                    if not spreadsheet_id:
                        return "I found some sheets but couldn't access them. Please provide a specific spreadsheet ID or ensure proper sharing permissions."
                except Exception as e:
                    return "I need a specific spreadsheet URL or ID to look up data. Please provide the Google Sheets link in your message."
            
            # Read the sheet data (try public first, then authenticated)
            sheet_data = await mcp_client.read_sheet_data(spreadsheet_id, try_public_first=True)
            if not sheet_data:
                return """I couldn't read the data from the specified sheet. This could be because:

1. **For public sheets**: Make sure the sheet is set to "Anyone with the link can view"
2. **For private sheets**: Run authentication setup with `python3 setup_auth.py`
3. **Check the URL**: Ensure the spreadsheet ID/URL is correct

Please verify the sharing settings and try again."""
            
            # Check if we got an error message instead of data
            if "Error reading" in sheet_data:
                return f"I encountered an issue accessing the sheet: {sheet_data}"
            
            # Use OpenAI to generate natural language response
            return self.generate_natural_response(user_query, sheet_data)
            
        except Exception as e:
            return f"An error occurred while looking up the data: {str(e)}"
    
    def lookup_data_in_sheets(self, user_query: str) -> str:
        """Synchronous wrapper for the async lookup function"""
        try:
            # Create new event loop if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, we need to use a different approach
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.lookup_data_in_sheets_async(user_query))
                        return future.result()
                else:
                    return loop.run_until_complete(self.lookup_data_in_sheets_async(user_query))
            except RuntimeError:
                # No event loop exists, create one
                return asyncio.run(self.lookup_data_in_sheets_async(user_query))
        except Exception as e:
            return f"An error occurred while setting up the lookup: {str(e)}"
    
    async def cleanup(self):
        """Clean up the MCP client"""
        await mcp_client.cleanup()
        self.mcp_initialized = False

# Global instance
sheets_service = SheetsService()
