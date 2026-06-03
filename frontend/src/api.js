const BASE_URL = 'http://localhost:8765/api';

async function request(url, options = {}) {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

export const api = {
  // 会话
  getConversation: () => request('/conversation'),
  updateTitle: (title) => request('/conversation/title', { method: 'PUT', body: JSON.stringify({ title }) }),
  clearConversation: () => request('/conversation/clear', { method: 'POST' }),
  newConversation: (title) => request('/conversation/new', { method: 'POST', body: JSON.stringify({ title }) }),

  // 消息
  addUserMessage: (content) => request('/messages/user', { method: 'POST', body: JSON.stringify({ content }) }),
  addAIMessage: (name, content, isSummary = false) => request('/messages/ai', { method: 'POST', body: JSON.stringify({ name, content, is_summary: isSummary }) }),
  deleteMessage: (index) => request(`/messages/${index}`, { method: 'DELETE' }),

  // 参与者
  addParticipant: (name, url = '') => request('/participants', { method: 'POST', body: JSON.stringify({ name, url }) }),
  removeParticipant: (name) => request('/participants', { method: 'DELETE', body: JSON.stringify({ name }) }),
  updateUrl: (name, url) => request('/participants/url', { method: 'PUT', body: JSON.stringify({ name, url }) }),

  // Prompt
  generatePrompt: (targetAI, mode = 'discussion', profileId = null) => request('/prompt', { method: 'POST', body: JSON.stringify({ target_ai: targetAI, mode, profile_id: profileId }) }),

  // 自动调用
  autoCall: (name, profileId = null) => request('/auto-call', { method: 'POST', body: JSON.stringify({ name, profile_id: profileId }) }),

  // API Key
  updateApiKey: (name, provider, apiKey, model = '') => request('/settings/api-key', { method: 'PUT', body: JSON.stringify({ name, provider, api_key: apiKey, model }) }),
  getSettings: () => request('/settings'),

  // 归档
  getArchives: () => request('/archives'),
  loadArchive: (path) => request('/archives/load', { method: 'POST', body: JSON.stringify({ path }) }),
  deleteArchive: (path) => request('/archives', { method: 'DELETE', body: JSON.stringify({ path }) }),

  // 导出
  exportJSON: () => request('/export/json'),
  exportMarkdown: () => request('/export/markdown'),
    // 补充缺失的方法
  exportTxt: () => request('/export/txt'),
  getParticipantUrl: (name) => request(`/participants/url?name=${encodeURIComponent(name)}`),
  updateSettings: (key, value) => request('/settings/update', { method: 'PUT', body: JSON.stringify({ key, value }) }),
};