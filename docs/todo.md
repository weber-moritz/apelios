- fix c4 layer diagram
- add adr files

# inject broker client into middleware
- Add broker_client as optional DI arg on orchestrator.
- If middleware_manager is not injected, build it with that shared client.
- Later, build input_runtime_manager with the same shared client.
