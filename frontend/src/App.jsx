import React, { useState, useEffect, useCallback } from 'react';
import { api } from './api';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import PromptPanel from './components/PromptPanel';
import './App.css';

export default function App() {
  const [conversation, setConversation] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [messages, setMessages] = useState([]);
  const [title, setTitle] = useState('');
  const [archives, setArchives] = useState([]);
  const [settings, setSettings] = useState({});
  const [activeRound, setActiveRound] = useState(0);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    const conv = await api.getConversation();
    setConversation(conv);
    setParticipants(conv.participants || []);
    setMessages(conv.messages || []);
    setTitle(conv.title || '');
  }, []);

  const refreshArchives = useCallback(async () => {
    const list = await api.getArchives();
    setArchives(list || []);
  }, []);

  const refreshSettings = useCallback(async () => {
    const s = await api.getSettings();
    setSettings(s || {});
  }, []);

  useEffect(() => {
    refresh();
    refreshArchives();
    refreshSettings();
  }, [refresh, refreshArchives, refreshSettings]);

  const handleExport = async (format) => {
    try {
      let data;
      if (format === 'json') {
        data = await api.exportJSON();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        download(blob, `${title || 'discussion'}_${new Date().toISOString().slice(0,10)}.json`);
      } else if (format === 'markdown') {
        const res = await api.exportMarkdown();
        const blob = new Blob([res.content], { type: 'text/markdown' });
        download(blob, res.filename);
      } else if (format === 'txt') {
        const res = await api.exportTxt();
        const blob = new Blob([res.content], { type: 'text/plain' });
        download(blob, res.filename);
      }
    } catch (e) {
      alert('导出失败');
    }
  };

  const download = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAddUserMessage = async (content) => {
    setLoading(true);
    await api.addUserMessage(content);
    await refresh();
    setActiveRound(-1);
    setLoading(false);
  };

  const handleAddAIMessage = async (name, content, isSummary = false) => {
    setLoading(true);
    await api.addAIMessage(name, content, isSummary);
    await refresh();
    setActiveRound(-1);
    setLoading(false);
  };

  const handleAutoCall = async (name, profileId) => {
    setLoading(true);
    try {
      const res = await api.autoCall(name, profileId);
      await refresh();
      setActiveRound(-1);
      return res;
    } catch (e) {
      alert('自动调用失败: ' + e.message);
    }
    setLoading(false);
  };

  const handleNewTopic = async (newTitle) => {
    await api.newConversation(newTitle);
    await refresh();
    await refreshArchives();
    setActiveRound(0);
  };

  const handleLoadArchive = async (path) => {
    await api.loadArchive(path);
    await refresh();
    setActiveRound(-1);
  };

  const handleDeleteArchive = async (path) => {
    await api.deleteArchive(path);
    await refreshArchives();
  };

  const handleDeleteMessage = async (index) => {
    await api.deleteMessage(index);
    await refresh();
  };

  const handleAddParticipant = async (name, url) => {
    await api.addParticipant(name, url);
    await refresh();
  };

  const handleRemoveParticipant = async (name) => {
    await api.removeParticipant(name);
    await refresh();
  };

  const handleGeneratePrompt = async (targetAI, mode, profileId) => {
    const result = await api.generatePrompt(targetAI, mode, profileId);
    return result;
  };

  const rounds = [];
  let current = [];
  for (const msg of messages) {
    if (msg.role === 'user' && current.length > 0) {
      rounds.push(current);
      current = [];
    }
    current.push(msg);
  }
  if (current.length > 0) rounds.push(current);

  const activeRoundIndex = activeRound === -1 ? rounds.length - 1 : Math.min(activeRound, rounds.length - 1);
  const displayedMessages = rounds[activeRoundIndex] || [];

  return (
    <div className="app">
      <div className="window-controls">
  <button className="win-btn win-min" onClick={() => window.electronAPI?.minimize()} title="最小化">
    <svg width="10" height="10" viewBox="0 0 10 10"><line x1="2" y1="5" x2="8" y2="5" stroke="currentColor" strokeWidth="1"/></svg>
  </button>
  <button className="win-btn win-max" onClick={() => window.electronAPI?.maximize()} title="最大化">
    <svg width="10" height="10" viewBox="0 0 10 10"><rect x="1.5" y="1.5" width="7" height="7" fill="none" stroke="currentColor" strokeWidth="1"/></svg>
  </button>
  <button className="win-btn win-close" onClick={() => window.electronAPI?.close()} title="关闭">
    <svg width="10" height="10" viewBox="0 0 10 10"><line x1="2" y1="2" x2="8" y2="8" stroke="currentColor" strokeWidth="1"/><line x1="8" y1="2" x2="2" y2="8" stroke="currentColor" strokeWidth="1"/></svg>
  </button>
</div>

<div className="app-bg" />
      <div className="app-content">
        <Sidebar
          title={title}
          participants={participants}
          archives={archives}
          settings={settings}
          onAddUserMessage={handleAddUserMessage}
          onAddParticipant={handleAddParticipant}
          onRemoveParticipant={handleRemoveParticipant}
          onNewTopic={handleNewTopic}
          onLoadArchive={handleLoadArchive}
          onDeleteArchive={handleDeleteArchive}
          onRefreshArchives={refreshArchives}
          onUpdateTitle={async (t) => { await api.updateTitle(t); await refresh(); }}
          onExport={handleExport}
          loading={loading}
        />

        <ChatArea
          title={title}
          messages={displayedMessages}
          rounds={rounds}
          activeRound={activeRoundIndex}
          onSelectRound={setActiveRound}
          onDeleteMessage={handleDeleteMessage}
          onExport={handleExport}
        />

        <PromptPanel
          participants={participants}
          onAddAIMessage={handleAddAIMessage}
          onAutoCall={handleAutoCall}
          onGeneratePrompt={handleGeneratePrompt}
          settings={settings}
          onUpdateApiKey={async (name, provider, key, model) => {
            await api.updateUrl(name, '', provider, key, model);
            await refreshSettings();
            await refresh();
          }}
          loading={loading}
        />
      </div>
    </div>
  );
}