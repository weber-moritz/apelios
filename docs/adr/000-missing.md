A runtime/orchestrator ADR for startup order, shutdown order, and dependency injection. That belongs in the same family as src/apelios/main_orchestrator.py.
A broker abstraction ADR for why the broker is split into runtime manager plus client facade, and why the orchestrator owns the server lifecycle. That captures the design behind src/apelios/broker/broker_runtime_manager.py and src/apelios/broker/broker_client.py.
A middleware state-model ADR for how raw input, previous input, and virtual output state are separated inside the core. That is the actual control-theory heart of src/apelios/middleware/middleware_core.py.
An output contract ADR for how processed state becomes broker output subjects and payloads. That documents src/apelios/middleware/middleware_output_publisher.py.
A configuration ADR for why mappings live in JSON and how profile changes are applied without code changes. That explains the “control table” idea behind the middleware.
A testing strategy ADR for why you use unit tests with mocks, integration tests with NATS, and what each layer is allowed to depend on. For a thesis, this is useful because it shows how you proved the architecture.
A plugin/device model ADR for how concrete adapters should be written on top of the base input adapter, including the rule that they stay stateless and only publish normalized events.

“GUI as a separate broker-speaking client, not an input adapter”
why it exists
what it subscribes to
what it may publish
whether video streaming is inside the same app or a separate service
So the line is:

Steam Deck / keyboard / mouse / Xbox controller = input adapters
GUI dashboard / control panel / stream viewer = separate client application

What makes it worth keeping as a module:

It uses the same broker and the same event contract.
It should start and stop with the same orchestrator or with a closely related runtime.
It shares domain concepts like mappings, device status, ping, and stream state.
You want one repository to keep the thesis story and system design coherent.
What makes it worth extracting later:

The video stream needs a different runtime, dependencies, or process model.
The GUI becomes large enough that UI changes slow down input/middleware work.
You want to run or deploy the GUI independently from the core pipeline.
So the pragmatic path is:

make GUI its own top-level module in the repo,
give it its own runtime manager if needed,
keep it out of input,
let it talk to the broker like everything else,
only split it into a separate repo if it really stops being part of the same system.