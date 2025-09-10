import json

from services.firestore_service import FirestoreService

db = FirestoreService().db


def evaluate_results():
    with open("test_results.json", "r") as f:
        test_results = json.load(f)

    evaluated_results = []
    durations = []
    success_count = 0
    total_count = 0

    for test in test_results:
        task_id = test.get("task_id")
        expected = test.get("expected_result")

        # If there was an error during task submission, skip Firestore lookup
        if not task_id:
            test["evaluation"] = "skipped (no task_id)"
            evaluated_results.append(test)
            continue

        total_count += 1

        # Fetch result from Firestore
        doc_ref = db.collection("browser_bookings").document(task_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            status = data.get("status", "unknown")
            result = data.get("result", "")
            duration_sec = data.get("duration", None)

            # Convert duration to minutes if present
            duration_min = round(duration_sec / 60, 2) if duration_sec is not None else None

            # Determine pass/fail
            passed = str(status).lower() == str(expected).lower()

            if passed:
                success_count += 1

            if duration_min is not None:
                durations.append(duration_min)

            # Add evaluation details
            test.update({
                "fetched_status": status,
                "fetched_result": result,
                "duration_minutes": duration_min,
                "passed": passed
            })
        else:
            test["evaluation"] = "not found in Firestore"

        evaluated_results.append(test)

    # Compute average duration and success rate
    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0
    success_rate = round((success_count / total_count) * 100, 2) if total_count else 0

    # Append stats to the JSON output
    summary = {
        "average_duration_minutes": avg_duration,
        "success_rate_percent": success_rate
    }
    evaluated_results.append({"summary": summary})

    # Save the evaluated results
    with open("evaluated_test_results.json", "w") as f:
        json.dump(evaluated_results, f, indent=4)

    print("✅ Evaluated results saved to evaluated_test_results.json")
    print(f"📊 Average duration: {avg_duration} minutes")
    print(f"✅ Success rate: {success_rate}%")


if __name__ == "__main__":
    evaluate_results()
