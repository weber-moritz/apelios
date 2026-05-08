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


Here's the pragmatic path:

The ADRs are not extra work—they ARE the thesis outline.

Each ADR is a thesis chapter:

Why did you choose this architecture?
What were the trade-offs?
What problem does it solve?
You already have 5 ADRs. Those cover the big decisions. You don't need to document every tiny choice. Focus on the decisions that constrain the system: why broker, why 60Hz, why stateless adapters, why this middleware model.

Stop at "complete" not "perfect."

The 5 ADRs you have + maybe 2-3 more (orchestrator, broker abstraction, middleware state model) = enough for a thesis.
Each one is maybe 300-500 words.
They're meant to be short.
When you write the thesis, the structure writes itself:

Introduction: system vision and design goals
ADR 001-003: foundational choices (broker, architecture, timing)
ADR 004-005: input contract and state model
ADR 006-008: (if you add them) orchestrator, output, testing strategy
Implementation sections: point to the test suites as proof
Conclusion: why this architecture mattered
The thesis is not "write a 50-page paper then make ADRs." It's "finish the ADRs, then write the thesis by explaining them."

My advice:

Trust what you have. The 5 ADRs are solid.
Add only the missing ones that explain major boundaries (orchestrator, middleware state, output contract).
Do not add an ADR for every micro-decision.
Let the tests speak for the "how." The ADRs explain the "why."
You're not overwhelmed. You're just at the point where the system is stable enough to document. That's healthy.