import pytest

from precept import ImmutableDict
from precept.errors import ImmutableError


def test_immutable_dict():
    data = ImmutableDict(foo='bar', bar='foo', n=1)
    assert 'foo' in data
    assert data.get('bar') == 'foo'
    assert data.foo == 'bar'
    assert data['n'] == 1
    assert len(data) == 3

    with pytest.raises(TypeError):
        data['foo'] = 'not foo'

    with pytest.raises(KeyError):
        # pylint: disable=unused-variable
        d = data.dont_exist  # noqa: F841

    with pytest.raises(ImmutableError):
        # pylint: disable=attribute-defined-outside-init
        data.foo = 'not foo'


def test_immutable_props():
    class TestDict(ImmutableDict):
        def __init__(self, foo, bar, keyword='keyword'):
            super(TestDict, self).__init__(foo=foo, bar=bar, keyword=keyword)

    first = TestDict('foo', 'bar')
    assert first.foo == 'foo'
    assert first.bar == 'bar'
    assert first.keyword == 'keyword'
    assert len(first) == 3

    with pytest.raises(ImmutableError) as context:
        # pylint: disable=attribute-defined-outside-init
        first.foo = 'bar'

    assert 'TestDict.foo is immutable' in str(context.value)

    second = TestDict(1, 2, keyword='foobar')
    assert second.keyword == 'foobar'
    assert len(second) == 3
