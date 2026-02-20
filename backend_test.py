import requests
import sys
import json
from datetime import datetime

class VoiceBotAPITester:
    def __init__(self, base_url="https://check-assignment.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            result = {
                "test_name": name,
                "success": success,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "endpoint": endpoint
            }

            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    result["response"] = response.json()
                except:
                    result["response"] = response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    result["error_response"] = response.json()
                except:
                    result["error_response"] = response.text

            self.test_results.append(result)
            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                "test_name": name,
                "success": False,
                "error": str(e),
                "endpoint": endpoint
            }
            self.test_results.append(result)
            return False, {}

    def test_root_endpoint(self):
        """Test GET / endpoint"""
        return self.run_test("Root Status", "GET", "/", 200)

    def test_scenarios_endpoint(self):
        """Test GET /scenarios endpoint"""
        success, response = self.run_test("Get Scenarios", "GET", "/scenarios", 200)
        if success:
            scenarios = response.get('scenarios', [])
            print(f"   Found {len(scenarios)} scenarios")
            if len(scenarios) == 12:
                print(f"   ✅ Correct number of scenarios (12)")
            else:
                print(f"   ⚠️  Expected 12 scenarios, got {len(scenarios)}")
            
            # Check for probing_instructions in scenarios
            has_probing = all('probing_instructions' in s for s in scenarios)
            if has_probing:
                print(f"   ✅ All scenarios have probing_instructions")
            else:
                print(f"   ⚠️  Some scenarios missing probing_instructions")
                
        return success, response

    def test_bug_patterns_endpoint(self):
        """Test GET /bug-patterns endpoint"""
        success, response = self.run_test("Get Bug Patterns", "GET", "/bug-patterns", 200)
        if success:
            patterns = response.get('patterns', [])
            print(f"   Found {len(patterns)} bug patterns")
            if len(patterns) == 5:
                print(f"   ✅ Correct number of bug patterns (5)")
            else:
                print(f"   ⚠️  Expected 5 bug patterns, got {len(patterns)}")
        return success, response

    def test_seeded_bug_exists(self):
        """Test if seeded bug exists in database"""
        success, response = self.run_test("Get Bugs for Seeded Check", "GET", "/bugs", 200)
        if success:
            bugs = response.get('bugs', [])
            seeded_bug = any(bug.get('bug_description') == "Infinite loading loop when checking multiple doctor availability" for bug in bugs)
            if seeded_bug:
                print(f"   ✅ Seeded bug found in database")
            else:
                print(f"   ⚠️  Seeded bug not found - should exist on startup")
        return success, response

    def test_config_status(self):
        """Test GET /config/status endpoint"""
        success, response = self.run_test("Config Status", "GET", "/config/status", 200)
        if success:
            twilio = response.get('twilio_configured', False)
            anthropic = response.get('anthropic_configured', False)
            print(f"   Twilio configured: {twilio}")
            print(f"   Anthropic configured: {anthropic}")
        return success, response

    def test_calls_endpoint(self):
        """Test GET /calls endpoint"""
        return self.run_test("Get Calls", "GET", "/calls", 200)

    def test_bugs_endpoint(self):
        """Test GET /bugs endpoint"""
        return self.run_test("Get Bugs", "GET", "/bugs", 200)

    def test_create_bug(self):
        """Test POST /bugs endpoint"""
        bug_data = {
            "call_id": "test-call-123",
            "bug_description": "Test bug description",
            "severity": "medium",
            "timestamp_in_call": "1:30",
            "details": "This is a test bug report created during automated testing"
        }
        success, response = self.run_test("Create Bug Report", "POST", "/bugs", 200, bug_data)
        return success, response

    def test_delete_bug(self, bug_id):
        """Test DELETE /bugs/{bug_id} endpoint"""
        if not bug_id:
            print("❌ No bug ID provided for delete test")
            return False, {}
        return self.run_test("Delete Bug Report", "DELETE", f"/bugs/{bug_id}", 200)

def main():
    print("🚀 Starting Voice Bot API Testing...")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = VoiceBotAPITester()
    
    # Test all endpoints
    print("\n" + "="*50)
    print("TESTING BACKEND APIS")
    print("="*50)

    # Basic endpoints
    tester.test_root_endpoint()
    tester.test_scenarios_endpoint()
    tester.test_bug_patterns_endpoint()  # New test for bug patterns
    tester.test_seeded_bug_exists()      # New test for seeded bug
    tester.test_config_status()
    tester.test_calls_endpoint()
    tester.test_bugs_endpoint()
    
    # Test bug creation and deletion
    success, bug_response = tester.test_create_bug()
    if success and 'bug_id' in bug_response:
        bug_id = bug_response['bug_id']
        print(f"   Created bug with ID: {bug_id}")
        # Test delete
        tester.test_delete_bug(bug_id)
    else:
        print("   ⚠️  Could not test bug deletion - bug creation failed")

    # Print final results
    print(f"\n📊 FINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Save detailed results to file
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": tester.tests_run,
            "passed_tests": tester.tests_passed,
            "success_rate": (tester.tests_passed/tester.tests_run)*100,
            "test_details": tester.test_results
        }, f, indent=2)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())