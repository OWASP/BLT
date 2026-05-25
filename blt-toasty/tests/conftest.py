import json
import glob
import os
import pytest

@pytest.fixture(scope="session")
def all_golden_reports():
    """
    Loads all JSON reports from both the historical and synthetic golden set directories.
    Returns a list of dictionaries.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    synthetic_files = glob.glob(os.path.join(base_dir, "golden_set", "synthetic", "*.json"))
    historical_files = glob.glob(os.path.join(base_dir, "golden_set", "historical", "*.json"))
    
    all_files = synthetic_files + historical_files
    reports = []
    
    for fpath in all_files:
        with open(fpath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # Store the file path in the dict for easier debugging if a test fails
                data["_filepath"] = fpath
                reports.append(data)
            except json.JSONDecodeError as e:
                pytest.fail(f"Failed to parse JSON in {fpath}: {str(e)}")
                
    return reports

def pytest_generate_tests(metafunc):
    """
    This tells Pytest to dynamically generate a test for EACH report in the golden set.
    Instead of running one big test 50 times, it creates 50 separate test cases.
    """
    if "golden_report" in metafunc.fixturenames:
        # We need to manually load the files here to parameterize the tests
        base_dir = os.path.dirname(os.path.abspath(__file__))
        synthetic_files = glob.glob(os.path.join(base_dir, "golden_set", "synthetic", "*.json"))
        historical_files = glob.glob(os.path.join(base_dir, "golden_set", "historical", "*.json"))
        all_files = synthetic_files + historical_files
        
        reports = []
        ids = []
        for fpath in all_files:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_filepath"] = fpath
                reports.append(data)
                # Use the file name as the test ID
                ids.append(os.path.basename(fpath))
                
        metafunc.parametrize("golden_report", reports, ids=ids)
