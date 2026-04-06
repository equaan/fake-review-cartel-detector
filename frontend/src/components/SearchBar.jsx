import { useEffect, useState } from "react";

export default function SearchBar({ onSearch, isLoading = false }) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!query.trim()) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      onSearch(query.trim());
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [onSearch, query]);

  function handleSubmit(event) {
    event.preventDefault();
    if (!query.trim()) {
      return;
    }

    onSearch(query.trim());
  }

  return (
    <section className="section-card">
      <form className="search-row" onSubmit={handleSubmit}>
        <input
          className="search-input"
          type="text"
          placeholder="Search product ID or reviewer ID"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button className="search-button" type="submit" disabled={isLoading}>
          {isLoading ? "Searching..." : "Search"}
        </button>
      </form>
    </section>
  );
}
