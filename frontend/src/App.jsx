import SearchBar from "./components/SearchBar";
import StatsPanel from "./components/StatsPanel";
import NetworkGraph from "./components/NetworkGraph";

const sampleNodes = [
  { id: "reviewer-001", cluster: 2, suspicion_score: 0.91, review_count: 14 },
  { id: "reviewer-002", cluster: 2, suspicion_score: 0.87, review_count: 11 },
  { id: "reviewer-003", cluster: -1, suspicion_score: 0.18, review_count: 4 }
];

const sampleEdges = [
  { source: "reviewer-001", target: "reviewer-002", shared_products: 6 }
];

export default function App() {
  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Machine Learning Project</p>
        <h1>Fake Review Cartel Detector</h1>
        <p className="hero-copy">
          Detect coordinated fake-review networks instead of only isolated
          suspicious reviews.
        </p>
      </header>

      <StatsPanel />
      <SearchBar />
      <NetworkGraph nodes={sampleNodes} edges={sampleEdges} />
    </div>
  );
}
