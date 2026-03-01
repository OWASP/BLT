from worker import WorkerEntrypoint

class Default(WorkerEntrypoint):
    def on_fetch(self, request):
        return "Hello World!"