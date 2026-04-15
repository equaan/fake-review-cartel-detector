import axios from "axios";

const api = axios.create({
  // Prefer explicit env override; otherwise use relative URLs via CRA proxy.
  baseURL: process.env.REACT_APP_API_BASE_URL || ""
});

export async function fetchStats() {
  const response = await api.get("/stats");
  return response.data;
}

export async function fetchCartels(includeNoise = false) {
  const response = await api.get("/cartels", {
    params: { include_noise: includeNoise }
  });
  return response.data;
}

export async function fetchReviewer(reviewerId) {
  const response = await api.get(`/analyze/reviewer/${reviewerId}`);
  return response.data;
}

export async function searchEntities(query) {
  const response = await api.post("/search", { query });
  return response.data;
}

export default api;
