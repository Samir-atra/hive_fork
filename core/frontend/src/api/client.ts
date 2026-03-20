const API_BASE = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: { error: string; type?: string; [key: string]: unknown },
  ) {
    super(body.error);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ error: response.statusText }));
    throw new ApiError(response.status, body);
  }

  return response.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, options?: RequestInit) => {
    let finalBody: BodyInit | undefined;
    let headers: Record<string, string> = { "Content-Type": "application/json" };

    if (body instanceof FormData) {
      finalBody = body;
      headers = {}; // Let browser set Content-Type for FormData
    } else if (body) {
      finalBody = JSON.stringify(body);
    }

    if (options?.headers) {
      Object.assign(headers, options.headers);
      if (headers["Content-Type"] === "multipart/form-data") {
        delete headers["Content-Type"]; // Allow browser boundary
      }
    }

    return request<T>(path, {
      ...options,
      method: "POST",
      body: finalBody,
      headers
    });
  },
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),
};
