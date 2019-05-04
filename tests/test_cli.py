from precept import CliApp, Command, Argument


class SimpleCli(CliApp):
    result = None

    @Command(
        Argument(
            'foo',
            type=int,
        ),
        Argument(
            '--bar',
            default=3,
            type=int,
        )
    )
    async def simple(self, foo, bar):
        self.result = foo + bar


def test_simple_cli():
    cli = SimpleCli()
    cli.start('--quiet simple 1'.split(' '))

    assert cli.result == 4

    cli.start('--quiet simple 3 --bar 6'.split(' '))
    assert cli.result == 9

