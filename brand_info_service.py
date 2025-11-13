#!/usr/bin/env python3
"""
Brand Information Service for fetching data from Brand Information Master table
"""

import os
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv
import openai
from difflib import SequenceMatcher
from direct_sheets_service import DirectSheetsService

# Load environment variables
load_dotenv()

class BrandInfoService:
    """Service for handling brand information queries"""
    
    def __init__(self):
        self.sheets_service = DirectSheetsService()
        self.openai_client = None
        
        # Brand Information Master sheet details
        self.brand_master_sheet_id = "1wkKXtgGLevFpbIaEWWrJ7Lw8iCUEjHT_Am-78PcJn80"
        self.brand_master_sheet_name = "Brand Information Master"
        # Use single quotes for sheet names with spaces
        self.brand_master_range = f"'{self.brand_master_sheet_name}'!A1:Z1000"
        
        # Column mapping (excluding column M as requested)
        self.excluded_columns = ['M']  # Column M should be excluded
    
    def _get_openai_client(self):
        """Get OpenAI client with lazy initialization"""
        if self.openai_client is None:
            try:
                self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            except Exception as e:
                print(f"⚠️  OpenAI client initialization failed in brand_info_service: {e}")
                # Create a mock client for brand name extraction
                self.openai_client = type('MockClient', (), {
                    'chat': type('Chat', (), {
                        'completions': type('Completions', (), {
                            'create': lambda *args, **kwargs: type('Response', (), {
                                'choices': [type('Choice', (), {
                                    'message': type('Message', (), {
                                        'content': 'Unable to extract brand name due to OpenAI client issues'
                                    })()
                                })()]
                            })()
                        })()
                    })()
                })()
        return self.openai_client
    
    def extract_brand_name(self, query: str) -> Optional[str]:
        """Extract brand name from user query using OpenAI"""
        try:
            client = self._get_openai_client()
            
            prompt = f"""
Extract the brand name from this query. Return only the brand name, nothing else.

Query: "{query}"

Examples:
- "fetch Freakins info" → Freakins
- "Show me info for Yama Yoga" → Yama Yoga
- "What's FAE's GST number" → FAE
- "Do we have inde wild's GST details" → inde wild
- "What is Theater's brand ID" → Theater

If no clear brand name is found, return "UNCLEAR".
"""
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a brand name extraction assistant. Extract only the brand name from queries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0
            )
            
            extracted_name = response.choices[0].message.content.strip()
            
            # Clean up the extracted name
            if extracted_name and extracted_name != "UNCLEAR":
                # Remove quotes and extra whitespace
                extracted_name = extracted_name.strip('"\'').strip()
                return extracted_name
            
            return None
            
        except Exception as e:
            print(f"Error extracting brand name: {e}")
            # Fallback: try simple pattern matching
            return self._extract_brand_name_fallback(query)
    
    def _extract_brand_name_fallback(self, query: str) -> Optional[str]:
        """Fallback method to extract brand name using pattern matching"""
        # Common patterns for brand queries
        patterns = [
            r"fetch\s+([^'\s]+(?:\s+[^'\s]+)*)\s+info",
            r"show\s+me\s+info\s+for\s+([^'\s]+(?:\s+[^'\s]+)*)",
            r"what'?s\s+([^'\s]+(?:\s+[^'\s]+)*)'?s?\s+gst",
            r"do\s+we\s+have\s+([^'\s]+(?:\s+[^'\s]+)*)'?s?\s+gst",
            r"what\s+is\s+([^'\s]+(?:\s+[^'\s]+)*)'?s?\s+brand\s+id",
            r"([^'\s]+(?:\s+[^'\s]+)*)\s+info",
            r"info\s+for\s+([^'\s]+(?:\s+[^'\s]+)*)",
        ]
        
        query_lower = query.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                brand_name = match.group(1).strip()
                # Clean up common words
                brand_name = re.sub(r'\b(the|a|an)\b', '', brand_name, flags=re.IGNORECASE).strip()
                if brand_name:
                    return brand_name
        
        return None
    
    def find_similar_brand(self, brand_name: str, company_names: List[str]) -> Tuple[Optional[str], float]:
        """Find the most similar brand name using fuzzy matching"""
        if not brand_name or not company_names:
            return None, 0.0
        
        best_match = None
        best_ratio = 0.0
        
        brand_name_lower = brand_name.lower().strip()
        
        for company_name in company_names:
            if not company_name:
                continue
                
            company_name_lower = company_name.lower().strip()
            
            # Exact match
            if brand_name_lower == company_name_lower:
                return company_name, 1.0
            
            # Check if brand name is contained in company name or vice versa
            if brand_name_lower in company_name_lower or company_name_lower in brand_name_lower:
                ratio = max(len(brand_name_lower) / len(company_name_lower), 
                           len(company_name_lower) / len(brand_name_lower))
                if ratio > best_ratio:
                    best_match = company_name
                    best_ratio = ratio
            
            # Use sequence matcher for fuzzy matching
            ratio = SequenceMatcher(None, brand_name_lower, company_name_lower).ratio()
            if ratio > best_ratio:
                best_match = company_name
                best_ratio = ratio
        
        return best_match, best_ratio
    
    def get_brand_sheet_data(self) -> Optional[Dict[str, Any]]:
        """Get data from the Brand Information Master sheet"""
        try:
            # Try OAuth first (for private sheets)
            sheet_data = None
            if self.sheets_service.oauth_credentials:
                print("🔐 Trying OAuth access for Brand Master sheet...")
                sheet_data = self.sheets_service.read_private_sheet_oauth(
                    self.brand_master_sheet_id, 
                    self.brand_master_range
                )
            
            # Fallback to API key (for public sheets)
            if not sheet_data and self.sheets_service.api_key:
                print("🔑 Trying API key access for Brand Master sheet...")
                sheet_data = self.sheets_service.read_public_sheet(
                    self.brand_master_sheet_id, 
                    self.brand_master_range
                )
            
            return sheet_data
            
        except Exception as e:
            print(f"Error accessing Brand Master sheet: {e}")
            return None
    
    def format_brand_info(self, headers: List[str], brand_row: List[str]) -> str:
        """Format brand information in a readable format"""
        if not headers or not brand_row:
            return "No brand information found."
        
        response = "📋 **Brand Information:**\n\n"
        
        # Convert column letters to indices for exclusion
        excluded_indices = []
        for col_letter in self.excluded_columns:
            # Convert A=0, B=1, C=2, ..., M=12, etc.
            col_index = ord(col_letter.upper()) - ord('A')
            excluded_indices.append(col_index)
        
        for i, (header, value) in enumerate(zip(headers, brand_row)):
            # Skip excluded columns
            if i in excluded_indices:
                continue
                
            if not header.strip():
                continue
                
            # Clean up header name
            clean_header = header.strip()
            clean_value = value.strip() if value else ""
            
            if clean_value:
                response += f"**{clean_header}**: {clean_value}\n"
            else:
                response += f"**{clean_header}**: _No information available_\n"
        
        return response
    
    def process_brand_query(self, query: str) -> str:
        """Main method to process brand information queries"""
        try:
            # Step 1: Extract brand name from query
            brand_name = self.extract_brand_name(query)
            
            if not brand_name:
                return "I couldn't identify a clear brand name from your query. Could you please specify which brand you're asking about?\n\nFor example:\n• 'fetch Freakins info'\n• 'Show me info for Yama Yoga'\n• 'What's FAE's GST number'"
            
            print(f"🔍 Extracted brand name: {brand_name}")
            
            # Step 2: Get sheet data
            sheet_data = self.get_brand_sheet_data()
            
            if not sheet_data:
                return "I couldn't access the Brand Information Master sheet. Please make sure I have permission to access it or that it's publicly viewable."
            
            headers = sheet_data.get('headers', [])
            rows = sheet_data.get('rows', [])
            
            if not headers or not rows:
                return "The Brand Information Master sheet appears to be empty or has no data."
            
            # Step 3: Find Company Name column (Column B)
            company_name_col_index = None
            for i, header in enumerate(headers):
                if header.lower().strip() in ['company name', 'brand name', 'name'] or i == 1:  # Column B is index 1
                    company_name_col_index = i
                    break
            
            if company_name_col_index is None:
                return "I couldn't find the Company Name column in the Brand Master sheet."
            
            # Step 4: Extract all company names for fuzzy matching
            company_names = []
            for row in rows:
                if len(row) > company_name_col_index and row[company_name_col_index].strip():
                    company_names.append(row[company_name_col_index].strip())
            
            # Step 5: Find the best matching brand
            best_match, similarity_ratio = self.find_similar_brand(brand_name, company_names)
            
            if not best_match or similarity_ratio < 0.6:  # Threshold for similarity
                return f"I couldn't find a brand matching '{brand_name}' in the Brand Master sheet.\n\nPlease check the spelling or try a different variation of the brand name."
            
            # Step 6: If similarity is not perfect, ask for confirmation
            if similarity_ratio < 0.9:
                return f"I found a similar brand: **{best_match}** (similarity: {similarity_ratio:.0%})\n\nDid you mean '{best_match}'? Please confirm and I'll fetch the information."
            
            # Step 7: Find the row with the matching brand
            brand_row = None
            for row in rows:
                if (len(row) > company_name_col_index and 
                    row[company_name_col_index].strip().lower() == best_match.lower()):
                    brand_row = row
                    break
            
            if not brand_row:
                return f"Found the brand '{best_match}' but couldn't retrieve its information."
            
            # Step 8: Format and return the brand information
            formatted_info = self.format_brand_info(headers, brand_row)
            
            return f"✅ Found information for **{best_match}**:\n\n{formatted_info}"
            
        except Exception as e:
            return f"Sorry, I encountered an error processing your brand query: {e}"

# Test the service
if __name__ == "__main__":
    service = BrandInfoService()
    
    # Test queries
    test_queries = [
        "fetch Freakins info",
        "Show me info for Yama Yoga",
        "What's FAE's GST number",
        "Do we have inde wild's GST details",
        "What is Theater's brand ID"
    ]
    
    print("🧪 Testing Brand Info Service")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = service.process_brand_query(query)
        print(f"Result: {result}")
        print("-" * 30)
