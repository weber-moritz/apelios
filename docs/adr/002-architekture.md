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


# layers:

### the fixture mapper
i choose this as i want seperation of concerns from the mapping middleware and the fixture mapping.
the problem is:
- if i use a n absolute input like an fader, it gets transformed into an rate value by the middelware. then it gets send to the fixture layer which converts it to the absolute value.
- if there is a package loss beteen the middleware and the fixture layer, the valuies get out of sync.

- the fix: send an `intent` with the value. intent can be: absolute or rate so that the output layer can decide what to do with it

