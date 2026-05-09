the adapter is a stateless interface between the os and the apelios system. each adapter is linux first but can be expanded to run on other os as well.

the adapter uses a base input adapter class, that implements the basics to avoid code repetition.

the input runtime manager calls the adapter tick function on each tick, the runtime manager tick is called by the main orchestrator.