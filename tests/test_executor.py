import pytest

from precept import AsyncExecutor


@pytest.mark.async_test
async def test_executor_wraps():
    executor = AsyncExecutor()

    @executor.wraps
    def plus_one(num):
        return num + 1

    three = await plus_one(2)
    assert three == 3
