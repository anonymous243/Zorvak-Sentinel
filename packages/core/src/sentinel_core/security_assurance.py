import json
import os
from pathlib import Path
from typing import List, Dict, Any

VALID_STATUSES = {"VERIFIED", "PARTIALLY_VERIFIED", "NOT_VERIFIED", "NOT_APPLICABLE"}
REQUIRED_FIELDS = {"control_id", "name", "implementation", "tests", "status", "environment", "limitations"}
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent

def validate_manifest(manifest_path: str) -> List[str]:
    """Validates the security assurance manifest returning a list of errors.
    Returns an empty list if perfectly valid.
    """
    errors = []
    
    if not os.path.exists(manifest_path):
        return [f"Manifest not found at {manifest_path}"]
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Failed to parse JSON: {e}"]
        
    if not isinstance(data, list):
        return ["Manifest must be a JSON array of objects."]
        
    seen_ids = set()
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"Item {idx} is not a JSON object.")
            continue
            
        missing_fields = REQUIRED_FIELDS - set(item.keys())
        if missing_fields:
            errors.append(f"Item {idx} missing required fields: {missing_fields}")
            
        control_id = item.get("control_id")
        if not control_id or not isinstance(control_id, str):
            errors.append(f"Item {idx} missing valid control_id.")
        elif control_id in seen_ids:
            errors.append(f"Duplicate control_id found: {control_id}")
        else:
            seen_ids.add(control_id)
            
        status = item.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"Item {idx} ({control_id}) has invalid status: {status}")
            
        # Verify references exist
        impls = item.get("implementation", [])
        tests = item.get("tests", [])
        
        for impl in impls:
            if not isinstance(impl, str) or not (ROOT_DIR / impl).exists():
                errors.append(f"Implementation file missing or invalid path: {impl}")
                
        for test in tests:
            if not isinstance(test, str) or not (ROOT_DIR / test).exists():
                errors.append(f"Test file missing or invalid path: {test}")
                
    return errors
