# Apelios

Apelios is an open-source, modular, soft real-time control system for moving-head
lighting fixtures. It aims to make remote follow-spot control more accessible
and provides an alternative to commercial systems.

It reads normalized controller input, maps it to fixture parameters, converts
those parameters to DMX values, and publishes the result over Art-Net.

The current reference setup targets a Steam Deck, but the input, routing,
fixture, and output layers can be replaced or extended independently. In
particular, the input and output layers use adapters so that support for new
hardware and protocols can be added without changing the rest of the pipeline.

## Architecture

Apelios processes data through four asynchronous layers connected by a message
broker:

```text
hardware -> input-layer -> router-layer -> fixture-layer -> output-layer -> Art-Net
```

Communication between the layers runs through the NATS message broker.

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
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Linux for the current hardware input adapters and process-management behavior
- Network access to the Art-Net target when using real lighting hardware

The Python environment installs a bundled `nats-server` executable through
`nats-server-bin`.

## Installation

```bash
git clone https://github.com/weber-moritz/apelios.git
cd apelios
uv sync
```

For development and performance tooling:

```bash
uv sync --all-extras
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
uv run python -m apelios.main_orchestrator
```

Stop the process with `Ctrl+C`. Apelios shuts down its adapters and bundled NATS
server during normal termination.

## Tests

Install the development dependencies, then run:

```bash
uv run pytest
```

Tests marked `integration` or `e2e` start or connect to supporting services. The
performance framework has additional usage documentation in
[`tools/performance`](tools/performance).

## Project status

Apelios is a work-in-progress prototype. Configuration formats, adapter
interfaces, and public contracts may change while the system is being refined.

## License

Apelios is available under the [MIT License](LICENSE).
