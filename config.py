# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Paths to your test case data files
SUCCESS_TEST_CASES_PATH = os.getenv("SUCCESS_TEST_CASES_PATH", "test/test_data/success_test_cases.json")
FAILURE_TEST_CASES_PATH = os.getenv("FAILURE_TEST_CASES_PATH", "test/test_data/failure_test_cases.json")

# Paths for raw results (after submission to agent)
RAW_SUCCESS_TEST_RESULTS_PATH = os.getenv("RAW_SUCCESS_TEST_RESULTS_PATH", "test/results/raw_success_test_results.json")
RAW_FAILURE_TEST_RESULTS_PATH = os.getenv("RAW_FAILURE_TEST_RESULTS_PATH", "test/results/raw_failure_test_results.json")

# Paths for evaluated results (after fetching from Firestore)
EVALUATED_SUCCESS_TEST_RESULTS_PATH = os.getenv("EVALUATED_SUCCESS_TEST_RESULTS_PATH", "test/results/evaluated_success_test_results.json")
EVALUATED_FAILURE_TEST_RESULTS_PATH = os.getenv("EVALUATED_FAILURE_TEST_RESULTS_PATH", "test/results/evaluated_failure_test_results.json")