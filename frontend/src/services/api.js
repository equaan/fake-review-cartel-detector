import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000"
});

export async function fetchStats() {
  const response = await api.get("/stats");
  return response.data;
}

export async function fetchCartels() {
  const response = await api.get("/cartels");
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
