import requests
import sys
import json
from datetime import datetime

class VoiceBotAPITester:
    def __init__(self, base_url="http://localhost:8000/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n Testing {name}...")

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
                print(f"  PASS - Status: {response.status_code}")
                try:
                    result["response"] = response.json()
                except Exception:
                    result["response"] = response.text
            else:
                print(f"  FAIL - Expected {expected_status}, got {response.status_code}")
                try:
                    result["error_response"] = response.json()
                except Exception:
                    result["error_response"] = response.text

            self.test_results.append(result)
            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"  FAIL - Error: {str(e)}")
            result = {
                "test_name": name,
                "success": False,
                "error": str(e),
                "endpoint": endpoint
            }
            self.test_results.append(result)
            return False, {}

    def test_root_endpoint(self):
        return self.run_test("Root Status", "GET", "/", 200)

    def test_scenarios_endpoint(self):
        success, response = self.run_test("Get Scenarios", "GET", "/scenarios", 200)
        if success:
            scenarios = response.get('scenarios', [])
            print(f"   Found {len(scenarios)} scenarios")
            if len(scenarios) == 12:
                print(f"   OK - Correct number of scenarios (12)")
            else:
                print(f"   WARN - Expected 12 scenarios, got {len(scenarios)}")

            has_probing = all('probing_instructions' in s for s in scenarios)
            if has_probing:
                print(f"   OK - All scenarios have probing_instructions")
            else:
                print(f"   WARN - Some scenarios missing probing_instructions")

        return success, response

    def test_bug_patterns_endpoint(self):
        success, response = self.run_test("Get Bug Patterns", "GET", "/bug-patterns", 200)
        if success:
            patterns = response.get('patterns', [])
            print(f"   Found {len(patterns)} bug patterns")
            if len(patterns) == 5:
                print(f"   OK - Correct number of bug patterns (5)")
            else:
                print(f"   WARN - Expected 5 bug patterns, got {len(patterns)}")
        return success, response

    def test_seeded_bug_exists(self):
        success, response = self.run_test("Get Bugs for Seeded Check", "GET", "/bugs", 200)
        if success:
            bugs = response.get('bugs', [])
            seeded_bug = any(
                bug.get('bug_description') == "Infinite loading loop when checking multiple doctor availability"
                for bug in bugs
            )
            if seeded_bug:
                print(f"   OK - Seeded bug found in database")
            else:
                print(f"   WARN - Seeded bug not found - should exist on startup")
        return success, response

    def test_config_status(self):
        success, response = self.run_test("Config Status", "GET", "/config/status", 200)
        if success:
            vapi = response.get('vapi_configured', False)
            print(f"   Vapi configured: {vapi}")
        return success, response

    def test_calls_endpoint(self):
        return self.run_test("Get Calls", "GET", "/calls", 200)

    def test_bugs_endpoint(self):
        return self.run_test("Get Bugs", "GET", "/bugs", 200)

    def test_create_bug(self):
        bug_data = {
            "call_id": "test-call-123",
            "bug_description": "Test bug description",
            "severity": "medium",
            "timestamp_in_call": "1:30",
            "details": "This is a test bug report created during automated testing"
        }
        return self.run_test("Create Bug Report", "POST", "/bugs", 200, bug_data)

    def test_delete_bug(self, bug_id):
        if not bug_id:
            print("  FAIL - No bug ID provided for delete test")
            return False, {}
        return self.run_test("Delete Bug Report", "DELETE", f"/bugs/{bug_id}", 200)

    def test_vapi_webhook(self):
        """Test the Vapi webhook endpoint with a simulated end-of-call-report"""
        webhook_payload = {
            "message": {
                "type": "end-of-call-report",
                "endedReason": "hangup",
                "call": {
                    "id": "vapi-test-call-123",
                    "startedAt": "2026-02-20T10:00:00Z",
                    "endedAt": "2026-02-20T10:02:30Z",
                    "assistant": {
                        "metadata": {
                            "call_id": "test-webhook-call",
                            "scenario_name": "Test Scenario"
                        }
                    }
                },
                "artifact": {
                    "messages": [
                        {"role": "assistant", "message": "Hi, I need to schedule an appointment please."},
                        {"role": "user", "message": "Sure, let me check availability. Please hold."},
                        {"role": "assistant", "message": "Okay, I'll hold."},
                        {"role": "user", "message": "Please hold while I check."},
                        {"role": "assistant", "message": "Still here."},
                        {"role": "user", "message": "One moment please, still checking."}
                    ],
                    "transcript": "Assistant: Hi... User: Sure..."
                }
            }
        }
        return self.run_test(
            "Vapi Webhook (end-of-call-report)", "POST", "/vapi/webhook", 200, webhook_payload
        )


def main():
    print("Starting Voice Bot API Testing...")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tester = VoiceBotAPITester()

    print("\n" + "="*50)
    print("TESTING BACKEND APIS")
    print("="*50)

    tester.test_root_endpoint()
    tester.test_scenarios_endpoint()
    tester.test_bug_patterns_endpoint()
    tester.test_seeded_bug_exists()
    tester.test_config_status()
    tester.test_calls_endpoint()
    tester.test_bugs_endpoint()
    tester.test_vapi_webhook()

    success, bug_response = tester.test_create_bug()
    if success and 'bug_id' in bug_response:
        bug_id = bug_response['bug_id']
        print(f"   Created bug with ID: {bug_id}")
        tester.test_delete_bug(bug_id)
    else:
        print("   WARN - Could not test bug deletion - bug creation failed")

    print(f"\nFINAL RESULTS")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")

    with open('backend_test_results.json', 'w') as f:
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
