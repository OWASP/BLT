from workers import WorkerEntrypoint, Response

class Default(WorkerEntrypoint):
    def fetch(self, request):
        return Response.json({"message": "Hello World!"})