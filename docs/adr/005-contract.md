# the contract:

## the profile for each input map looks like this:

```json
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
    }
}
```

## the contract that the input layer sends:

```json
{
    "source": "fader.1",
    "value": 0.75
}
```

the reason: there are input types that are absolute (like a fader), some send the delta change (like gyro or mouse) and there are joysticks and trigger that send a rate value, that need to be integrated over by time to get a constant change.

bipolar means the trigger can go from -1 to 1. unipolar means 0-1

deadzone and sensitivity is selfexplanetory. the absolute fader does not support either.