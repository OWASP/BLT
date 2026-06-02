import pytest

def test_golden_set_schema_compliance(golden_report):
    """
    Validates that a given golden set report has all the mandatory fields required
    by the Toasty pipeline schema.
    """
    required_keys = [
        "id", 
        "source", 
        "category", 
        "raw_text", 
        "expected_entities", 
        "expected_redacted_text", 
        "adversarial_notes"
    ]
    
    filepath = golden_report.get("_filepath", "Unknown File")
    
    for key in required_keys:
        assert key in golden_report, f"Missing required key '{key}' in {filepath}"

def test_golden_set_byte_offsets(golden_report):
    """
    Validates that the 'start' and 'end' byte offsets strictly match
    the expected 'value' substring in the raw text.
    """
    raw_text = golden_report.get("raw_text", "")
    entities = golden_report.get("expected_entities", [])
    filepath = golden_report.get("_filepath", "Unknown File")
    
    for idx, entity in enumerate(entities):
        start = entity.get("start")
        end = entity.get("end")
        expected_value = entity.get("value")
        
        assert start is not None, f"Missing 'start' offset in {filepath} (Entity #{idx})"
        assert end is not None, f"Missing 'end' offset in {filepath} (Entity #{idx})"
        assert expected_value is not None, f"Missing 'value' in {filepath} (Entity #{idx})"
        
        # Extract the string using the provided offsets
        sliced_text = raw_text[start:end]
        
        assert sliced_text == expected_value, (
            f"Offset mismatch in {filepath} (Entity #{idx}):\n"
            f"  Expected value: '{expected_value}'\n"
            f"  Actual sliced text at [{start}:{end}]: '{sliced_text}'\n"
            f"Please fix the start/end offsets in the JSON file."
        )

def test_golden_set_source_validity(golden_report):
    """
    Validates that the source flag is correctly set to either historical or synthetic.
    """
    source = golden_report.get("source")
    filepath = golden_report.get("_filepath", "Unknown File")
    
    assert source in ["historical", "synthetic"], f"Invalid source '{source}' in {filepath}. Must be 'historical' or 'synthetic'."
