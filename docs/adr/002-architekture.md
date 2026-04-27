# why this architecture?

this architecture is a microkernal/hexagonal architecture.

microkernal means that every module has its own manager (`runtime_manager`) class. It routs information inside the module, and has a start, stop and tick/process function that is called by the `main_orchestrator`.

the architecture in each module is not everywhere the same.
the middleware has a very simple hexagonal architecture.
the broker has 2 modules: the `broker_runtime_manager` and the `broker_client`. the runtime manager gets started/stopped by the main orchestrator. the client gets imported by all modules that require communication.

it would also be possible to use a single client for all modules and pass the reference of that client from the main orchestrator to the modules, but that would conflict with the modularisation that is targetet with this project.

this architecture fulfills the ntr (non-technical-requirements):
**modularization**: each module can be exchanged or changed with minimal changes in the other modules. only the orchestrator knows about the other modules, the modules themselves dont know what other moudles exist in the module.

**stability:** is given through the independend modules. should one not work anymore, would that not affect the other modules.

