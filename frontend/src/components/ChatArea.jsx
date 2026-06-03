import React, { useState } from 'react';
import MessageBubble from './MessageBubble';
import { Download, Edit3, ChevronDown, ChevronUp } from 'lucide-react';

export default function ChatArea({ title, messages, rounds, activeRound, onSelectRound, onDeleteMessage, onExport, onUpdateTitle }) {
  const [showExport, setShowExport] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [editTitleValue, setEditTitleValue] = useState(title);

  const handleSaveTitle = () => {
    onUpdateTitle(editTitleValue);
    setEditingTitle(false);
  };

  return (
    <div className="chat-area">
      <div className="chat-header">
     {editingTitle ? (
  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
    <input
      className="topic-input"
      value={editTitleValue}
      onChange={(e) => setEditTitleValue(e.target.value)}
      onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()}
      autoFocus
      style={{ fontSize: 16, fontWeight: 700, width: 260 }}
    />
    <button className="btn btn-primary btn-sm" onClick={handleSaveTitle}>保存</button>
    <button className="btn btn-ghost btn-sm" onClick={() => setEditingTitle(false)}>取消</button>
  </div>
) : (
  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
    <span className="chat-title">{title || '对话记录'}</span>
    <button className="btn btn-ghost btn-icon" onClick={() => { setEditTitleValue(title); setEditingTitle(true); }}>
      <Edit3 size={14} />
    </button>
  </div>
)}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="chat-meta">{messages.length} 条</span>
          <div style={{ position: 'relative' }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowExport(!showExport)}>
              <Download size={14} /> 导出
            </button>
            {showExport && (
              <div className="dropdown-menu">
                <button className="dropdown-item" onClick={() => { onExport('txt'); setShowExport(false); }}>TXT</button>
                <button className="dropdown-item" onClick={() => { onExport('json'); setShowExport(false); }}>JSON</button>
                <button className="dropdown-item" onClick={() => { onExport('markdown'); setShowExport(false); }}>Markdown</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {rounds.length > 1 && (
        <div className="round-tabs">
          {rounds.map((round, i) => (
            <button
              key={i}
              className={`round-tab ${i === activeRound ? 'active' : ''}`}
              onClick={() => onSelectRound(i)}
            >
              第 {i + 1} 轮
            </button>
          ))}
        </div>
      )}

      <div className="message-list">
        {messages.length === 0 ? (
          <div className="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
            <p>还没有发言</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <MessageBubble
              key={i}
              message={msg}
              index={i}
              onDelete={() => onDeleteMessage(i)}
            />
          ))
        )}
      </div>
    </div>
  );
}