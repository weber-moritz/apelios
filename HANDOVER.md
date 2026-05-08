# Handover: Next Input Layer Slice

**State of play**
- The base input adapter slice is done and tested.
- The current contract is stable: input adapters publish `{"source": "device.axis", "value": float}` through `InputPublisher`.
- The ADR was updated to match the live contract.

**What is already true**
- [src/apelios/input/base_input_adapter.py](/path/to/apelios/src/apelios/input/base_input_adapter.py) provides the stateless adapter lifecycle helper.
- [tests/input/test_base_input_adapter.py](/path/to/apelios/tests/input/test_base_input_adapter.py) covers start, stop, publish, and idempotency.
- The focused test suite passes in the project venv.

**Next day goal**
Build a fake or mock input adapter first, then use it to improve the input-layer tests before touching real hardware adapters.

**Recommended next steps**
1. Add a fake adapter implementation in the tests or a small test helper module.
   - It should inherit from `BaseInputAdapter`.
   - It should simulate one poll cycle by calling `publish()` a few times.
   - Keep it stateless.
2. Add a runtime-manager test that starts the fake adapter and verifies publisher injection.
3. Add one adapter contract test that proves multiple `publish()` calls happen from one fake poll.
4. Only after that, start the first real adapter.
   - Keyboard or mouse is probably the easiest first real source.
   - Steam Deck and Xbox controller can come later.
5. Add the first input-layer integration test after one real adapter exists.
   - Adapter -> broker client -> middleware subscriber.

**Open questions to resolve later**
- Whether the GUI stays in this repo as a separate module or becomes its own project.
- Which real adapter should be first: keyboard or mouse is likely simpler than Steam Deck or controller.

**Reminder for tomorrow**
- Start with the fake adapter and the tests around it.
- Do not jump straight to end-to-end coverage; keep the slice narrow.
