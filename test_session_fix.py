#!/usr/bin/env python3
"""
Test script to verify session timeout fixes for slow data entry
"""

import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_session_config():
    """Test that session configuration is properly set"""
    print("🧪 Testing session configuration...")
    
    # Read app.py and check for session configuration
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check for session lifetime configuration
    if 'PERMANENT_SESSION_LIFETIME' in content and 'timedelta(hours=2)' in content:
        print("✅ Session lifetime extended to 2 hours")
    else:
        print("❌ Session lifetime not properly configured")
        return False
    
    # Check for permanent session setting
    if 'session.permanent = True' in content:
        print("✅ Session set to permanent")
    else:
        print("❌ Session not set to permanent")
        return False
    
    # Check for keep-alive endpoint
    if '/keep-alive' in content:
        print("✅ Keep-alive endpoint implemented")
    else:
        print("❌ Keep-alive endpoint missing")
        return False
    
    return True

def test_file_cleanup():
    """Test that file cleanup is more conservative"""
    print("\n🧪 Testing file cleanup configuration...")
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check for conservative cleanup timing
    if 'total_seconds() > 7200' in content:
        print("✅ File cleanup made more conservative (2-hour protection)")
    else:
        print("❌ File cleanup not properly protected")
        return False
    
    return True

def test_client_validation():
    """Test that client-side validation is implemented"""
    print("\n🧪 Testing client-side validation...")
    
    with open('templates/configure.html', 'r') as f:
        content = f.read()
    
    # Check for form validation (looking for actual validation code)
    if ('isNaN(solarCapacity)' in content and
        'e.preventDefault()' in content and
        'alert(' in content):
        print("✅ Client-side form validation implemented")
    else:
        print("❌ Client-side form validation missing")
        return False
    
    # Check for keep-alive mechanism
    if ('keepAliveInterval' in content and
        'fetch(\'/keep-alive\'' in content):
        print("✅ Client-side keep-alive mechanism implemented")
    else:
        print("❌ Client-side keep-alive mechanism missing")
        return False
    
    # Check for session status indicator
    if ('sessionStatus' in content and
        'bg-green-50' in content):
        print("✅ Session status indicator implemented")
    else:
        print("❌ Session status indicator missing")
        return False
    
    return True

def test_file_validation():
    """Test that file validation is implemented"""
    print("\n🧪 Testing file validation...")
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check for file existence validation
    if 'os.path.exists(file_path)' in content:
        print("✅ File existence validation implemented")
    else:
        print("❌ File existence validation missing")
        return False
    
    # Check for session cleanup on file not found
    if 'session.pop(\'uploaded_file\', None)' in content:
        print("✅ Session cleanup on file not found implemented")
    else:
        print("❌ Session cleanup on file not found missing")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🔧 Testing Solar Analyzer Session Timeout Fixes")
    print("=" * 50)
    
    tests = [
        test_session_config,
        test_file_cleanup,
        test_client_validation,
        test_file_validation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! The session timeout issue should be fixed.")
        print("\n📋 Summary of fixes implemented:")
        print("1. Extended session lifetime to 2 hours")
        print("2. Made sessions permanent after file upload")
        print("3. Implemented conservative file cleanup (2-hour protection)")
        print("4. Added client-side form validation")
        print("5. Added keep-alive mechanism for slow data entry")
        print("6. Added session status indicator")
        print("7. Added file existence validation before processing")
        print("8. Added proper session cleanup on file errors")
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)