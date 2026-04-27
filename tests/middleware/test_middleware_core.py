import pytest
from apelios.middleware.middleware_core import MappingMiddleware

@pytest.fixture
def middleware():
    mock_profile = {
        "fader.1": {
            "target": "group1.dimmer", 
            "type": "absolute",
            "axis_type": "unipolar"
        },
        "mouse.x": {
            "target": "group1.pan", 
            "type": "delta", 
            "sensitivity": 0.01,
            "axis_type": "bipolar"
        },
        "joystick.1": {
            "target": "group1.tilt", 
            "type": "rate", 
            "sensitivity": 0.4,
            "axis_type": "bipolar",
            "deadzone": 0.05
        },
        "joystick.2": {
            "target": "group1.tilt", 
            "type": "rate", 
            "sensitivity": 0.2,
            "axis_type": "bipolar",
            "deadzone": 0.07
        },
        "joystick.3": {
            "target": "group1.tilt", 
            "type": "rate", 
            "sensitivity": 0.1,
            "axis_type": "bipolar",
            "deadzone": 0.1
        }
    }
    return MappingMiddleware(profile=mock_profile)


def test_core_absolute_mapping(middleware):
    middleware.handle_input(source="fader.1", value=0.75)
    assert "group1.dimmer" not in middleware.virtual_output_state
    
    middleware.process_frame(dt=0.016) # Passed standard 60hz dt
    assert middleware.virtual_output_state["group1.dimmer"] == 0.75


def test_core_delta_with_async_overwrites(middleware):
    #prime the prev state:
    middleware.handle_input(source="mouse.x", value=5000.0)
    middleware.process_frame(dt=0.016)
    
    middleware.virtual_output_state["group1.pan"] = 0.5
    middleware.handle_input(source="mouse.x", value=5000.0)
    middleware.process_frame(dt=0.016)
    
    middleware.handle_input(source="mouse.x", value=5005.0)
    middleware.handle_input(source="mouse.x", value=5008.0)
    middleware.handle_input(source="mouse.x", value=5010.0) 
    
    middleware.process_frame(dt=0.016)
    
    assert middleware.previous_abs_input["mouse.x"] == 5010.0
    # 0.5 + ((5010 - 5000) * 0.01) = 0.6
    assert middleware.virtual_output_state["group1.pan"] == pytest.approx(0.6)


def test_core_rate_mapping_with_delta_time(middleware):
    """Test that a rate axis continuously adds to the state based on time."""
    #prime the prev state
    middleware.handle_input(source="joystick.1", value=0)
    middleware.process_frame(dt=0.016)
    
    
    # 1. ARRANGE: Set initial state
    middleware.virtual_output_state["group1.tilt"] = 0.5
    
    # 2. ACT: Hold the joystick steadily at 0.75 for 10 frames
    middleware.handle_input(source="joystick.1", value=0.75)
    
    dt = 0.016  # standard 60Hz tick
    frames_passed = 10
    
    for _ in range(frames_passed):
        middleware.process_frame(dt=dt)
        
    # 3. ASSERT:
    # calculation: value (0.75) * sensitivity (0.4) * dt (0.016) = 0.0048 per frame
    # 0.0048 * 10 frames = 0.048 total change
    expected_output = 0.5 + 0.048
    
    assert middleware.virtual_output_state["group1.tilt"] == pytest.approx(expected_output)



def test_core_deadzone_on_bipolar_axis(middleware):
    """Test that a joystick resting slightly off-center snaps to exactly 0.0."""
    #prime the prev state
    middleware.handle_input(source="joystick.1", value=0)
    middleware.process_frame(dt=0.016)
    
    # Set an initial state so we can see if it drifts
    middleware.virtual_output_state["group1.tilt"] = 0.5
    
    # Joystick is resting at 0.03, which is inside the 0.05 center deadzone
    middleware.handle_input(source="joystick.1", value=0.03)
    middleware.process_frame(dt=0.016)
    
    # Since the deadzone snapped the value to 0.0, the rate math added 0.0. 
    # State should remain exactly 0.5 without drifting.
    assert middleware.virtual_output_state["group1.tilt"] == 0.5
    
    
def test_core_clamping_prevents_out_of_bounds(middleware):
    """Test that delta and rate math never exceed 1.0 or drop below 0.0."""
    
    # --- TEST 1: Clamp Upper Bound (1.0) ---
    middleware.virtual_output_state["group1.pan"] = 0.95
    
    # Send a massive delta that would push the value to 1.5
    middleware.handle_input(source="mouse.x", value=5000.0)
    middleware.process_frame(dt=0.016)
    middleware.handle_input(source="mouse.x", value=5050.0) # Delta of +50
    middleware.process_frame(dt=0.016)
    
    # The math says 0.95 + (50 * 0.01) = 1.45. 
    # The Core MUST clamp this to 1.0.
    assert middleware.virtual_output_state["group1.pan"] == 1.0

    # --- TEST 2: Clamp Lower Bound (0.0) ---
    #prime the prev state:
    middleware.handle_input(source="joystick.1", value=0)
    middleware.process_frame(dt=0.016)
    
    
    middleware.virtual_output_state["group1.tilt"] = 0.05
    
    # Hold the joystick full reverse for a long time
    middleware.handle_input(source="joystick.1", value=-1.0)
    
    # Process 60 frames (1 second). 
    # Math: 0.05 + (-1.0 * 0.4 sensitivity * 0.016 * 60) = -0.334
    for _ in range(60):
        middleware.process_frame(dt=0.016)
        
    # The Core MUST clamp this to 0.0.
    assert middleware.virtual_output_state["group1.tilt"] == 0.0
    
    
def test_core_multiple_input_accumulation(middleware):
    """Test that multiple inputs targeting the same output accumulate correctly."""
    
    # prime the prv values:
    middleware.handle_input(source="joystick.1", value=0) # sens 0.4
    middleware.handle_input(source="joystick.2", value=0) # sens 0.2
    middleware.handle_input(source="joystick.3", value=0) # sens 0.1
    
    dt = 0.016
    middleware.process_frame(dt=dt)
    
    # Set initial output state
    middleware.virtual_output_state["group1.tilt"] = 0.2
    
    # 2. ACT: Push all three joysticks halfway
    middleware.handle_input(source="joystick.1", value=0.5) # sens 0.4
    middleware.handle_input(source="joystick.2", value=0.5) # sens 0.2
    middleware.handle_input(source="joystick.3", value=0.5) # sens 0.1
    
    middleware.process_frame(dt=dt)
    
    # 3. ASSERT: Math Breakdown
    # Formula: new_state = old_state + (change1) + (change2) + (change3)
    # Change formula for 'rate': value * sensitivity * dt
    # j1_change = 0.5 * 0.4 * 0.016 = 0.0032
    # j2_change = 0.5 * 0.2 * 0.016 = 0.0016
    # j3_change = 0.5 * 0.1 * 0.016 = 0.0008
    # Total change = 0.0056
    # Expected output = 0.2 + 0.0056 = 0.2056
    
    expected_output = 0.2 + (0.5 * 0.4 * dt) + (0.5 * 0.2 * dt) + (0.5 * 0.1 * dt)
    
    assert middleware.virtual_output_state["group1.tilt"] == pytest.approx(expected_output)
    

def test_core_first_delta_value_primes_state_without_output(middleware):
    # first delta sample should only set baseline, not move output
    middleware.handle_input(source="mouse.x", value=200.0)

    middleware.process_frame(dt=0.016)

    assert "group1.pan" not in middleware.virtual_output_state
    assert middleware.previous_abs_input["mouse.x"] == 200.0


def test_core_first_rate_value_primes_state_without_output(middleware):
    # first rate sample should prime state and not create an output jump
    middleware.virtual_output_state["group1.tilt"] = 0.5
    middleware.handle_input(source="joystick.1", value=0.75)

    middleware.process_frame(dt=0.016)

    assert middleware.virtual_output_state["group1.tilt"] == 0.5
    assert middleware.previous_abs_input["joystick.1"] == 0.0