# tests/result_evaluator.py
import json
import os
from services.firestore_service import FirestoreService

class ResultEvaluator:
    def __init__(self):
        self.db = FirestoreService().db

    def evaluate_specific_results(self, raw_results_path, evaluated_results_path, test_type_name=""):
        """
        Evaluates results from a specific raw results file and saves to a specific evaluated file.
        """
        print(f"\n--- Starting Evaluation for {test_type_name.capitalize()} Tests ---")
        try:
            with open(raw_results_path, "r") as f:
                test_results = json.load(f)
        except FileNotFoundError:
            print(f"Error: Raw test results file not found at {raw_results_path}. Cannot evaluate {test_type_name} tests.")
            return
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {raw_results_path}.")
            return

        evaluated_results = []
        durations = []
        success_count = 0
        total_tests_processed = 0 # Count tests for which we attempt Firestore lookup

        for test in test_results:
            task_id = test.get("task_id")
            expected = test.get("expected_result")
            test_details = test.get("task_details", {})

            # If there was an error during task submission, skip Firestore lookup
            if not task_id:
                test["evaluation_status"] = "submission_failed"
                test["passed"] = False # Mark as failed if submission itself failed
                evaluated_results.append(test)
                print(f"Skipping evaluation for a failed submission: {test_details.get('restaurant_name')}")
                continue

            total_tests_processed += 1
            print(f"Evaluating task ID: {task_id} (Expected: {expected}) for {test_details.get('restaurant_name')})")

            # Fetch result from Firestore
            doc_ref = self.db.collection("browser_bookings").document(task_id)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                status = data.get("status", "unknown")
                result_message = data.get("result", "No result message.")
                duration_sec = data.get("duration_seconds", None)
                duration_min = round(duration_sec / 60, 2) if duration_sec is not None else None

                # Determine pass/fail logic
                passed = False
                if str(expected).lower() == "completed":
                    passed = (str(status).lower() == "completed")
                elif str(expected).lower() == "failed":
                    # If expected is 'failed', and the actual status is NOT 'completed', consider it passed
                    # This implies any non-completion status means it failed as expected.
                    # Adjust this logic if you have specific failure statuses (e.g., "ERROR", "UNAVAILABLE").
                    passed = (str(status).lower() != "completed")
                else: # Catch unexpected 'expected' values
                    print(f"Warning: Unknown expected result type '{expected}' for test {task_id}")
                    passed = False

                if passed:
                    success_count += 1

                if duration_min is not None:
                    durations.append(duration_min)

                # Add evaluation details
                test.update({
                    "fetched_status": status,
                    "fetched_result_message": result_message,
                    "duration_minutes": duration_min,
                    "passed": passed,
                    "evaluation_status": "evaluated"
                })
                print(f"  -> Evaluated: Status='{status}', Passed={passed}")
            else:
                test["evaluation_status"] = "not_found_in_firestore"
                test["passed"] = False # If not found, it failed to complete or report
                print(f"  -> Evaluation skipped: Task ID {task_id} not found in Firestore.")

            evaluated_results.append(test)

        avg_duration = round(sum(durations) / len(durations), 2) if durations else 0
        max_duration = max(durations) if durations else 0
        median_duration = round(sorted(durations)[len(durations) // 2], 2) if durations else 0
        min_duration = min(durations) if durations else 0
        success_rate = round((success_count / total_tests_processed) * 100, 2) if total_tests_processed else 0


        # Append stats to the JSON output
        summary = {
            "test_type": test_type_name,
            "total_tests_attempted_submission": len(test_results),
            "total_tests_processed_for_evaluation": total_tests_processed,
            "successful_evaluations_count": success_count,
            "overall_success_rate_percent": success_rate,
            "average_duration_minutes": avg_duration,
            "max_duration_minutes": max_duration,
            "median_duration_minutes": median_duration,
            "min_duration_minutes": min_duration,
        }
        evaluated_results.append({"summary": summary})

        # Save the evaluated results
        output_dir = os.path.dirname(evaluated_results_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(evaluated_results_path, "w") as f:
            json.dump(evaluated_results, f, indent=4)

        print(f"✅ Evaluated {test_type_name} results saved to {evaluated_results_path}")
        print(f"📊 {test_type_name.capitalize()} Success Rate (matching expected outcome): {success_rate}%")
        print(f"📊 Average duration for {test_type_name} tasks: {avg_duration} minutes")