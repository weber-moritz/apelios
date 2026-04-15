import pytest

# Note: This will fail because middleware.core does not exist yet.
from apelios.middleware.middleware_core import MappingMiddleware

@pytest.fixture
def middleware():
    """
    Provides a MappingMiddleware instance with a hardcoded mock profile.
    This allows us to test the math before we build the JSON loader.
    """
    mock_profile = {
        "fader.1": {
            "target": "group1.dimmer", 
            "type": "absolute"
        },
        "mouse.x": {
            "target": "group1.pan", 
            "type": "absolute_to_delta", 
            "sensitivity": 0.01
        }
    }
    return MappingMiddleware(profile=mock_profile)


def test_core_absolute_mapping(middleware):
    """Tests that a direct 1:1 hardware fader updates the virtual output."""
    
    # 1. ACT: NATS subscriber receives fader pushed to 75%
    middleware.handle_input(source="fader.1", value=0.75)
    
    # 2. ASSERT PRE-FRAME: Virtual state must not change until the 60Hz tick
    assert "group1.dimmer" not in middleware.virtual_output_state
    
    # 3. ACT: The 60Hz loop fires
    middleware.process_frame()
    
    # 4. ASSERT POST-FRAME: Output is updated
    assert middleware.virtual_output_state["group1.dimmer"] == 0.75


def test_core_absolute_to_delta_with_async_overwrites(middleware):
    """
    Tests the 'Local Snapshot' pattern. 
    Simulates the NATS thread rapidly overwriting the current state without locks.
    """
    
    # 1. ARRANGE: Set initial virtual canvas state to perfectly centered (0.5)
    middleware.virtual_output_state["group1.pan"] = 0.5
    
    # Establish the baseline state (e.g., the mouse is currently at tick 5000)
    middleware.handle_input(source="mouse.x", value=5000.0)
    middleware.process_frame()
    
    # 2. ACT: Simulate rapid async NATS inputs between frame ticks
    # The Sub overwrites 'current_raw_input' three times incredibly fast
    middleware.handle_input(source="mouse.x", value=5005.0)
    middleware.handle_input(source="mouse.x", value=5008.0)
    middleware.handle_input(source="mouse.x", value=5010.0) 
    # ^ 5010.0 is the final state the Core will capture in its snapshot
    
    # 3. ACT: The 60Hz loop fires
    middleware.process_frame()
    
    # 4. ASSERT:
    # The Core should calculate: 5010 (snapshot) - 5000 (prev) = 10 delta.
    # Output should be: 0.5 (initial) + (10 delta * 0.01 sensitivity) = 0.6
    
    # Verify the 'previous' state was correctly updated to the snapshot
    assert middleware.previous_raw_input["mouse.x"] == 5010.0
    
    # Verify the math was applied correctly to the virtual output
    assert middleware.virtual_output_state["group1.pan"] == pytest.approx(0.6)