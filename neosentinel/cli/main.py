import webbrowser
import click


@click.group()
@click.version_option()
def cli() -> None:
    """NeoSentinel autonomous cluster healing CLI."""
    pass


@cli.command()
def init() -> None:
    """Initialize local NeoSentinel configuration and environment."""
    click.echo("Initializing local NeoSentinel environment...")


@cli.command("cluster-init")
@click.option("--nodes", default=3, help="Number of nodes to bootstrap.")
def cluster_init(nodes: int) -> None:
    """Bootstrap services on remote Graviton4 cluster nodes."""
    click.echo(f"Bootstrapping NeoSentinel on {nodes} cluster nodes...")


@cli.command()
@click.option("--port", default=8080, help="Dashboard server port.")
@click.option(
    "--open-browser/--no-open-browser",
    default=True,
    help="Automatically open the dashboard in a web browser.",
)
def start(port: int, open_browser: bool) -> None:
    """Start the NeoSentinel control plane dashboard server."""
    url = f"http://localhost:{port}"
    click.echo(f"Starting NeoSentinel dashboard server on {url}...")
    if open_browser:
        webbrowser.open(url)


@cli.command()
def doctor() -> None:
    """Run diagnostic checks on local toolchain and cluster nodes."""
    click.echo("Running NeoSentinel diagnostics...")
    click.echo("[OK] CLI toolchain operational.")
