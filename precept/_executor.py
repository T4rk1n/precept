import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor


class AsyncExecutor:
    """Execute functions in a Pool Executor"""
    def __init__(self, loop=None, executor=None, max_workers=None):
        """
        :param loop: asyncio event loop.
        :param executor: Set to use an already existing PoolExecutor, default
            to a new ThreadPoolExecutor if not supplied.
        :param max_workers: Max workers of the created ThreadPoolExecutor.
        """
        self.loop = loop or asyncio.get_event_loop()
        self.lock = asyncio.Lock(loop=loop)
        if executor:  # pragma: no cover
            self.executor = executor
        else:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute(self, func, *args, **kwargs):
        """
        Execute a sync function asynchronously in the executor.

        :param func: Synchronous function.
        :param args: Argument to give to the function.
        :param kwargs: Keyword arguments to give to the function
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

    def wraps(self, func):
        """
        Wraps a synchronous function to execute in the pool when called,
        making it async.

        :param func: The function to wraps
        :return: Async wrapped function.
        """

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.execute(func, *args, **kwargs)

        return wrapper
