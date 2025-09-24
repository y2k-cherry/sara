#!/usr/bin/env python3
"""
Service Status Checker for Sara Bot
Checks the health and availability of all critical services
"""

import os
import json
import requests
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv
import openai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

class ServiceStatusChecker:
    """Comprehensive service status checker for Sara Bot"""
    
    def __init__(self):
        self.status_results = {}
        
    def check_all_services(self) -> Dict[str, Any]:
        """Check all services and return comprehensive status"""
        print("🔍 Checking all Sara services...")
        
        # Core Services
        self.status_results['openai'] = self._check_openai_service()
        self.status_results['google_sheets_api'] = self._check_google_sheets_api()
        self.status_results['google_oauth'] = self._check_google_oauth()
        self.status_results['slack_bot'] = self._check_slack_bot_config()
        
        # Feature Services
        self.status_results['intent_classifier'] = self._check_intent_classifier()
        self.status_results['direct_sheets'] = self._check_direct_sheets_service()
        self.status_results['brand_info'] = self._check_brand_info_service()
        self.status_results['email_service'] = self._check_email_service()
        self.status_results['agreement_service'] = self._check_agreement_service()
        
        # Environment & Configuration
        self.status_results['environment'] = self._check_environment_variables()
        self.status_results['file_permissions'] = self._check_file_permissions()
        
        return self.status_results
    
    def _check_openai_service(self) -> Dict[str, Any]:
        """Check OpenAI API connectivity and configuration"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return {
                    'status': 'FAILED',
                    'error': 'OPENAI_API_KEY environment variable not set',
                    'impact': 'Intent classification will fail, causing inconsistent responses'
                }
            
            # Test API connection
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            
            return {
                'status': 'HEALTHY',
                'details': 'OpenAI API connection successful',
                'model': 'gpt-4'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Intent classification will use fallback patterns only'
            }
    
    def _check_google_sheets_api(self) -> Dict[str, Any]:
        """Check Google Sheets API key"""
        try:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                return {
                    'status': 'FAILED',
                    'error': 'GOOGLE_API_KEY environment variable not set',
                    'impact': 'Cannot access public Google Sheets'
                }
            
            # Test API with a simple request
            test_sheet_id = "1Ch6NflcXS6BfK0zZ8SoeoiU_PwKe8_oEVjDX2tTE8QY"  # Brand Balances sheet
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{test_sheet_id}/values/A1:A1"
            params = {'key': api_key}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return {
                    'status': 'HEALTHY',
                    'details': 'Google Sheets API key working'
                }
            else:
                return {
                    'status': 'FAILED',
                    'error': f'API returned status {response.status_code}',
                    'impact': 'Cannot access public Google Sheets'
                }
                
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Cannot access public Google Sheets'
            }
    
    def _check_google_oauth(self) -> Dict[str, Any]:
        """Check Google OAuth credentials for private sheets"""
        try:
            # Check for OAuth credentials in environment or file
            google_token_json = os.getenv('GOOGLE_TOKEN_JSON')
            token_file_exists = os.path.exists('token.json')
            
            if not google_token_json and not token_file_exists:
                return {
                    'status': 'WARNING',
                    'error': 'No OAuth credentials found (neither GOOGLE_TOKEN_JSON env var nor token.json)',
                    'impact': 'Cannot access private Google Sheets'
                }
            
            # Try to load and validate credentials
            credentials = None
            if google_token_json:
                token_data = json.loads(google_token_json)
                credentials = Credentials.from_authorized_user_info(token_data)
            elif token_file_exists:
                credentials = Credentials.from_authorized_user_file('token.json')
            
            if credentials:
                # Test if credentials need refresh
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                
                # Test with a simple API call
                service = build('sheets', 'v4', credentials=credentials)
                test_sheet_id = "1Ch6NflcXS6BfK0zZ8SoeoiU_PwKe8_oEVjDX2tTE8QY"
                
                result = service.spreadsheets().values().get(
                    spreadsheetId=test_sheet_id,
                    range="A1:A1"
                ).execute()
                
                return {
                    'status': 'HEALTHY',
                    'details': 'OAuth credentials working, can access private sheets'
                }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Cannot access private Google Sheets'
            }
    
    def _check_slack_bot_config(self) -> Dict[str, Any]:
        """Check Slack bot configuration"""
        try:
            bot_token = os.getenv('SLACK_BOT_TOKEN')
            app_token = os.getenv('SLACK_APP_TOKEN')
            
            if not bot_token:
                return {
                    'status': 'FAILED',
                    'error': 'SLACK_BOT_TOKEN environment variable not set',
                    'impact': 'Bot cannot connect to Slack'
                }
            
            if not app_token:
                return {
                    'status': 'FAILED',
                    'error': 'SLACK_APP_TOKEN environment variable not set',
                    'impact': 'Bot cannot use Socket Mode'
                }
            
            return {
                'status': 'HEALTHY',
                'details': 'Slack tokens configured'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Bot may not connect to Slack properly'
            }
    
    def _check_intent_classifier(self) -> Dict[str, Any]:
        """Check intent classification functionality"""
        try:
            from intent_classifier import get_intent_from_text
            
            # Test with the problematic query
            test_query = "who hasn't paid"
            intent = get_intent_from_text(test_query)
            
            if intent == 'lookup_sheets':
                return {
                    'status': 'HEALTHY',
                    'details': f'Intent classifier working - "{test_query}" -> "{intent}"'
                }
            else:
                return {
                    'status': 'WARNING',
                    'error': f'Intent classifier returned "{intent}" for "{test_query}", expected "lookup_sheets"',
                    'impact': 'Payment queries may not be classified correctly'
                }
                
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Intent classification will fail'
            }
    
    def _check_direct_sheets_service(self) -> Dict[str, Any]:
        """Check Direct Sheets Service functionality"""
        try:
            from direct_sheets_service import DirectSheetsService
            
            service = DirectSheetsService()
            
            # Test payment query functionality
            test_result = service._check_brand_balances("who hasn't paid")
            
            if "Error" not in test_result and "couldn't access" not in test_result:
                return {
                    'status': 'HEALTHY',
                    'details': 'Direct Sheets Service can access Brand Balances sheet'
                }
            else:
                return {
                    'status': 'WARNING',
                    'error': test_result,
                    'impact': 'Payment queries may fail'
                }
                
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Sheets queries will fail'
            }
    
    def _check_brand_info_service(self) -> Dict[str, Any]:
        """Check Brand Info Service"""
        try:
            from brand_info_service import BrandInfoService
            
            service = BrandInfoService()
            return {
                'status': 'HEALTHY',
                'details': 'Brand Info Service initialized successfully'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Brand information queries will fail'
            }
    
    def _check_email_service(self) -> Dict[str, Any]:
        """Check Email Service configuration"""
        try:
            smtp_server = os.getenv('SMTP_SERVER')
            smtp_port = os.getenv('SMTP_PORT')
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            
            missing_vars = []
            if not smtp_server: missing_vars.append('SMTP_SERVER')
            if not smtp_port: missing_vars.append('SMTP_PORT')
            if not smtp_username: missing_vars.append('SMTP_USERNAME')
            if not smtp_password: missing_vars.append('SMTP_PASSWORD')
            
            if missing_vars:
                return {
                    'status': 'WARNING',
                    'error': f'Missing email configuration: {", ".join(missing_vars)}',
                    'impact': 'Email sending functionality will not work'
                }
            
            return {
                'status': 'HEALTHY',
                'details': 'Email service configuration complete'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Email service may not work'
            }
    
    def _check_agreement_service(self) -> Dict[str, Any]:
        """Check Agreement Service dependencies"""
        try:
            template_exists = os.path.exists('Partnership Agreement Template.docx')
            
            if not template_exists:
                return {
                    'status': 'WARNING',
                    'error': 'Partnership Agreement Template.docx not found',
                    'impact': 'Agreement generation will fail'
                }
            
            return {
                'status': 'HEALTHY',
                'details': 'Agreement template file exists'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Agreement generation may fail'
            }
    
    def _check_environment_variables(self) -> Dict[str, Any]:
        """Check critical environment variables"""
        try:
            critical_vars = [
                'OPENAI_API_KEY',
                'SLACK_BOT_TOKEN', 
                'SLACK_APP_TOKEN',
                'GOOGLE_API_KEY'
            ]
            
            optional_vars = [
                'GOOGLE_TOKEN_JSON',
                'SMTP_SERVER',
                'SMTP_PORT', 
                'SMTP_USERNAME',
                'SMTP_PASSWORD'
            ]
            
            missing_critical = [var for var in critical_vars if not os.getenv(var)]
            missing_optional = [var for var in optional_vars if not os.getenv(var)]
            
            if missing_critical:
                return {
                    'status': 'FAILED',
                    'error': f'Missing critical environment variables: {", ".join(missing_critical)}',
                    'impact': 'Core functionality will fail'
                }
            
            details = f'All critical environment variables set'
            if missing_optional:
                details += f'. Optional missing: {", ".join(missing_optional)}'
            
            return {
                'status': 'HEALTHY',
                'details': details
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'Environment configuration issues'
            }
    
    def _check_file_permissions(self) -> Dict[str, Any]:
        """Check file permissions and access"""
        try:
            critical_files = [
                'orchestrator.py',
                'intent_classifier.py',
                'direct_sheets_service.py'
            ]
            
            missing_files = [f for f in critical_files if not os.path.exists(f)]
            
            if missing_files:
                return {
                    'status': 'FAILED',
                    'error': f'Missing critical files: {", ".join(missing_files)}',
                    'impact': 'Bot will not function'
                }
            
            return {
                'status': 'HEALTHY',
                'details': 'All critical files present'
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'impact': 'File access issues'
            }
    
    def format_status_report(self) -> str:
        """Format a comprehensive status report"""
        if not self.status_results:
            self.check_all_services()
        
        report = "🔍 **Sara Service Status Report**\n\n"
        
        # Count statuses
        healthy_count = sum(1 for s in self.status_results.values() if s['status'] == 'HEALTHY')
        warning_count = sum(1 for s in self.status_results.values() if s['status'] == 'WARNING')
        failed_count = sum(1 for s in self.status_results.values() if s['status'] == 'FAILED')
        total_count = len(self.status_results)
        
        # Overall status
        if failed_count > 0:
            overall_status = "🔴 CRITICAL ISSUES"
        elif warning_count > 0:
            overall_status = "🟡 SOME ISSUES"
        else:
            overall_status = "🟢 ALL SYSTEMS OPERATIONAL"
        
        report += f"**Overall Status**: {overall_status}\n"
        report += f"**Services**: {healthy_count}✅ {warning_count}⚠️ {failed_count}❌ (Total: {total_count})\n\n"
        
        # Detailed status by category
        categories = {
            "🔧 Core Services": ['openai', 'google_sheets_api', 'google_oauth', 'slack_bot'],
            "🎯 Feature Services": ['intent_classifier', 'direct_sheets', 'brand_info', 'email_service', 'agreement_service'],
            "⚙️ System": ['environment', 'file_permissions']
        }
        
        for category, services in categories.items():
            report += f"**{category}**\n"
            for service in services:
                if service in self.status_results:
                    status_info = self.status_results[service]
                    status_emoji = {
                        'HEALTHY': '✅',
                        'WARNING': '⚠️',
                        'FAILED': '❌'
                    }.get(status_info['status'], '❓')
                    
                    service_name = service.replace('_', ' ').title()
                    report += f"• {status_emoji} **{service_name}**: {status_info['status']}\n"
                    
                    if status_info['status'] != 'HEALTHY':
                        if 'error' in status_info:
                            report += f"  └─ Error: {status_info['error']}\n"
                        if 'impact' in status_info:
                            report += f"  └─ Impact: {status_info['impact']}\n"
                    elif 'details' in status_info:
                        report += f"  └─ {status_info['details']}\n"
            report += "\n"
        
        # Specific diagnosis for the user's issue
        report += "**🔍 Diagnosis for 'who hasn't paid' Issue:**\n"
        
        intent_status = self.status_results.get('intent_classifier', {})
        openai_status = self.status_results.get('openai', {})
        sheets_status = self.status_results.get('direct_sheets', {})
        
        if intent_status.get('status') == 'FAILED' or openai_status.get('status') == 'FAILED':
            report += "❌ **Root Cause**: Intent classification is failing due to OpenAI issues\n"
            report += "📋 **Solution**: Fix OpenAI API key or connection issues\n"
        elif sheets_status.get('status') == 'FAILED':
            report += "❌ **Root Cause**: Sheets access is failing\n"
            report += "📋 **Solution**: Fix Google Sheets API or OAuth credentials\n"
        else:
            report += "✅ **Status**: All components for payment queries appear functional\n"
            report += "📋 **Note**: Issue may be intermittent or related to specific deployment environment\n"
        
        return report
    
    def get_quick_status(self) -> str:
        """Get a quick status summary"""
        if not self.status_results:
            self.check_all_services()
        
        healthy = sum(1 for s in self.status_results.values() if s['status'] == 'HEALTHY')
        total = len(self.status_results)
        
        if healthy == total:
            return f"🟢 All {total} services operational"
        else:
            failed = sum(1 for s in self.status_results.values() if s['status'] == 'FAILED')
            warning = sum(1 for s in self.status_results.values() if s['status'] == 'WARNING')
            return f"🔴 {failed} failed, ⚠️ {warning} warnings, ✅ {healthy} healthy (of {total} total)"

# Test the service
if __name__ == "__main__":
    checker = ServiceStatusChecker()
    print(checker.format_status_report())
