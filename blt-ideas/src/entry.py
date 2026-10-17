from workers import WorkerEntrypoint


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await self.env.ASSETS.fetch(request)
