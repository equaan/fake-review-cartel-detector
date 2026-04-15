import { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";

export default function NetworkGraph({
  nodes,
  edges,
  highlightedIds = [],
  onNodeClick
}) {
  const svgRef = useRef(null);
  const tooltipRef = useRef(null);
  const highlightedSet = useMemo(() => new Set(highlightedIds), [highlightedIds]);

  useEffect(() => {
    const svgElement = svgRef.current;
    if (!svgElement) {
      return undefined;
    }

    const width = svgElement.clientWidth || 960;
    const height = svgElement.clientHeight || 560;
    const svg = d3.select(svgElement);
    svg.selectAll("*").remove();
    svg.attr("viewBox", [0, 0, width, height]);

    const defs = svg.append("defs");
    const filter = defs.append("filter").attr("id", "cartel-glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "coloredBlur");
    const merge = filter.append("feMerge");
    merge.append("feMergeNode").attr("in", "coloredBlur");
    merge.append("feMergeNode").attr("in", "SourceGraphic");

    const root = svg.append("g");
    const simulationNodes = nodes.map((node) => ({ ...node, id: String(node.id) }));
    const simulationEdges = edges.map((edge) => ({
      ...edge,
      source: String(edge.source),
      target: String(edge.target)
    }));
    const simulation = d3
      .forceSimulation(simulationNodes)
      .force(
        "link",
        d3
          .forceLink(simulationEdges)
          .id((node) => String(node.id))
          .distance(70)
          .strength(0.1)
      )
      .force("charge", d3.forceManyBody().strength(-90))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((node) => Math.max(8, (node.review_count ?? 1) + 4)));

    const zoom = d3
      .zoom()
      .scaleExtent([0.4, 4])
      .on("zoom", (event) => {
        root.attr("transform", event.transform);
      });

    svg.call(zoom);

    const link = root
      .append("g")
      .attr("stroke", "rgba(255, 209, 102, 0.75)")
      .attr("stroke-opacity", 0.8)
      .selectAll("line")
      .data(simulationEdges)
      .join("line")
      .attr("stroke-width", (edge) => Math.min(4, Math.max(1, edge.shared_products / 2)));

    const node = root
      .append("g")
      .selectAll("circle")
      .data(simulation.nodes())
      .join("circle")
      .attr("r", (graphNode) =>
        graphNode.cluster >= 0
          ? Math.min(20, Math.max(5, graphNode.review_count ?? 5))
          : 4
      )
      .attr("fill", (graphNode) => (graphNode.cluster >= 0 ? "#ff4444" : "#555555"))
      .attr("stroke", (graphNode) =>
        highlightedSet.has(graphNode.id) ? "#ffd166" : "rgba(255,255,255,0.35)"
      )
      .attr("stroke-width", (graphNode) => (highlightedSet.has(graphNode.id) ? 3 : 1))
      .attr("filter", (graphNode) => (graphNode.cluster >= 0 ? "url(#cartel-glow)" : null))
      .style("cursor", "pointer")
      .call(
        d3
          .drag()
          .on("start", (event, graphNode) => {
            if (!event.active) {
              simulation.alphaTarget(0.3).restart();
            }
            graphNode.fx = graphNode.x;
            graphNode.fy = graphNode.y;
          })
          .on("drag", (event, graphNode) => {
            graphNode.fx = event.x;
            graphNode.fy = event.y;
          })
          .on("end", (event, graphNode) => {
            if (!event.active) {
              simulation.alphaTarget(0);
            }
            graphNode.fx = null;
            graphNode.fy = null;
          })
      )
      .on("click", (_, graphNode) => onNodeClick?.(graphNode))
      .on("mousemove", (event, graphNode) => {
        const tooltip = tooltipRef.current;
        if (!tooltip) {
          return;
        }

        tooltip.style.opacity = "1";
        tooltip.style.left = `${event.pageX + 14}px`;
        tooltip.style.top = `${event.pageY + 14}px`;
        tooltip.innerHTML = `
          <strong>${graphNode.id}</strong><br />
          Cluster: ${graphNode.cluster}<br />
          Suspicion: ${Math.round((graphNode.suspicion_score ?? 0) * 100)}%
        `;
      })
      .on("mouseleave", () => {
        if (tooltipRef.current) {
          tooltipRef.current.style.opacity = "0";
        }
      });

    simulation.on("tick", () => {
      link
        .attr("x1", (edge) => edge.source.x)
        .attr("y1", (edge) => edge.source.y)
        .attr("x2", (edge) => edge.target.x)
        .attr("y2", (edge) => edge.target.y);

      node.attr("cx", (graphNode) => graphNode.x).attr("cy", (graphNode) => graphNode.y);
    });

    const legend = svg.append("g").attr("transform", `translate(${width - 180}, 28)`);
    legend
      .append("circle")
      .attr("cx", 10)
      .attr("cy", 10)
      .attr("r", 8)
      .attr("fill", "#ff4444")
      .attr("filter", "url(#cartel-glow)");
    legend
      .append("text")
      .attr("x", 28)
      .attr("y", 14)
      .attr("fill", "#effaf5")
      .text("Cartel member");
    legend
      .append("circle")
      .attr("cx", 10)
      .attr("cy", 40)
      .attr("r", 6)
      .attr("fill", "#555555");
    legend
      .append("text")
      .attr("x", 28)
      .attr("y", 44)
      .attr("fill", "#effaf5")
      .text("Genuine reviewer");

    return () => {
      simulation.stop();
    };
  }, [edges, highlightedSet, nodes, onNodeClick]);

  return (
    <section className="section-card graph-card">
      <div className="graph-heading">
        <div>
          <h2>Cartel Network View</h2>
          <p>
            Reviewer nodes and shared-product links. Click a node to inspect its
            review history.
          </p>
        </div>
        <div className="graph-metadata">
          <span>{nodes.length} nodes</span>
          <span>{edges.length} edges</span>
        </div>
      </div>
      {nodes.length === 0 ? (
        <div className="empty-state">
          <p>No cartel graph data yet. Generate cluster labels on the stronger PC and refresh this app.</p>
        </div>
      ) : (
        <div className="graph-shell">
          <svg ref={svgRef} className="graph-canvas" />
          <div ref={tooltipRef} className="graph-tooltip" />
        </div>
      )}
    </section>
  );
}
