# Apelios

Apelios is an experimental, low-latency control pipeline for moving-head
lighting fixtures. It reads normalized controller input, routes it to fixture
parameters, converts those parameters to DMX values, and publishes the result
over Art-Net.

The current reference setup targets a Steam Deck and a Lixada Mini Moving Head,
but the input, routing, fixture, and output layers are designed to be replaced or
extended independently.

## Architecture

Apelios processes data through five asynchronous components:

```text
input -> router -> fixture -> output -> Art-Net
             NATS message broker
```

- **Input** samples registered controllers and publishes normalized values.
- **Router** maps input controls to fixture targets.
- **Fixture** converts targets such as pan and tilt into DMX channel values.
- **Output** maintains DMX universes and publishes them through protocol adapters.
- **Broker** connects the layers using NATS; an in-memory implementation is also
  available for isolated tests.

Architectural decisions and diagrams are available in [`docs/adr`](docs/adr) and
[`docs/diagrams`](docs/diagrams).

## Requirements

- Python 3.10 or newer
- Linux for the current hardware input adapters and process-management behavior
- Network access to the Art-Net target when using real lighting hardware

The Python environment installs a bundled `nats-server` executable through
`nats-server-bin`.

## Installation

```bash
git clone <repository-url>
cd apelios
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

For development and performance tooling:

```bash
python -m pip install -e '.[dev,performance]'
```

## Configuration

The checked-in defaults are starting points for the reference hardware:

- Input registration: `src/apelios/input/input_adapter_bootstrap.py`
- Input routing: `src/apelios/router/routing/`
- Fixture patches: `src/apelios/fixture/patch/`
- Art-Net output: `src/apelios/output/config/artnet_config.json`

Review the Art-Net source and target addresses before connecting real fixtures.

## Running

```bash
python -m apelios.main_orchestrator
```

Stop the process with `Ctrl+C`. Apelios shuts down its adapters and bundled NATS
server during normal termination.

## Tests

Install the development dependencies, then run:

```bash
python -m pytest
```

Tests marked `integration` or `e2e` start or connect to supporting services. The
performance framework has additional usage documentation in
[`tools/performance`](tools/performance).

## Project status

Apelios is a research prototype. Configuration formats and public Python APIs may
change while the system is being refined.

## License

Apelios is available under the [MIT License](LICENSE).
