import { useEffect, useState } from "react";

import { fetchStats } from "../services/api";

function getFakeRateTone(value) {
  if (value > 30) {
    return "stat-value danger";
  }

  if (value > 15) {
    return "stat-value warning";
  }

  return "stat-value safe";
}

export default function StatsPanel() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadStats() {
      try {
        setError("");
        const data = await fetchStats();
        if (active) {
          setStats(data);
        }
      } catch (loadError) {
        if (active) {
          setError("Unable to load platform stats yet.");
        }
      }
    }

    loadStats();
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <section className="section-card">
        <p className="panel-error">{error}</p>
      </section>
    );
  }

  if (!stats) {
    return (
      <section className="section-card">
        <div className="stats-grid">
          {Array.from({ length: 5 }).map((_, index) => (
            <article className="stat-card skeleton-card" key={index}>
              <span className="skeleton-line skeleton-value" />
              <span className="skeleton-line skeleton-label" />
            </article>
          ))}
        </div>
      </section>
    );
  }

  const cards = [
    { label: "Total Reviews Analyzed", value: stats.total_reviews?.toLocaleString() ?? "0" },
    {
      label: "Fake Review Percentage",
      value: `${stats.fake_percentage ?? 0}%`,
      className: getFakeRateTone(stats.fake_percentage ?? 0)
    },
    { label: "Cartels Detected", value: stats.num_cartels_detected?.toLocaleString() ?? "0" },
    { label: "Largest Cartel Size", value: stats.largest_cartel_size?.toLocaleString() ?? "0" },
    { label: "Unique Reviewers", value: stats.unique_reviewers?.toLocaleString() ?? "0" }
  ];

  return (
    <section className="section-card">
      <div className="stats-grid">
        {cards.map((card) => (
          <article className="stat-card" key={card.label}>
            <span className={card.className ?? "stat-value"}>{card.value}</span>
            <span className="stat-label">{card.label}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
