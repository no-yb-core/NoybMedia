import typer

app = typer.Typer(
    name="noybmedia",
    help="Download Wistia videos you are authorized to access.",
)


@app.command()
def main() -> None:
    """Display the NoybMedia CLI welcome message."""
    typer.echo("NoybMedia — Wistia video downloader")


if __name__ == "__main__":
    app()
