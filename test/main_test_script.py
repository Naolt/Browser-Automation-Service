# tests/main_test_script.py
import asyncio
import argparse
import os

# Import paths from your centralized config file
from config import (
    API_BASE_URL,
    SUCCESS_TEST_CASES_PATH,
    FAILURE_TEST_CASES_PATH,
    RAW_SUCCESS_TEST_RESULTS_PATH,
    RAW_FAILURE_TEST_RESULTS_PATH,
    EVALUATED_SUCCESS_TEST_RESULTS_PATH,
    EVALUATED_FAILURE_TEST_RESULTS_PATH
)
from test.test_runner import TestRunner
from test.result_evaluator import ResultEvaluator

async def main():
    parser = argparse.ArgumentParser(description="Run and evaluate browser agent tests.")
    parser.add_argument("--run-success", action="store_true", help="Run only success test cases.")
    parser.add_argument("--run-failure", action="store_true", help="Run only failure test cases.")
    parser.add_argument("--evaluate-success", action="store_true", help="Evaluate results from success test runs.")
    parser.add_argument("--evaluate-failure", action="store_true", help="Evaluate results from failure test runs.")
    parser.add_argument("--run-all", action="store_true", help="Run both success and failure test cases.")
    parser.add_argument("--evaluate-all", action="store_true", help="Evaluate results from both success and failure test runs.")
    parser.add_argument("--full-pipeline", action="store_true", help="Run all tests and then evaluate all results.")

    args = parser.parse_args()

    # Ensure results directory exists for all output paths
    os.makedirs(os.path.dirname(RAW_SUCCESS_TEST_RESULTS_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(RAW_FAILURE_TEST_RESULTS_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(EVALUATED_SUCCESS_TEST_RESULTS_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(EVALUATED_FAILURE_TEST_RESULTS_PATH), exist_ok=True)

    runner = TestRunner(api_base_url=API_BASE_URL)
    evaluator = ResultEvaluator()

    # --- Run Tests ---
    if args.run_success or args.run_all or args.full_pipeline:
        await runner.run_success_tests(
            success_cases_path=SUCCESS_TEST_CASES_PATH,
            output_path=RAW_SUCCESS_TEST_RESULTS_PATH
        )

    if args.run_failure or args.run_all or args.full_pipeline:
        await runner.run_failure_tests(
            failure_cases_path=FAILURE_TEST_CASES_PATH,
            output_path=RAW_FAILURE_TEST_RESULTS_PATH
        )

    # --- Evaluate Results ---
    if args.evaluate_success or args.evaluate_all or args.full_pipeline:
        evaluator.evaluate_specific_results(
            raw_results_path=RAW_SUCCESS_TEST_RESULTS_PATH,
            evaluated_results_path=EVALUATED_SUCCESS_TEST_RESULTS_PATH,
            test_type_name="success"
        )

    if args.evaluate_failure or args.evaluate_all or args.full_pipeline:
        evaluator.evaluate_specific_results(
            raw_results_path=RAW_FAILURE_TEST_RESULTS_PATH,
            evaluated_results_path=EVALUATED_FAILURE_TEST_RESULTS_PATH,
            test_type_name="failure"
        )

    # If no specific action was requested, print help
    if not any([args.run_success, args.run_failure, args.evaluate_success,
                args.evaluate_failure, args.run_all, args.evaluate_all, args.full_pipeline]):
        parser.print_help()
        print("\nNo action specified. Use --help for available options.")

if __name__ == "__main__":
    # Use asyncio.run() because your TestRunner methods are async.
    asyncio.run(main())