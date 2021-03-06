import asyncio
import pytest


# noinspection PyProtectedMember
# pylint: disable=inconsistent-return-statements
@pytest.mark.tryfirst
def pytest_pyfunc_call(pyfuncitem):
    """Run tests marked as async in the loop."""
    for marker in pyfuncitem.own_markers:
        if marker.name == 'async_test':
            loop = asyncio.get_event_loop()
            task = loop.create_task(pyfuncitem.obj(**{
                k: pyfuncitem.funcargs[k]
                for k in pyfuncitem._fixtureinfo.argnames
            }))
            loop.run_until_complete(task)
            return True
