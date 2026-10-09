from typer.testing import CliRunner

from noybmedia.cli import app

runner = CliRunner()


def test_cli_displays_welcome_message() -> None:
    result = runner.invoke(app)

    assert result.exit_code == 0
    assert "NoybMedia" in result.stdout
    assert "Wistia video downloader" in result.stdout
