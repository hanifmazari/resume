import requests
import json
import os
import time
import socket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FlexibleResumeAPITester:
    def __init__(self, base_urls=None):
        # Try multiple possible server locations
        if base_urls is None:
            base_urls = [
                "http://localhost:8000",
                "http://127.0.0.1:8000", 
                "http://localhost:8001",
                "http://127.0.0.1:8001",
                "http://localhost:5000",
                "http://127.0.0.1:5000"
            ]
        
        self.base_url = None
        self.jwt_token = None
        self.api_key = os.getenv("API_KEY", "resume-api-key-2024-secure-change-in-production-xyz789")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "SecureAdmin123!")
        
        # Find working server
        self.base_url = self.find_working_server(base_urls)
        
        if self.base_url:
            print(f"🌐 Found API server at: {self.base_url}")
            print(f"🔧 Using API Key: {self.api_key[:20]}...")
            print(f"🔧 Using Admin Password: {'*' * len(self.admin_password)}")
        else:
            print("❌ No API server found! Please start your server first.")
            self.show_startup_instructions()
    
    def find_working_server(self, base_urls):
        """Try to find a working API server"""
        print("🔍 Searching for API server...")
        
        for url in base_urls:
            try:
                print(f"  Trying {url}...")
                response = requests.get(f"{url}/health", timeout=3)
                if response.status_code == 200:
                    print(f"  ✅ Found server at {url}")
                    return url
                else:
                    print(f"  ❌ Server responded with {response.status_code}")
            except requests.exceptions.ConnectionError:
                print(f"  ❌ Connection refused")
            except requests.exceptions.Timeout:
                print(f"  ❌ Connection timeout")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        return None
    
    def show_startup_instructions(self):
        """Show instructions for starting the server"""
        print("\n" + "="*60)
        print("🚨 SERVER NOT RUNNING - STARTUP INSTRUCTIONS")
        print("="*60)
        print("Your API server needs to be running before you can test it.")
        print("\nTo start your server, try one of these commands:")
        print("\n1. Using uvicorn:")
        print("   uvicorn app:app --host 0.0.0.0 --port 8000 --reload")
        print("   uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        print("\n2. Using Python directly:")
        print("   python app.py")
        print("   python main.py")
        print("\n3. Check for startup scripts:")
        print("   python run.py")
        print("   python start.py")
        print("\n4. Install missing dependencies:")
        print("   pip install fastapi uvicorn python-multipart")
        print("\nOnce your server is running, you should see:")
        print("   INFO: Uvicorn running on http://0.0.0.0:8000")
        print("\nThen run this test script again!")
        print("="*60)
    
    def check_port_availability(self, port=8000):
        """Check if a port is available"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0  # True if port is in use
    
    def get_server_info(self):
        """Get server information"""
        if not self.base_url:
            return False
        
        print("\n🔍 Getting server information...")
        try:
            # Check health
            health_response = requests.get(f"{self.base_url}/health")
            print(f"Health Status: {health_response.status_code}")
            
            # Check root endpoint
            root_response = requests.get(f"{self.base_url}/")
            print(f"Root Endpoint: {root_response.status_code}")
            
            # Check if docs are available
            try:
                docs_response = requests.get(f"{self.base_url}/docs")
                if docs_response.status_code == 200:
                    print(f"📚 API Documentation: {self.base_url}/docs")
            except:
                pass
            
            return True
        except Exception as e:
            print(f"❌ Error getting server info: {e}")
            return False
    
    def test_basic_connectivity(self):
        """Test basic server connectivity"""
        if not self.base_url:
            return False
        
        print("\n🔍 Testing basic connectivity...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Connectivity test failed: {e}")
            return False
    
    def test_authentication_quick(self):
        """Quick authentication test"""
        if not self.base_url:
            return False
        
        print("\n🔍 Quick authentication test...")
        try:
            # Test API key
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"text": "Test authentication"}
            response = requests.post(f"{self.base_url}/enhance_experience", json=data, headers=headers)
            
            if response.status_code == 200:
                print("✅ API Key authentication working!")
                return True
            elif response.status_code == 401:
                print("❌ API Key authentication failed - check your API key")
                return False
            else:
                print(f"⚠️ Unexpected response: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication test error: {e}")
            return False
    
    def test_jwt_login_quick(self):
        """Quick JWT login test"""
        if not self.base_url:
            return False
        
        print("\n🔍 Quick JWT login test...")
        try:
            data = {
                "username": "admin",
                "password": self.admin_password
            }
            response = requests.post(f"{self.base_url}/auth/login", data=data)
            
            if response.status_code == 200:
                result = response.json()
                self.jwt_token = result.get("access_token")
                print(f"✅ JWT Login successful!")
                return True
            else:
                print(f"❌ JWT Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ JWT Login error: {e}")
            return False
    
    def run_connectivity_check(self):
        """Run basic connectivity and authentication checks"""
        if not self.base_url:
            return False
        
        print("🚀 Running Connectivity Check\n")
        print("=" * 50)
        
        tests = [
            ("Server Info", self.get_server_info),
            ("Basic Connectivity", self.test_basic_connectivity),
            ("JWT Login", self.test_jwt_login_quick),
            ("API Key Auth", self.test_authentication_quick),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"{status}: {test_name}")
            except Exception as e:
                results.append((test_name, False))
                print(f"❌ FAILED: {test_name} - {e}")
            
            print("-" * 30)
        
        # Summary
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"\n🏁 Connectivity Check: {passed}/{total} tests passed")
        
        if passed == total:
            print("✅ All basic tests passed! Your server is ready.")
            print("You can now run the full test suite:")
            print("python test2.py full")
        else:
            print("❌ Some basic tests failed. Please check your server configuration.")
        
        return passed == total

def check_server_startup():
    """Check if server can be started"""
    print("🔍 Checking server startup requirements...")
    
    # Check if main files exist
    possible_main_files = ["app.py", "main.py", "run.py", "start.py", "server.py"]
    found_files = []
    
    for file in possible_main_files:
        if os.path.exists(file):
            found_files.append(file)
    
    if found_files:
        print(f"✅ Found potential server files: {', '.join(found_files)}")
    else:
        print("❌ No main server files found (app.py, main.py, etc.)")
        return False
    
    # Check if uvicorn is installed
    try:
        import uvicorn
        print("✅ Uvicorn is installed")
    except ImportError:
        print("❌ Uvicorn not installed. Run: pip install uvicorn")
        return False
    
    # Check if FastAPI is installed
    try:
        import fastapi
        print("✅ FastAPI is installed")
    except ImportError:
        print("❌ FastAPI not installed. Run: pip install fastapi")
        return False
    
    return True

def main():
    """Main function to handle different test modes"""
    import sys
    
    # Load environment variables
    load_dotenv()
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "check":
            # Check if server can be started
            check_server_startup()
            
        elif mode == "connectivity" or mode == "connect":
            # Run basic connectivity tests
            tester = FlexibleResumeAPITester()
            if tester.base_url:
                tester.run_connectivity_check()
            
        elif mode == "full":
            # Import and run full test suite (your original tests)
            print("Running full test suite...")
            try:
                from test2 import ResumeAPITester
                tester = ResumeAPITester()
                if tester.base_url:
                    tester.run_all_tests()
                else:
                    print("❌ Server not available for full testing")
            except ImportError:
                print("❌ Could not import full test suite")
                
        elif mode == "help":
            print("Usage: python flexible_test.py [mode]")
            print("Modes:")
            print("  check        - Check server startup requirements")
            print("  connectivity - Test basic server connectivity")
            print("  full         - Run full test suite")
            print("  help         - Show this help")
            
        else:
            print(f"Unknown mode: {mode}")
            print("Use 'help' for available modes")
    else:
        # Default: run connectivity check
        print("Running default connectivity check...")
        print("Use 'python flexible_test.py help' for more options\n")
        
        tester = FlexibleResumeAPITester()
        if tester.base_url:
            tester.run_connectivity_check()

if __name__ == "__main__":
    main()