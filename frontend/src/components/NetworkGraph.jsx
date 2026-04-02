export default function NetworkGraph({ nodes, edges }) {
  return (
    <section className="section-card graph-placeholder">
      <div className="graph-copy">
        <h2>Cartel Network View</h2>
        <p>
          Interactive D3 visualization will live here once the API and dataset
          are connected.
        </p>
        <p>
          Current scaffold includes {nodes.length} sample nodes and {edges.length} sample edge.
        </p>
        <div className="graph-preview" aria-hidden="true" />
      </div>
    </section>
  );
}
