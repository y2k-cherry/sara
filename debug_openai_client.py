#!/usr/bin/env python3
"""
Debug script to diagnose OpenAI client initialization issues
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_versions():
    """Test OpenAI package version and compatibility"""
    print("🔍 Testing OpenAI Package...")
    
    try:
        import openai
        print(f"✅ OpenAI package imported successfully")
        print(f"📦 OpenAI version: {openai.__version__}")
    except ImportError as e:
        print(f"❌ Failed to import OpenAI: {e}")
        return False
    
    return True

def test_environment_variables():
    """Test environment variable configuration"""
    print("\n🔍 Testing Environment Variables...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    print(f"✅ OPENAI_API_KEY found (length: {len(api_key)})")
    print(f"🔑 Key starts with: {api_key[:10]}...")
    
    return True

def test_basic_client_init():
    """Test basic OpenAI client initialization"""
    print("\n🔍 Testing Basic Client Initialization...")
    
    try:
        import openai
        api_key = os.getenv('OPENAI_API_KEY')
        
        # Try the most basic initialization
        client = openai.OpenAI(api_key=api_key)
        print("✅ Basic OpenAI client initialized successfully")
        return client
        
    except Exception as e:
        print(f"❌ Basic client initialization failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        return None

def test_client_with_timeout():
    """Test client initialization with timeout parameter"""
    print("\n🔍 Testing Client with Timeout...")
    
    try:
        import openai
        api_key = os.getenv('OPENAI_API_KEY')
        
        client = openai.OpenAI(
            api_key=api_key,
            timeout=30.0
        )
        print("✅ Client with timeout initialized successfully")
        return client
        
    except Exception as e:
        print(f"❌ Client with timeout failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        return None

def test_simple_api_call(client):
    """Test a simple API call"""
    print("\n🔍 Testing Simple API Call...")
    
    if not client:
        print("❌ No client available for testing")
        return False
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        print("✅ API call successful")
        print(f"📝 Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        
        # Check for common error types
        if "rate_limit" in str(e).lower():
            print("💡 This appears to be a rate limiting issue")
        elif "authentication" in str(e).lower():
            print("💡 This appears to be an authentication issue")
        elif "quota" in str(e).lower():
            print("💡 This appears to be a quota/billing issue")
        
        return False

def test_intent_classifier_import():
    """Test importing and using the intent classifier"""
    print("\n🔍 Testing Intent Classifier Import...")
    
    try:
        from intent_classifier import get_intent_from_text
        print("✅ Intent classifier imported successfully")
        
        # Test with a simple query
        test_query = "who hasn't paid"
        intent = get_intent_from_text(test_query)
        print(f"✅ Intent classification test: '{test_query}' -> '{intent}'")
        
        if intent == 'lookup_sheets':
            print("✅ Payment query classified correctly")
        else:
            print(f"⚠️  Payment query classified as '{intent}', expected 'lookup_sheets'")
        
        return True
        
    except Exception as e:
        print(f"❌ Intent classifier test failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return False

def provide_recommendations():
    """Provide recommendations based on test results"""
    print("\n💡 RECOMMENDATIONS:")
    print("=" * 50)
    
    print("1. **Check OpenAI Package Version**:")
    print("   - Run: pip show openai")
    print("   - Expected: openai>=1.0.0")
    print("   - If wrong version: pip install --upgrade openai")
    
    print("\n2. **Verify API Key**:")
    print("   - Check your .env file has: OPENAI_API_KEY=sk-...")
    print("   - Verify the key is valid at https://platform.openai.com/api-keys")
    print("   - Check your OpenAI account has available credits")
    
    print("\n3. **Check Network/Proxy Issues**:")
    print("   - If behind corporate firewall, may need proxy configuration")
    print("   - Try from different network to isolate network issues")
    
    print("\n4. **Environment-Specific Issues**:")
    print("   - Render deployment may have different Python/package versions")
    print("   - Check Render logs for specific error messages")
    print("   - Consider pinning exact package versions in requirements.txt")

def main():
    """Run all diagnostic tests"""
    print("🚀 OpenAI Intent Classifier Diagnostic Tool")
    print("=" * 60)
    
    # Run all tests
    tests_passed = 0
    total_tests = 6
    
    if test_openai_versions():
        tests_passed += 1
    
    if test_environment_variables():
        tests_passed += 1
    
    client = test_basic_client_init()
    if client:
        tests_passed += 1
    
    client_with_timeout = test_client_with_timeout()
    if client_with_timeout:
        tests_passed += 1
    
    # Use the best available client for API test
    best_client = client_with_timeout or client
    if test_simple_api_call(best_client):
        tests_passed += 1
    
    if test_intent_classifier_import():
        tests_passed += 1
    
    # Summary
    print(f"\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 30)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! OpenAI client should be working.")
    elif tests_passed >= 4:
        print("⚠️  Most tests passed. Minor issues detected.")
    else:
        print("❌ Multiple issues detected. OpenAI client needs attention.")
    
    provide_recommendations()
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
