const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");

function apiUrl(path: string): string {
  if (!API_BASE_URL) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed for ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getV2Intelligence(symbol: string) {
  return getJson(`/v2/intelligence?symbol=${encodeURIComponent(symbol)}`);
}

export async function getV2DashboardSummary() {
  return getJson("/v2/dashboard-summary");
}

export async function getWeeklyStockOpportunities() {
  return getJson("/stocks/weekly-opportunities");
}
