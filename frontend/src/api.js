// Every call to the Flask API goes through this file. Keeping it in one
// place means the rest of the app never constructs a URL or calls fetch()
// directly -- if the API's base URL or error shape ever changes, this is
// the only file that needs to change.

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (networkError) {
    throw new ApiError(
      `Can't reach the triage API at ${BASE_URL}. Is api.py running?`,
      0
    );
  }

  let body = null;
  try {
    body = await response.json();
  } catch {
    // non-JSON response, fall through with body = null
  }

  if (!response.ok) {
    throw new ApiError(body?.error || `Request failed (${response.status})`, response.status);
  }
  return body;
}

export const api = {
  health: () => request("/api/health"),

  sampleTickets: () => request("/api/tickets/sample"),

  triageOne: (ticket, useLlm = false) =>
    request("/api/triage", {
      method: "POST",
      body: JSON.stringify({ ...ticket, use_llm: useLlm }),
    }),

  triageBatch: (tickets, useLlm = false) =>
    request("/api/triage/batch", {
      method: "POST",
      body: JSON.stringify({ tickets, use_llm: useLlm }),
    }),
};

export { ApiError };
