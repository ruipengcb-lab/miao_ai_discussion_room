import React, { useState } from 'react';
import { Trash2, ChevronDown, ChevronUp } from 'lucide-react';

const COLORS = {
  '我': '#0071e3',
  '喵酱': '#0071e3',
  'ChatGPT': '#34c759',
  'DeepSeek': '#5856d6',
  'GLM': '#ff9500',
  'MiniMax': '#ff3b30',
  '总结': '#af52de',
};

const FALLBACK = ['#0071e3', '#34c759', '#ff9500', '#ff3b30', '#af52de', '#5ac8fa', '#ff2d55'];

function getColor(name) {
  if (COLORS[name]) return COLORS[name];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return FALLBACK[Math.abs(hash) % FALLBACK.length];
}

function getInitial(name) {
  return name.charAt(0).toUpperCase();
}

export default function MessageBubble({ message, index, onDelete }) {
  const speaker = message.role === 'user' ? '我' : message.speaker;
  const isUser = message.role === 'user';
  const color = getColor(speaker);
  const content = message.content || '';
  const isLong = content.length > 520;
  const [expanded, setExpanded] = useState(false);

  const displayContent = isLong && !expanded ? content.slice(0, 520) + '\n\n...' : content;

  return (
    <div className="message-bubble">
      <div className={`message-avatar ${isUser ? 'user' : 'ai'}`} style={isUser ? {} : { border: `2px solid ${color}` }}>
        {getInitial(speaker)}
      </div>
      <div className="message-body">
        <div className="message-header">
          <span className="message-speaker" style={{ color: isUser ? 'var(--text-primary)' : color }}>
            {speaker}
          </span>
          <span className="message-time">
            {message.created_at?.replace('T', ' ') || ''}
          </span>
          <button className="btn btn-ghost btn-sm" onClick={onDelete} style={{ marginLeft: 'auto' }}>
            <Trash2 size={12} />
          </button>
        </div>
        <div className={`message-content ${isLong && !expanded ? 'collapsed-preview' : ''}`}>
          {displayContent}
        </div>
        {isLong && (
          <button className="fold-btn" onClick={() => setExpanded(!expanded)}>
            {expanded ? <><ChevronUp size={12} /> 收起</> : <><ChevronDown size={12} /> 展开全文</>}
          </button>
        )}
      </div>
    </div>
  );
}