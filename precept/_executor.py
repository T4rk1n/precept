import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor


class AsyncExecutor:
    """Execute function a ThreadPool or ProcessPool."""
    def __init__(self, loop=None, executor=None, max_workers=None):
        self.loop = loop or asyncio.get_event_loop()
        self.lock = asyncio.Lock(loop=loop)
        if executor:  # pragma: no cover
            self.executor = executor
        else:  # pragma: no cover
            self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute(self, func, *args, **kwargs):
        """
        Execute a sync function asynchronously in the executor.

        :param func: Synchronous function.
        :param args:
        :param kwargs:
        :return:
        """
        return await self.loop.run_in_executor(
            self.executor,
            functools.partial(func, *args, **kwargs)
        )

    # pragma: no cover
    async def execute_with_lock(self, func, *args, **kwargs):
        """
        Acquire lock before executing the function.

        :param func: Synchronous function.
        :param args:
        :param kwargs:
        :return:
        """
        await self.lock.acquire()
        ret = await self.execute(func, *args, **kwargs)
        self.lock.release()
        return ret
