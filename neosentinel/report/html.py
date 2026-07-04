"""Render a ``ClusterReport`` to a self-contained HTML document.

Kept deliberately dependency-free (string templating + ``html.escape``) so the
report generates identically on a laptop or a Graviton4 node with no extra
packages.
"""

from __future__ import annotations

from html import escape

from neosentinel.report.provider import ClusterReport

_STATUS_COLOR = {"HEALTHY": "#16a34a", "DEGRADED": "#d97706", "CRITICAL": "#dc2626"}


def _node_rows(report: ClusterReport) -> str:
    rows = []
    for n in report.nodes:
        rows.append(
            "<tr>"
            f"<td class='mono'>{escape(n.node_id)}</td>"
            f"<td>{escape(str(n.status))}</td>"
            f"<td>{n.ttft_p99_ms:.0f} ms</td>"
            f"<td>{n.tokens_per_sec:.1f} tok/s</td>"
            f"<td>{n.sve2_utilization_pct:.0f}%</td>"
            f"<td>{n.dram_bandwidth_pct:.0f}%</td>"
            f"<td>{n.requests_per_min:.0f}/min</td>"
            f"<td class='mono'>{escape(n.top_hotspot or '—')}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _audit_rows(report: ClusterReport) -> str:
    if not report.audit:
        return "<tr><td colspan='5'>No audit entries in window.</td></tr>"
    rows = []
    for a in report.audit:
        rows.append(
            "<tr>"
            f"<td class='mono'>{escape(a.timestamp.isoformat())}</td>"
            f"<td class='mono'>{escape(a.short_sha)}</td>"
            f"<td class='mono'>{escape(a.node_id)}</td>"
            f"<td>{escape(a.action)}</td>"
            f"<td>{escape(a.message)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_report_html(report: ClusterReport) -> str:
    """Build a complete HTML report document from a ``ClusterReport``."""
    color = _STATUS_COLOR.get(report.overall_status, "#334155")
    h = report.healing
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>NeoSentinel Cluster Report</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 2rem;
         background: #0b0f17; color: #e2e8f0; }}
  h1 {{ font-size: 1.4rem; margin: 0 0 .25rem; }}
  .headline {{ color: {color}; font-weight: 600; margin: 0 0 1.5rem; }}
  .badge {{ display: inline-block; padding: .15rem .6rem; border-radius: 999px;
            background: {color}; color: #fff; font-size: .8rem; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; margin: .5rem 0 2rem; font-size: .9rem; }}
  th, td {{ text-align: left; padding: .4rem .6rem; border-bottom: 1px solid #1e293b; }}
  th {{ color: #94a3b8; text-transform: uppercase; font-size: .72rem; letter-spacing: .05em; }}
  .mono {{ font-family: ui-monospace, Menlo, monospace; }}
  .grid {{ display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 1.5rem; }}
  .kpi small {{ display: block; color: #94a3b8; text-transform: uppercase; font-size: .7rem; }}
  .kpi b {{ font-size: 1.3rem; }}
  footer {{ color: #64748b; font-size: .75rem; margin-top: 2rem; }}
</style>
</head>
<body>
  <h1>NeoSentinel Cluster Health & Audit Report</h1>
  <p class="headline">{escape(report.headline)}</p>
  <p><span class="badge">{escape(report.overall_status)}</span>
     &nbsp;{escape(report.cluster_id)} · generated {escape(report.generated_at.isoformat())}</p>

  <div class="grid">
    <div class="kpi"><small>Nodes</small><b>{report.total_nodes}</b></div>
    <div class="kpi"><small>Healthy</small><b>{report.healthy_nodes}/{report.total_nodes}</b></div>
    <div class="kpi"><small>Heals</small><b>{h.total}</b></div>
    <div class="kpi"><small>Heal success</small><b>{h.success_rate * 100:.0f}%</b></div>
    <div class="kpi"><small>Avg TTFT gain</small><b>{h.avg_ttft_improvement_ms:.0f} ms</b></div>
    <div class="kpi"><small>Avg SVE2 gain</small><b>{h.avg_sve2_gain_pct:.0f}%</b></div>
  </div>

  <h2>Nodes</h2>
  <table>
    <thead><tr>
      <th>Node</th><th>Status</th><th>TTFT p99</th><th>Throughput</th>
      <th>SVE2</th><th>DRAM BW</th><th>Req rate</th><th>Top hotspot</th>
    </tr></thead>
    <tbody>
{_node_rows(report)}
    </tbody>
  </table>

  <h2>GitOps Audit Trail</h2>
  <table>
    <thead><tr>
      <th>Timestamp</th><th>Commit</th><th>Node</th><th>Action</th><th>Message</th>
    </tr></thead>
    <tbody>
{_audit_rows(report)}
    </tbody>
  </table>

  <footer>NeoSentinel · Graviton4 autonomous inference control plane</footer>
</body>
</html>"""
