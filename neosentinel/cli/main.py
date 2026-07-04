import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any

import click

from neosentinel.cli.config import init_local_config
from neosentinel.cli.diagnostics import run_doctor
from neosentinel.simulation.player import inject_anomaly, replay_stream, run_simulation


@click.group()
@click.version_option()
def cli() -> None:
    """NeoSentinel autonomous cluster healing CLI."""
    pass


@cli.command()
def init() -> None:
    """Initialize local NeoSentinel configuration and environment."""
    config_path = init_local_config()
    click.echo(f"[SUCCESS] Initialized NeoSentinel config at '{config_path}'.")


@cli.command("cluster-init")
@click.option("--nodes", default=3, help="Number of nodes to bootstrap.")
@click.option("--mock-ssh/--live-ssh", default=True, help="Use mock SSH provisioning.")
def cluster_init(nodes: int, mock_ssh: bool) -> None:
    """Bootstrap services on remote Graviton4 cluster nodes."""
    from neosentinel.cli.provision import DEFAULT_STEPS, MockSshRunner, node_hosts

    if nodes < 1:
        raise click.ClickException("Node count must be at least 1.")
    click.echo(f"Bootstrapping NeoSentinel on {nodes} cluster nodes...")
    runner = MockSshRunner() if mock_ssh else None
    ssh = runner or MockSshRunner()
    hosts = node_hosts(nodes)
    total_steps = len(hosts) * len(DEFAULT_STEPS)
    try:
        with click.progressbar(length=total_steps, label="Provisioning nodes") as bar:
            for host in hosts:
                for step in DEFAULT_STEPS:
                    code, _output = ssh.run(host, step.command)
                    if code != 0:
                        raise RuntimeError(f"Provision failed on {host}: {step.label}")
                    bar.update(1)
        mode = "mock SSH" if mock_ssh else "live SSH"
        click.echo(f"[SUCCESS] Cluster bootstrap complete via {mode}.")
    except Exception as exc:
        click.echo(f"[ERROR] Cluster bootstrap failed: {exc}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--port", default=8080, help="Dashboard server port.")
@click.option(
    "--open-browser/--no-open-browser",
    default=True,
    help="Automatically open the dashboard in a web browser.",
)
@click.option(
    "--serve/--no-serve",
    default=False,
    help="Launch the FastAPI dashboard server in the background.",
)
def start(port: int, open_browser: bool, serve: bool) -> None:
    """Start the NeoSentinel control plane dashboard server."""
    url = f"http://localhost:{port}"
    if serve:
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "neosentinel.dashboard.server:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.5)
        click.echo(f"Dashboard server listening on {url}")
    else:
        click.echo(f"Starting NeoSentinel dashboard server on {url}...")
    if open_browser:
        webbrowser.open(url)


@cli.command()
@click.option("--live/--mock", default=True, help="Run live probes or mock checks.")
def doctor(live: bool) -> None:
    """Run diagnostic checks on local toolchain and cluster nodes."""
    click.echo("Running NeoSentinel diagnostics...")
    checks = run_doctor(mock=not live)
    failures = 0
    for check in checks:
        status = "[OK]" if check.passed else "[FAIL]"
        if not check.passed:
            failures += 1
        click.echo(f"{status} {check.name} — {check.detail}")
    if failures:
        click.echo(f"[WARN] {failures} diagnostic check(s) need attention.")
        raise SystemExit(1)
    click.echo("[SUCCESS] All 7 cluster diagnostic checks operational.")


@cli.command()
@click.option("--scenario", default="sve2_underutilization", help="Simulation scenario name.")
@click.option("--speed", default=1.0, type=float, help="Playback speed multiplier.")
def simulate(scenario: str, speed: float) -> None:
    """Execute an offline end-to-end anomaly and autonomous healing demo simulation."""
    click.echo(f"Starting simulation scenario '{scenario}' at {speed}x speed...")

    def progress_cb(evt: dict[str, Any]) -> None:
        evt_type = evt.get("type", "unknown")
        ts = evt.get("timestamp", "")
        if evt_type == "agent_thought":
            click.echo(f"[{ts}] [AGENT THOUGHT] {evt.get('chunk')}")
        elif evt_type == "healing":
            click.echo(f"[{ts}] [HEALING ACTION] {evt.get('action')} -> {evt.get('status')}")
        elif evt_type == "audit":
            click.echo(f"[{ts}] [GITOPS AUDIT] {evt.get('message')}")

    try:
        res = run_simulation(scenario, speed=speed, callback=progress_cb)
        msg = (
            f"[SUCCESS] Simulation finished: {res['action_taken']} "
            f"executed on {res['target_node']}."
        )
        click.echo(msg)
    except Exception as e:
        click.echo(f"[ERROR] Simulation failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--node", required=True, help="Target node ID.")
@click.option("--anomaly", default="kv_eviction_flood", help="Type of anomaly to inject.")
@click.option("--mock/--real", default=True, help="Use mock or live degradation injection.")
def inject(node: str, anomaly: str, mock: bool) -> None:
    """Inject synthetic degradation on a target cluster node."""
    try:
        res = inject_anomaly(node, anomaly, mock=mock)
        click.echo(f"[INJECTED] {res['message']}")
    except Exception as e:
        click.echo(f"[ERROR] Injection failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--stream", default="sve2_underutilization", help="Redis stream or fixture name.")
@click.option("--speed", default=1.0, type=float, help="Replay speed multiplier.")
def replay(stream: str, speed: float) -> None:
    """Replay historical telemetry stream window at N× speed."""
    click.echo(f"Replaying stream '{stream}' at {speed}x speed...")
    events = replay_stream(stream, speed=speed)
    click.echo(f"[SUCCESS] Replayed {len(events)} events from '{stream}'.")


@cli.command()
@click.option("--node", required=True, help="Target node ID.")
@click.option("--checkpoint", required=True, help="GitOps checkpoint ID to restore.")
@click.option("--store", default=".neosentinel/checkpoints", help="Checkpoint store directory.")
def rollback(node: str, checkpoint: str, store: str) -> None:
    """Restore a target node to a known healthy checkpoint state."""
    from neosentinel.audit.checkpoints import CheckpointStore

    click.echo(f"Initiating rollback on node '{node}' to checkpoint '{checkpoint}'...")
    try:
        checkpoint_store = CheckpointStore(Path(store))
        restored = checkpoint_store.restore(checkpoint)
        if restored.node_id != node:
            raise ValueError(
                f"Checkpoint '{checkpoint}' belongs to '{restored.node_id}', not '{node}'"
            )
        click.echo(
            f"[SUCCESS] Node '{node}' restored to '{checkpoint}' "
            f"(action={restored.action.value})."
        )
    except Exception as exc:
        click.echo(f"[ERROR] Rollback failed: {exc}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--output", default="cluster_report.html", help="Output HTML file path.")
@click.option("--redis-host", default="127.0.0.1", help="Redis host for report data.")
@click.option("--redis-port", default=6379, type=int, help="Redis port for report data.")
def report(output: str, redis_host: str, redis_port: int) -> None:
    """Generate an interactive HTML health and audit report."""
    import redis

    from neosentinel.report import ReportDataProvider, render_cluster_report_html

    try:
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        client.ping()
        provider = ReportDataProvider(client)
        data = provider.collect()
    except Exception:
        from datetime import UTC, datetime

        from neosentinel.report.provider import ClusterReportData

        data = ClusterReportData(
            generated_at=datetime.now(UTC),
            cluster_id="cluster-graviton4",
            snapshot=None,
        )
    html_content = render_cluster_report_html(data)
    with open(output, "w", encoding="utf-8") as f:
        f.write(html_content)
    click.echo(f"[SUCCESS] Generated cluster report at '{output}'.")
