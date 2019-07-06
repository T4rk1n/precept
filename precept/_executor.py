import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from precept import is_windows


class AsyncExecutor:
    """Execute function a ThreadPool or ProcessPool."""
    def __init__(self, loop=None, executor=None):
        self.loop = loop or asyncio.get_event_loop()
        self.global_lock = asyncio.Lock(loop=loop)
        if executor:
            self.executor = executor
        elif is_windows():  # pragma: no cover
            # Processes don't work good with windows.
            self.executor = ThreadPoolExecutor()
        else:  # pragma: no cover
            self.executor = ProcessPoolExecutor()

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
        await self.global_lock.acquire()
        ret = await self.execute(func, *args, **kwargs)
        self.global_lock.release()
        return ret
