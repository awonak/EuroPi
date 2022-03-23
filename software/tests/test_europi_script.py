import os
import pytest
from europi_script import EuroPiScript

class ScriptForTesting(EuroPiScript):
    pass

@pytest.fixture
def script_for_testing():
    s = ScriptForTesting() 
    yield s
    s._reset_state()

def test_save_state(script_for_testing):
    script_for_testing._save_state("test state")
    assert script_for_testing._load_state() == "test state"

def test_state_file_name(script_for_testing):
    assert script_for_testing._state_filename == "saved_state_ScriptForTesting.txt"