from __future__ import annotations

from neosentinel.report.provider import ClusterReportData


def render_cluster_report_html(data: ClusterReportData) -> str:
    status = "HEALTHY"
    if data.unhealthy_node_count > 0:
        status = "UNHEALTHY"
    elif data.degraded_node_count > 0:
        status = "DEGRADED"

    decision_rows = "".join(
        f"<tr><td>{item.timestamp.isoformat()}</td>"
        f"<td>{item.node_id}</td>"
        f"<td>{item.action.value}</td>"
        f"<td>{item.confidence:.2f}</td></tr>"
        for item in data.decisions[:20]
    )
    healing_rows = "".join(
        f"<tr><td>{item.timestamp.isoformat()}</td>"
        f"<td>{item.node_id}</td>"
        f"<td>{item.action.value}</td>"
        f"<td>{item.status}</td></tr>"
        for item in data.healing_events[:20]
    )
    checkpoint_rows = "".join(
        f"<tr><td>{item.checkpoint_id}</td>"
        f"<td>{item.node_id}</td>"
        f"<td>{item.action.value}</td></tr>"
        for item in data.checkpoints[:20]
    )

    return (
        "<html><head><title>NeoSentinel Cluster Report</title>"
        "<style>body{font-family:sans-serif;margin:2rem}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ccc;padding:0.5rem}</style></head><body>"
        "<h1>NeoSentinel Cluster Health &amp; Audit Report</h1>"
        f"<p>Cluster: <strong>{data.cluster_id}</strong></p>"
        f"<p>Generated: {data.generated_at.isoformat()}</p>"
        f"<p>Status: <strong>{status}</strong></p>"
        f"<p>Nodes &mdash; healthy: {data.healthy_node_count}, "
        f"degraded: {data.degraded_node_count}, "
        f"unhealthy: {data.unhealthy_node_count}</p>"
        "<h2>Recent Decisions</h2><table>"
        "<tr><th>Timestamp</th><th>Node</th><th>Action</th><th>Confidence</th></tr>"
        f"{decision_rows or '<tr><td colspan=4>No decisions recorded</td></tr>'}"
        "</table>"
        "<h2>Healing Events</h2><table>"
        "<tr><th>Timestamp</th><th>Node</th><th>Action</th><th>Status</th></tr>"
        f"{healing_rows or '<tr><td colspan=4>No healing events recorded</td></tr>'}"
        "</table>"
        "<h2>Checkpoints</h2><table>"
        "<tr><th>Checkpoint</th><th>Node</th><th>Action</th></tr>"
        f"{checkpoint_rows or '<tr><td colspan=3>No checkpoints recorded</td></tr>'}"
        "</table>"
        "<p>Graviton4 Control Plane Nominal</p></body></html>"
    )
