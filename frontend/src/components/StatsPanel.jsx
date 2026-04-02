const stats = [
  { label: "Total Reviews", value: "0" },
  { label: "Unique Reviewers", value: "0" },
  { label: "Cartels Detected", value: "0" },
  { label: "Largest Cartel", value: "0" }
];

export default function StatsPanel() {
  return (
    <section className="section-card">
      <div className="stats-grid">
        {stats.map((stat) => (
          <article className="stat-card" key={stat.label}>
            <span className="stat-value">{stat.value}</span>
            <span className="stat-label">{stat.label}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
