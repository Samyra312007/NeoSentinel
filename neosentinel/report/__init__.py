"""Cluster health & audit report data provider (Sahil · Week 6).

Public API consumed by the ``neosentinel report`` CLI and any other renderer.
"""

from neosentinel.report.html import render_report_html
from neosentinel.report.provider import (
    AuditRecord,
    ClusterReport,
    HealingSummary,
    NodeReport,
    build_cluster_report,
    nominal_cluster_report,
)

__all__ = [
    "AuditRecord",
    "ClusterReport",
    "HealingSummary",
    "NodeReport",
    "build_cluster_report",
    "nominal_cluster_report",
    "render_report_html",
]
