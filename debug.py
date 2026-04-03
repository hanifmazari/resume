import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoints():
    """Test various endpoints to see what's available"""
    endpoints_to_test = [
        "/",
        "/health", 
        "/docs",
        "/test"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            print(f"\n🔍 Testing {BASE_URL}{endpoint}...")
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    print(f"   Response: {json_data}")
                except:
                    print(f"   Response (text): {response.text[:200]}...")
            else:
                print(f"   Error: {response.text}")
                
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ Connection Error: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return True

def test_basic_connection():
    """Test basic connection to the port"""
    try:
        print(f"🔍 Testing basic connection to {BASE_URL}...")
        response = requests.get(BASE_URL, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Server is responding!")
            return True
        else:
            print(f"   ⚠️ Server responded with status: {response.status_code}")
            return True  # Server is running, just different response
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ No server running on port 8000: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 DEBUG: Testing API server...")
    
    if test_basic_connection():
        print("\n📍 Server is running! Testing individual endpoints...")
        test_endpoints()
        
        print("\n💡 Next steps:")
        print("1. Check if your FastAPI app is properly defined")
        print("2. Make sure all routes are correctly decorated")
        print("3. Check the server logs for any errors")
        print("4. Try accessing http://localhost:8000/docs in your browser")
        
    else:
        print("\n❌ No server detected on port 8000")
        print("Please start your FastAPI server first:")
        print("python app2.py")