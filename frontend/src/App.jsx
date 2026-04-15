import { useCallback, useEffect, useMemo, useState } from "react";

import NetworkGraph from "./components/NetworkGraph";
import ReviewCard from "./components/ReviewCard";
import SearchBar from "./components/SearchBar";
import StatsPanel from "./components/StatsPanel";
import {
  fetchCartels,
  fetchReviewer,
  searchEntities
} from "./services/api";

const fallbackNodes = [
  { id: "reviewer-001", cluster: 2, suspicion_score: 0.91, review_count: 14, avg_rating: 4.9 },
  { id: "reviewer-002", cluster: 2, suspicion_score: 0.87, review_count: 11, avg_rating: 5.0 },
  { id: "reviewer-003", cluster: -1, suspicion_score: 0.18, review_count: 4, avg_rating: 3.8 }
];

const fallbackEdges = [
  { source: "reviewer-001", target: "reviewer-002", shared_products: 6 }
];

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [graphError, setGraphError] = useState("");
  const [includeNoise, setIncludeNoise] = useState(false);
  const [selectedReviewer, setSelectedReviewer] = useState(null);
  const [reviewerError, setReviewerError] = useState("");
  const [reviewerLoading, setReviewerLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [highlightedIds, setHighlightedIds] = useState([]);

  useEffect(() => {
    let active = true;

    async function loadCartels() {
      try {
        const data = await fetchCartels(includeNoise);
        if (!active) {
          return;
        }

        if (!data.nodes?.length) {
          setGraphData({ nodes: fallbackNodes, edges: fallbackEdges });
          setGraphError("Using fallback graph until cartel clustering outputs are generated.");
          return;
        }

        setGraphData(data);
        setGraphError("");
      } catch (error) {
        if (active) {
          setGraphData({ nodes: fallbackNodes, edges: fallbackEdges });
          setGraphError("Backend cartel data is not ready yet, so a fallback demo graph is shown.");
        }
      }
    }

    loadCartels();
    return () => {
      active = false;
    };
  }, [includeNoise]);

  async function handleNodeClick(node) {
    setReviewerLoading(true);
    setReviewerError("");

    try {
      const data = await fetchReviewer(node.id);
      setSelectedReviewer(data);
    } catch (error) {
      setReviewerError("Reviewer details are not available yet.");
      setSelectedReviewer({
        reviewer_id: node.id,
        cluster_label: node.cluster,
        suspicion_score: node.suspicion_score,
        features: {
          avg_rating: node.avg_rating,
          review_count: node.review_count
        },
        reviews: []
      });
    } finally {
      setReviewerLoading(false);
    }
  }

  const handleSearch = useCallback(async (query) => {
    setSearchLoading(true);

    try {
      const data = await searchEntities(query);
      const matches = [...(data.reviewers ?? []), ...(data.products ?? [])];
      const reviewerMatches = graphData.nodes
        .map((node) => node.id)
        .filter((id) => matches.includes(id));

      setHighlightedIds(reviewerMatches);
    } catch (error) {
      const localMatches = graphData.nodes
        .map((node) => node.id)
        .filter((id) => id.toLowerCase().includes(query.toLowerCase()));
      setHighlightedIds(localMatches);
    } finally {
      setSearchLoading(false);
    }
  }, [graphData.nodes]);

  const reviewerFeatures = useMemo(() => {
    if (!selectedReviewer?.features) {
      return [];
    }

    return Object.entries(selectedReviewer.features);
  }, [selectedReviewer]);

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Machine Learning Project</p>
        <h1>Fake Review Cartel Detector</h1>
        <p className="hero-copy">
          Detect coordinated fake-review networks instead of only isolated suspicious reviews.
        </p>
      </header>

      <StatsPanel />
      <SearchBar onSearch={handleSearch} isLoading={searchLoading} />

      {graphError ? <p className="panel-note">{graphError}</p> : null}

      <div className="workspace-grid">
        <div className="workspace-main">
          <NetworkGraph
            nodes={graphData.nodes}
            edges={graphData.edges}
            highlightedIds={highlightedIds}
            includeNoise={includeNoise}
            onToggleIncludeNoise={() => setIncludeNoise((previous) => !previous)}
            onNodeClick={handleNodeClick}
          />
        </div>

        <aside className={`reviewer-drawer ${selectedReviewer ? "open" : ""}`}>
          <div className="drawer-header">
            <div>
              <p className="eyebrow">Reviewer Panel</p>
              <h2>{selectedReviewer?.reviewer_id ?? "Select a node"}</h2>
            </div>
          </div>

          {!selectedReviewer && (
            <div className="empty-state drawer-empty">
              <p>Click a graph node to inspect reviewer features and review history.</p>
            </div>
          )}

          {reviewerLoading && <p className="panel-note">Loading reviewer details...</p>}
          {reviewerError && <p className="panel-error">{reviewerError}</p>}

          {selectedReviewer && !reviewerLoading && (
            <>
              <div className="drawer-summary">
                <span>Cluster: {selectedReviewer.cluster_label}</span>
                <span>
                  Suspicion: {Math.round((selectedReviewer.suspicion_score ?? 0) * 100)}%
                </span>
              </div>

              <section className="drawer-section">
                <h3>Behavioral Features</h3>
                <div className="feature-list">
                  {reviewerFeatures.map(([key, value]) => (
                    <div className="feature-row" key={key}>
                      <span>{key}</span>
                      <strong>{typeof value === "number" ? value.toFixed(3) : value}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="drawer-section">
                <h3>Reviews</h3>
                <div className="review-list">
                  {(selectedReviewer.reviews ?? []).length === 0 ? (
                    <div className="empty-state">
                      <p>Reviewer review history is not available yet from the backend.</p>
                    </div>
                  ) : (
                    selectedReviewer.reviews.map((review, index) => (
                      <ReviewCard key={`${review.product_id}-${index}`} review={review} />
                    ))
                  )}
                </div>
              </section>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
