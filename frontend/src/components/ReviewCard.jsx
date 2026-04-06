export default function ReviewCard({ review }) {
  const fakeProbability = Math.round((review.fake_probability ?? 0) * 100);
  const toneClass =
    fakeProbability >= 70 ? "danger" : fakeProbability >= 40 ? "warning" : "safe";

  return (
    <article className="review-card">
      <div className="review-card-top">
        <span className="review-meta">Product {review.product_id}</span>
        <span className={`review-badge ${toneClass}`}>{fakeProbability}% fake risk</span>
      </div>
      <p className="review-text">{review.review_body || "No review text available."}</p>
      <div className="review-footer">
        <span>Rating: {review.star_rating ?? "N/A"}</span>
        <span>{review.review_date ?? "Unknown date"}</span>
      </div>
    </article>
  );
}
