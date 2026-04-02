export default function SearchBar() {
  return (
    <section className="section-card">
      <div className="search-row">
        <input
          className="search-input"
          type="text"
          placeholder="Search product ID or reviewer ID"
        />
        <button className="search-button" type="button">
          Search
        </button>
      </div>
    </section>
  );
}
