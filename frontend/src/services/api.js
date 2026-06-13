import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || '';
    const isAuthRoute = url.includes('/auth/login') || url.includes('/auth/register');
    if (error.response?.status === 401 && !isAuthRoute) {
      localStorage.removeItem('token');
      window.dispatchEvent(new Event('auth:logout'));
    }
    return Promise.reject(error);
  },
);

function unwrapError(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ');
  return error.response?.data?.message || error.message || 'Request failed';
}

export async function register(payload) {
  try {
    const response = await api.post('/auth/register', {
      email: payload.email,
      full_name: payload.fullName,
      password: payload.password,
    });
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function login(payload) {
  try {
    const response = await api.post('/auth/login', payload);
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function fetchWorkspaces() {
  try {
    const response = await api.get('/workspaces');
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function createWorkspace(payload) {
  try {
    const response = await api.post('/workspaces', payload);
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function uploadDocument(workspaceId, file) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/documents/${workspaceId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function fetchDocuments(workspaceId) {
  try {
    const response = await api.get(`/documents/${workspaceId}`);
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function searchWorkspace(payload) {
  try {
    const response = await api.post('/search', payload);
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function runResearch(payload) {
  try {
    const response = await api.post('/research/runs', payload);
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function fetchReports(workspaceId) {
  try {
    const response = await api.get(`/reports/${workspaceId}`);
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export async function fetchConnectors() {
  try {
    const response = await api.get('/mcp/connectors');
    return response.data;
  } catch (error) {
    throw new Error(unwrapError(error));
  }
}

export default api;
