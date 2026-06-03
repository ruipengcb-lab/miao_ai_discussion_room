import React, { useState } from 'react';
import { Plus, Trash2, FolderOpen } from 'lucide-react';

const COLORS = ['#0071e3', '#34c759', '#ff9500', '#ff3b30', '#af52de', '#5ac8fa', '#ff2d55'];

export default function Sidebar({
  title, participants, archives, onAddUserMessage, onAddParticipant,
  onRemoveParticipant, onNewTopic, onLoadArchive, onDeleteArchive,
  onRefreshArchives, onUpdateTitle, loading
}) {
  const [userInput, setUserInput] = useState('');
  const [showNewTopic, setShowNewTopic] = useState(false);
  const [newTopicName, setNewTopicName] = useState('');
  const [newAIName, setNewAIName] = useState('');

  const handleAddUser = async () => {
    if (!userInput.trim()) return;
    await onAddUserMessage(userInput);
    setUserInput('');
  };

  const handleSaveTitle = async () => {
    await onUpdateTitle(newTitle);
    setEditingTitle(false);
  };

  const handleNewTopic = () => {
    if (!newTopicName.trim()) return;
    onNewTopic(newTopicName);
    setNewTopicName('');
    setShowNewTopic(false);
  };

  const handleAddAI = () => {
    if (!newAIName.trim()) return;
    onAddParticipant(newAIName);
    setNewAIName('');
  };

  return (
    <div className="sidebar">
      {/* 主题 */}
      <div className="topic-section">
<span className="topic-display">多AI 讨论工具</span>
      </div>

      {/* 新话题 */}
      {showNewTopic ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="topic-input"
            placeholder="新话题名称"
            value={newTopicName}
            onChange={(e) => setNewTopicName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNewTopic()}
          />
          <button className="btn btn-primary btn-sm" onClick={handleNewTopic}>创建</button>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowNewTopic(false)}>取消</button>
        </div>
      ) : (
        <button className="btn btn-secondary btn-full" onClick={() => setShowNewTopic(true)}>
          <Plus size={16} /> 创建新话题
        </button>
      )}

      {/* 参与者 */}
      <div>
        <div className="sidebar-header">
          <span className="sidebar-title">AI 发言者</span>
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          <input
            className="topic-input"
            placeholder="添加 AI 名称"
            value={newAIName}
            onChange={(e) => setNewAIName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddAI()}
            style={{ flex: 1 }}
          />
          <button className="btn btn-secondary btn-sm" onClick={handleAddAI}>
            <Plus size={16} />
          </button>
        </div>
        <div className="participant-list" style={{ marginTop: 8 }}>
          {participants.map((name, i) => (
            <div className="participant-item" key={name}>
              <span className="participant-name">
                <span className="participant-dot" style={{ background: COLORS[i % COLORS.length] }} />
                {name}
              </span>
              <div className="participant-actions">
                {participants.length > 1 && (
                  <button className="btn btn-ghost btn-sm" onClick={() => onRemoveParticipant(name)}>
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="divider" />

      {/* 我发言 */}
      <div>
        <div className="sidebar-header">
          <span className="sidebar-title">我发言</span>
        </div>
        <textarea
          className="textarea"
          placeholder="输入你的观点、问题或追问"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleAddUser();
          }}
        />
        <button
          className="btn btn-primary btn-full"
          onClick={handleAddUser}
          disabled={loading || !userInput.trim()}
          style={{ marginTop: 8 }}
        >
          {loading ? '发送中...' : '加入我的发言'}
        </button>
      </div>

      <div className="divider" />

      {/* 历史话题 */}
      <div>
        <div className="sidebar-header">
          <span className="sidebar-title">历史话题</span>
          <button className="btn btn-ghost btn-icon" onClick={onRefreshArchives}>
            <FolderOpen size={14} />
          </button>
        </div>
        <div className="archive-list" style={{ marginTop: 8 }}>
          {archives.length === 0 ? (
            <p style={{ fontSize: 12, color: 'var(--text-tertiary)', padding: 8 }}>还没有历史话题</p>
          ) : (
            archives.slice(0, 12).map((arch) => (
              <div className="archive-item" key={arch.path}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div onClick={() => onLoadArchive(arch.path)} style={{ flex: 1, cursor: 'pointer' }}>
                    <div className="archive-title">{arch.title || '无标题'}</div>
                    <div className="archive-meta">{arch.message_count} 条 / {arch.updated_at}</div>
                  </div>
                  <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); onDeleteArchive(arch.path); }}>
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}