const defaultHeaders = {
  "Content-Type": "application/json",
};

const buildUrl = (apiUrl, path) => `${apiUrl}${path}`;

const request = (apiUrl, path, options = {}) =>
  fetch(buildUrl(apiUrl, path), {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers ?? {}),
    },
  });

const get = (apiUrl, path) => request(apiUrl, path);
const post = (apiUrl, path, body) =>
  request(apiUrl, path, {
    method: "POST",
    body: JSON.stringify(body),
  });
const put = (apiUrl, path, body) =>
  request(apiUrl, path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
const del = (apiUrl, path, body) =>
  request(apiUrl, path, {
    method: "DELETE",
    body: body ? JSON.stringify(body) : undefined,
  });

export const apiClient = {
  get,
  post,
  put,
  del,
};
