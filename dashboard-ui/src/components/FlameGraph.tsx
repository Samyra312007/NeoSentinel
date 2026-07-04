import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { HotspotEntry } from '../types/telemetry';

interface FlameGraphProps {
  node_id?: string;
  hotspots: HotspotEntry[];
}

export const FlameGraph: React.FC<FlameGraphProps> = ({ node_id = 'CLUSTER', hotspots }) => {
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const top5 = hotspots.slice(0, 5);
    const width = 600;
    const barHeight = 36;
    const margin = { top: 20, right: 60, bottom: 20, left: 160 };
    const height = margin.top + margin.bottom + top5.length * barHeight;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${width} ${height}`).attr('class', 'w-full h-auto overflow-visible font-mono');

    if (top5.length === 0) {
      svg
        .append('text')
        .attr('x', width / 2)
        .attr('y', margin.top + 30)
        .attr('text-anchor', 'middle')
        .attr('fill', 'var(--text-muted, #71717a)')
        .attr('font-size', '12px')
        .text('[ NO HOTSPOT TELEMETRY CAPTURED // SYSTEM NOMINAL ]');
      return;
    }

    const maxPct = d3.max(top5, (d) => d.samples_pct) || 100;
    const xScale = d3
      .scaleLinear()
      .domain([0, Math.max(100, maxPct)])
      .range([0, width - margin.left - margin.right]);

    const yScale = d3
      .scaleBand()
      .domain(top5.map((d) => d.symbol))
      .range([margin.top, height - margin.bottom])
      .padding(0.2);

    const g = svg.append('g').attr('transform', `translate(${margin.left},0)`);

    // Grid lines
    const xAxisGrid = d3
      .axisTop(xScale)
      .ticks(5)
      .tickSize(-(height - margin.top - margin.bottom))
      .tickFormat(() => '');

    g.append('g')
      .attr('class', 'grid opacity-10')
      .attr('transform', `translate(0,${margin.top})`)
      .call(xAxisGrid)
      .selectAll('line')
      .attr('stroke', '#ffffff');

    // Bars
    const colorScale = d3
      .scaleLinear<string>()
      .domain([0, 50, 100])
      .range(['#06b6d4', '#f59e0b', '#ef4444']);

    const bars = g
      .selectAll('.bar-group')
      .data(top5)
      .enter()
      .append('g')
      .attr('class', 'bar-group')
      .attr('transform', (d) => `translate(0, ${yScale(d.symbol) || 0})`);

    bars
      .append('rect')
      .attr('class', 'bar transition-all duration-300')
      .attr('x', 0)
      .attr('y', 0)
      .attr('height', yScale.bandwidth())
      .attr('width', (d) => xScale(d.samples_pct))
      .attr('fill', (d) => colorScale(d.samples_pct))
      .attr('rx', 2)
      .attr('opacity', 0.85);

    // Module tag labels inside bars
    bars
      .append('text')
      .attr('x', 8)
      .attr('y', yScale.bandwidth() / 2 + 4)
      .attr('fill', '#000000')
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .text((d) => `[${d.module}]`);

    // Percentage value text at the end of bars
    bars
      .append('text')
      .attr('x', (d) => xScale(d.samples_pct) + 8)
      .attr('y', yScale.bandwidth() / 2 + 4)
      .attr('fill', 'var(--text-main, #ffffff)')
      .attr('font-size', '11px')
      .attr('font-weight', 'bold')
      .text((d) => `${d.samples_pct.toFixed(1)}%`);

    // Y-Axis labels (symbols)
    const yAxis = d3.axisLeft(yScale).tickSize(0);
    const yAxisGroup = svg
      .append('g')
      .attr('transform', `translate(${margin.left - 10}, 0)`)
      .call(yAxis);

    yAxisGroup.select('.domain').remove();
    yAxisGroup
      .selectAll('text')
      .attr('fill', 'var(--accent-cyan, #06b6d4)')
      .attr('font-size', '11px')
      .attr('font-family', 'monospace')
      .style('text-anchor', 'end')
      .text((d) => {
        const str = String(d);
        return str.length > 18 ? `${str.slice(0, 16)}...` : str;
      });
  }, [hotspots]);

  return (
    <div className="border border-[var(--border-color)] bg-[var(--card-bg)] p-4 font-mono">
      <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--accent-cyan)] animate-pulse" />
          <h2 className="text-sm font-bold tracking-wider uppercase text-[var(--text-main)]">
            [ TOP-5 HOTSPOT FLAME GRAPH // <span className="text-[var(--accent-amber)]">{node_id}</span> ]
          </h2>
        </div>
        <span className="text-xs text-[var(--text-muted)] uppercase">
          SVE2 PMU PMU-SAMPLING
        </span>
      </div>

      <div className="w-full overflow-x-auto">
        <svg ref={svgRef} className="w-full min-w-[450px]" />
      </div>
    </div>
  );
};
