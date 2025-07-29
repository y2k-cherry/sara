#!/usr/bin/env python3
"""
Direct Google Sheets service that bypasses MCP authentication issues
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv('mcp-gdrive/.env')
load_dotenv()

class DirectSheetsService:
    """Direct Google Sheets service with OAuth for private sheets"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.oauth_credentials = None
        
        # Try to load OAuth credentials for private sheet access
        self._load_oauth_credentials()
        
        if not self.api_key and not self.oauth_credentials:
            raise ValueError("Neither GOOGLE_API_KEY nor OAuth credentials found")
    
    def _load_oauth_credentials(self):
        """Load OAuth credentials from token.json"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            
            token_path = 'token.json'
            if os.path.exists(token_path):
                self.oauth_credentials = Credentials.from_authorized_user_file(token_path)
                
                # Refresh if expired
                if self.oauth_credentials.expired and self.oauth_credentials.refresh_token:
                    self.oauth_credentials.refresh(Request())
                    
                print("✅ OAuth credentials loaded successfully")
            else:
                print("⚠️  No OAuth credentials found (token.json missing)")
                
        except Exception as e:
            print(f"⚠️  Failed to load OAuth credentials: {e}")
            self.oauth_credentials = None
    
    def extract_sheet_id(self, url_or_id: str) -> str:
        """Extract sheet ID from URL or return ID if already provided"""
        if 'docs.google.com/spreadsheets' in url_or_id:
            # Extract ID from URL
            parts = url_or_id.split('/d/')
            if len(parts) > 1:
                sheet_id = parts[1].split('/')[0]
                return sheet_id
        return url_or_id
    
    def read_private_sheet_oauth(self, sheet_id: str, range_name: str = "A1:Z10000") -> Optional[Dict[str, Any]]:
        """Read data from a private Google Sheet using OAuth credentials"""
        if not self.oauth_credentials:
            return None
            
        try:
            from googleapiclient.discovery import build
            
            # Build the service with OAuth credentials
            service = build('sheets', 'v4', credentials=self.oauth_credentials)
            
            # Call the Sheets API
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return None
            
            # Process the data
            headers = values[0] if values else []
            rows = values[1:] if len(values) > 1 else []
            
            return {
                'sheet_id': sheet_id,
                'headers': headers,
                'rows': rows,
                'total_rows': len(values),
                'total_columns': len(headers) if headers else 0
            }
            
        except Exception as e:
            print(f"OAuth Error reading sheet: {e}")
            return None
    
    def read_public_sheet(self, sheet_id: str, range_name: str = "A1:Z1000") -> Optional[Dict[str, Any]]:
        """Read data from a public Google Sheet using API key"""
        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range_name}"
            params = {'key': self.api_key}
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                values = data.get('values', [])
                
                if not values:
                    return None
                
                # Process the data
                headers = values[0] if values else []
                rows = values[1:] if len(values) > 1 else []
                
                return {
                    'sheet_id': sheet_id,
                    'headers': headers,
                    'rows': rows,
                    'total_rows': len(values),
                    'total_columns': len(headers) if headers else 0
                }
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error reading sheet: {e}")
            return None
    
    def analyze_sheet_data(self, sheet_data: Dict[str, Any], query: str) -> str:
        """Use OpenAI to analyze sheet data and answer queries"""
        if not sheet_data:
            return "I couldn't access the sheet data. Please make sure the sheet is publicly viewable."
        
        # Prepare data summary for OpenAI
        headers = sheet_data.get('headers', [])
        rows = sheet_data.get('rows', [])
        
        # Check if this is a search/count query that needs full data analysis
        search_patterns = [
            'how many times', 'count', 'find', 'search', 'appears', 'occurrences', 'instances',
            'how many brands', 'how many are listed', 'total brands', 'number of brands',
            'unique brands', 'distinct brands', 'brands are listed', 'listed here',
            'brands are', 'column b', 'status column', 'marked as', 'check whether',
            'brands are marked', 'marked as listed', 'how many', 'listed'
        ]
        is_search_query = any(pattern in query.lower() for pattern in search_patterns)
        
        # Force complete analysis for any query containing "brand" or "count" or "how many"
        force_complete_analysis = any(keyword in query.lower() for keyword in ['brand', 'count', 'how many'])
        
        if is_search_query or force_complete_analysis:
            # For search queries, analyze the complete dataset
            return self._analyze_complete_dataset(headers, rows, query)
        else:
            # For general queries, use sample data to avoid token limits
            sample_rows = rows[:10]
            
            # Create prompt for OpenAI with instruction to be brief and direct
            prompt = f"""
You are Sara, a helpful assistant that analyzes Google Sheets data. Be brief and direct in your responses.

Dataset Info:
- Headers: {headers}
- Total Rows: {len(rows)}
- Total Columns: {len(headers)}
- Sample Data (first 10 rows): {json.dumps(sample_rows, indent=2)}

User Query: {query}

Provide a brief, direct answer. Do not suggest manual formulas or explain how the user can do it themselves. Just analyze the data and give the answer.
"""

            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are Sara, a helpful assistant. Be brief and direct. Analyze the data and provide answers, don't suggest manual methods."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                return f"I was able to access the sheet with {len(rows)} rows and {len(headers)} columns, but encountered an error analyzing it: {e}"
    
    def _analyze_complete_dataset(self, headers: List[str], rows: List[List[str]], query: str) -> str:
        """Analyze the complete dataset for search/count queries"""
        try:
            # Check if this is a brand counting query
            brand_patterns = [
                'how many brands', 'brands are listed', 'total brands', 'number of brands', 
                'unique brands', 'distinct brands', 'brands are marked', 'marked as listed',
                'brands marked as', 'listed brands'
            ]
            is_brand_query = any(pattern in query.lower() for pattern in brand_patterns)
            
            # Also check if query contains "brand" and any counting/listing words
            has_brand = 'brand' in query.lower()
            has_counting = any(word in query.lower() for word in ['how many', 'count', 'total', 'number', 'listed', 'marked'])
            
            if is_brand_query or (has_brand and has_counting):
                return self._analyze_brands_complete(headers, rows, query)
            
            # Extract search terms from the query for regular search
            search_terms = self._extract_search_terms(query)
            
            if not search_terms:
                return "I couldn't identify what to search for in your query. Please specify what term or value you'd like me to find."
            
            # Search through all data
            results = {}
            for term in search_terms:
                count = 0
                locations = []
                
                # Search through all rows and columns
                for row_idx, row in enumerate(rows):
                    for col_idx, cell in enumerate(row):
                        if isinstance(cell, str) and term.lower() in cell.lower():
                            count += 1
                            col_name = headers[col_idx] if col_idx < len(headers) else f"Column {col_idx + 1}"
                            locations.append(f"Row {row_idx + 2}, {col_name}")  # +2 because row 1 is headers
                
                results[term] = {
                    'count': count,
                    'locations': locations[:10]  # Show first 10 locations
                }
            
            # Format response
            response_parts = []
            for term, data in results.items():
                count = data['count']
                if count == 0:
                    response_parts.append(f"The term '{term}' does not appear in the sheet.")
                elif count == 1:
                    response_parts.append(f"The term '{term}' appears once in the sheet.")
                else:
                    response_parts.append(f"The term '{term}' appears {count} times in the sheet.")
                    
                    if data['locations']:
                        response_parts.append(f"First few locations: {', '.join(data['locations'][:5])}")
                        if count > 5:
                            response_parts.append(f"(and {count - 5} more occurrences)")
            
            return "\n\n".join(response_parts)
            
        except Exception as e:
            return f"Error analyzing the complete dataset: {e}"
    
    def _analyze_brands_complete(self, headers: List[str], rows: List[List[str]], query: str) -> str:
        """Analyze brands using the complete dataset"""
        try:
            # Find brand column (usually first column or column B)
            brand_col_idx = 0
            if len(headers) > 1 and 'brand' in headers[1].lower():
                brand_col_idx = 1
            
            # Find status column (look for column M or 'Status')
            status_col_idx = None
            for idx, header in enumerate(headers):
                if header.lower() in ['status', 'm'] or idx == 12:  # Column M is index 12
                    status_col_idx = idx
                    break
            
            # Count all brands
            all_brands = set()
            listed_brands = set()
            
            for row in rows:
                if len(row) > brand_col_idx and row[brand_col_idx].strip():
                    brand = row[brand_col_idx].strip()
                    all_brands.add(brand)
                    
                    # Check if listed (if status column exists)
                    if status_col_idx is not None and len(row) > status_col_idx:
                        status = row[status_col_idx].strip().lower()
                        if 'listed' in status:
                            listed_brands.add(brand)
            
            total_brands = len(all_brands)
            total_listed = len(listed_brands)
            
            # Format response based on query
            if 'listed' in query.lower() and status_col_idx is not None:
                response = f"I analyzed the complete dataset with {len(rows)} rows:\n\n"
                response += f"📊 **Total unique brands**: {total_brands}\n"
                response += f"✅ **Brands marked as 'listed'**: {total_listed}\n"
                response += f"❌ **Brands not listed**: {total_brands - total_listed}\n\n"
                
                if total_listed > 0:
                    response += f"**Listed brands include**: {', '.join(list(listed_brands)[:10])}"
                    if total_listed > 10:
                        response += f" (and {total_listed - 10} more)"
                
                return response
            else:
                response = f"I analyzed the complete dataset with {len(rows)} rows:\n\n"
                response += f"📊 **Total unique brands**: {total_brands}\n\n"
                response += f"**Examples**: {', '.join(list(all_brands)[:10])}"
                if total_brands > 10:
                    response += f" (and {total_brands - 10} more)"
                
                return response
                
        except Exception as e:
            return f"Error analyzing brands in complete dataset: {e}"
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract search terms from the query"""
        import re
        
        # Look for quoted terms first
        quoted_terms = re.findall(r'"([^"]*)"', query)
        if quoted_terms:
            return quoted_terms
        
        # Look for terms after common patterns
        patterns = [
            r'how many times (?:is |does )?(?:the )?(?:word |term )?["\']?([^"\'?\s]+)["\']?',
            r'count (?:the )?(?:word |term )?["\']?([^"\'?\s]+)["\']?',
            r'find (?:the )?(?:word |term )?["\']?([^"\'?\s]+)["\']?',
            r'search for (?:the )?(?:word |term )?["\']?([^"\'?\s]+)["\']?',
            r'(?:word |term )?["\']?([^"\'?\s]+)["\']? appears',
            r'occurrences of (?:the )?(?:word |term )?["\']?([^"\'?\s]+)["\']?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query.lower())
            if matches:
                return [match.strip() for match in matches if match.strip()]
        
        # Fallback: look for capitalized words that might be search terms
        words = query.split()
        potential_terms = []
        for word in words:
            # Remove punctuation and check if it's a meaningful term
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) > 2 and clean_word.upper() == clean_word:
                potential_terms.append(clean_word)
        
        return potential_terms if potential_terms else []
    
    def _check_brand_balances(self, query: str) -> str:
        """Check Brand Balances sheet for negative amounts (unpaid brands)"""
        try:
            # Hardcoded Brand Balances sheet URL
            brand_balances_sheet_id = "1Ch6NflcXS6BfK0zZ8SoeoiU_PwKe8_oEVjDX2tTE8QY"
            brand_balances_range = "Brand Balances!A1:B1000"  # Specific sheet and range
            
            print("💰 Checking Brand Balances sheet for unpaid amounts...")
            
            # Try to read the Brand Balances sheet
            sheet_data = None
            if self.oauth_credentials:
                sheet_data = self.read_private_sheet_oauth(brand_balances_sheet_id, brand_balances_range)
            
            if not sheet_data and self.api_key:
                sheet_data = self.read_public_sheet(brand_balances_sheet_id, brand_balances_range)
            
            if not sheet_data:
                return "I couldn't access the Brand Balances sheet. Please make sure I have permission to access it."
            
            headers = sheet_data.get('headers', [])
            rows = sheet_data.get('rows', [])
            
            if len(headers) < 2:
                return "The Brand Balances sheet doesn't have the expected structure (needs at least 2 columns)."
            
            # Find brands with negative balances
            unpaid_brands = []
            
            for row in rows:
                if len(row) >= 2:
                    brand_name = row[0].strip() if row[0] else ""
                    balance_str = row[1].strip() if row[1] else ""
                    
                    if brand_name and balance_str:
                        try:
                            # Parse the balance (handle currency symbols, commas, etc.)
                            balance_clean = balance_str.replace('$', '').replace(',', '').replace('₹', '').strip()
                            balance = float(balance_clean)
                            
                            # If balance is negative, this brand hasn't paid
                            if balance < 0:
                                unpaid_brands.append({
                                    'brand': brand_name,
                                    'amount_due': abs(balance),  # Convert to positive for display
                                    'original_balance': balance_str
                                })
                        except ValueError:
                            # Skip rows where balance can't be parsed as a number
                            continue
            
            # Format the response
            if not unpaid_brands:
                return "🎉 Great news! All brands have paid their balances. No outstanding payments found."
            
            # Sort by amount due (highest first)
            unpaid_brands.sort(key=lambda x: x['amount_due'], reverse=True)
            
            response = f"💸 **Brands that haven't paid** ({len(unpaid_brands)} total):\n\n"
            
            total_outstanding = sum(brand['amount_due'] for brand in unpaid_brands)
            
            for brand in unpaid_brands:
                response += f"• **{brand['brand']}**: ₹{brand['amount_due']:,.2f} due\n"
            
            response += f"\n💰 **Total outstanding**: ₹{total_outstanding:,.2f}"
            
            return response
            
        except Exception as e:
            return f"Error checking brand balances: {e}"
    
    def count_unique_values(self, sheet_data: Dict[str, Any], column_index: int = 0) -> Dict[str, Any]:
        """Count unique values in a specific column"""
        if not sheet_data or not sheet_data.get('rows'):
            return {'error': 'No data available'}
        
        rows = sheet_data['rows']
        unique_values = set()
        
        for row in rows:
            if len(row) > column_index and row[column_index].strip():
                unique_values.add(row[column_index].strip())
        
        return {
            'unique_count': len(unique_values),
            'unique_values': list(unique_values),
            'total_rows': len(rows)
        }
    
    def process_sheets_query(self, sheet_url_or_id: str, query: str) -> str:
        """Main method to process a sheets query with OAuth fallback"""
        try:
            # Check if this is a payment status query
            payment_patterns = [
                "who hasn't paid", "who has not paid", "unpaid brands", "negative balance",
                "outstanding balance", "who owes", "brands that owe", "payment due",
                "overdue", "brands with negative", "who needs to pay"
            ]
            is_payment_query = any(pattern in query.lower() for pattern in payment_patterns)
            
            if is_payment_query:
                return self._check_brand_balances(query)
            
            # Extract sheet ID
            sheet_id = self.extract_sheet_id(sheet_url_or_id)
            sheet_data = None
            access_method = "unknown"
            
            # Try OAuth first (for private sheets)
            if self.oauth_credentials:
                print("🔐 Trying OAuth access for private sheet...")
                sheet_data = self.read_private_sheet_oauth(sheet_id)
                if sheet_data:
                    access_method = "OAuth (private sheet)"
            
            # Fallback to API key (for public sheets)
            if not sheet_data and self.api_key:
                print("🔑 Trying API key access for public sheet...")
                sheet_data = self.read_public_sheet(sheet_id)
                if sheet_data:
                    access_method = "API key (public sheet)"
            
            if not sheet_data:
                error_msg = f"I couldn't access the sheet (ID: {sheet_id}). "
                if not self.oauth_credentials and not self.api_key:
                    error_msg += "No authentication methods available."
                elif not self.oauth_credentials:
                    error_msg += "The sheet appears to be private. Please either:\n1. Make it publicly viewable, or\n2. Set up OAuth authentication for private access."
                elif not self.api_key:
                    error_msg += "OAuth failed and no API key available for public access."
                else:
                    error_msg += "Both OAuth and API key access failed. The sheet might not exist or you might not have permission."
                
                return error_msg
            
            print(f"✅ Successfully accessed sheet using {access_method}")
            
            # Remove the special handling that bypasses complete dataset analysis
            # All brand queries should now go through the complete dataset analysis
            
            # Use OpenAI for general analysis
            analysis = self.analyze_sheet_data(sheet_data, query)
            return analysis
            
        except Exception as e:
            return f"Sorry, I encountered an error processing your sheets query: {e}"

# Test the service
if __name__ == "__main__":
    service = DirectSheetsService()
    
    # Test with the user's sheet
    test_sheet_id = "167kbSbvnQunrYVD7lFplM42rTpexs6OlCvxABNGtnxc"
    test_query = "How many brands are in this sheet?"
    
    print("🧪 Testing Direct Sheets Service")
    print("=" * 50)
    
    result = service.process_sheets_query(test_sheet_id, test_query)
    print(f"Result: {result}")
