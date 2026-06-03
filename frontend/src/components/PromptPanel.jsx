import React, { useState, useEffect, useCallback } from 'react';
import { Copy, Zap, Send, Settings, HelpCircle, Plus, Trash2, Save, ExternalLink, Globe } from 'lucide-react';
import { api } from '../api';

export default function PromptPanel({
  participants, onAddAIMessage, onAutoCall, onGeneratePrompt,
  settings, onUpdateApiKey, loading
}) {
  const [targetAI, setTargetAI] = useState(participants[0] || '');
  const [prompt, setPrompt] = useState('');
  const [mode, setMode] = useState('discussion');
  const [pasteContent, setPasteContent] = useState('');
  const [pasteTarget, setPasteTarget] = useState(participants[0] || '');

  const [showApiConfig, setShowApiConfig] = useState(false);
  const [apiName, setApiName] = useState('');
  const [apiProvider, setApiProvider] = useState('deepseek');
  const [apiKey, setApiKey] = useState('');
  const [apiUrl, setApiUrl] = useState('');

  const [profiles, setProfiles] = useState([]);
  const [activeProfileId, setActiveProfileId] = useState('default');
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [showHelpDialog, setShowHelpDialog] = useState(false);

  const [editingName, setEditingName] = useState('');
  const [matrix, setMatrix] = useState([['']]);
  const [summaryPrompt, setSummaryPrompt] = useState('');
  const [currentRound, setCurrentRound] = useState(1);
  const [currentTurn, setCurrentTurn] = useState(1);

  useEffect(() => {
    if (participants.length > 0 && !participants.includes(targetAI)) {
      setTargetAI(participants[0]);
      setPasteTarget(participants[0]);
    }
  }, [participants]);

  useEffect(() => {
    const saved = settings?.prompt_profiles;
    if (saved && saved.length > 0) {
      setProfiles(saved);
      setActiveProfileId(settings.active_prompt_profile_id || saved[0].id);
    } else {
      setProfiles([{
        id: 'default', name: '默认模板', first_round: '', later_round: '',
        round_prompts: [''], prompt_matrix: [['']], summary: '',
      }]);
      setActiveProfileId('default');
    }
  }, [settings]);

  const normalizeMatrix = useCallback((m) => {
    const rows = (m && m.length > 0) ? m.map(row =>
      (Array.isArray(row) ? row : [row || '']).map(c => c || '')
    ) : [['']];
    const maxCols = Math.max(...rows.map(r => r.length), 1);
    return rows.map(row => [...row, ...Array(maxCols - row.length).fill('')]);
  }, []);

  const openTemplateDialog = () => {
    const profile = profiles.find(p => p.id === activeProfileId) || profiles[0];
    setEditingName(profile.name || '');
    const mat = profile.prompt_matrix?.length ? normalizeMatrix(profile.prompt_matrix)
      : (profile.round_prompts?.length ? profile.round_prompts.map(p => [p || '']) : [['']]);
    setMatrix(normalizeMatrix(mat));
    setSummaryPrompt(profile.summary || '');
    setCurrentRound(1);
    setCurrentTurn(1);
    setShowTemplateDialog(true);
  };

  const saveCurrentCell = () => {
    const newMatrix = matrix.map(row => [...row]);
    if (newMatrix[currentRound - 1]) {
      newMatrix[currentRound - 1][currentTurn - 1] = prompt;
    }
    setMatrix(newMatrix);
  };

  const addRound = () => { saveCurrentCell(); const nm = matrix.map(r => [...r]); nm.push(Array(matrix[0].length).fill('')); setMatrix(nm); setCurrentRound(nm.length); };
  const removeRound = () => { if (matrix.length <= 1) return; saveCurrentCell(); const nm = matrix.slice(0, -1); setMatrix(nm); setCurrentRound(Math.min(currentRound, nm.length)); };
  const addTurn = () => { saveCurrentCell(); const nm = matrix.map(r => [...r, '']); setMatrix(nm); setCurrentTurn(nm[0].length); };
  const removeTurn = () => { if (matrix[0].length <= 1) return; saveCurrentCell(); const nm = matrix.map(r => r.slice(0, -1)); setMatrix(nm); setCurrentTurn(Math.min(currentTurn, nm[0].length)); };

  const saveProfile = () => {
    saveCurrentCell();
    const np = profiles.map(p => p.id === activeProfileId ? { ...p, name: editingName || '未命名', prompt_matrix: matrix, round_prompts: matrix.map(r => r[0] || ''), summary: summaryPrompt } : p);
    setProfiles(np);
    onUpdateSettings?.('prompt_profiles', np);
    setShowTemplateDialog(false);
  };

  const saveAsNew = () => {
    saveCurrentCell();
    const id = 'profile_' + Date.now();
    const np = [...profiles, { id, name: editingName || '新模板', prompt_matrix: matrix, round_prompts: matrix.map(r => r[0] || ''), summary: summaryPrompt }];
    setProfiles(np); setActiveProfileId(id);
    onUpdateSettings?.('prompt_profiles', np);
    onUpdateSettings?.('active_prompt_profile_id', id);
    setShowTemplateDialog(false);
  };

  const deleteProfile = () => {
    if (activeProfileId === 'default') return;
    const np = profiles.filter(p => p.id !== activeProfileId);
    setProfiles(np); setActiveProfileId(np[0]?.id || 'default');
    onUpdateSettings?.('prompt_profiles', np);
    onUpdateSettings?.('active_prompt_profile_id', np[0]?.id || 'default');
    setShowTemplateDialog(false);
  };

  const handleGeneratePrompt = async () => {
    const result = await onGeneratePrompt(targetAI, mode, activeProfileId);
    setPrompt(result.prompt);
    if (result.next_ai && result.next_ai !== targetAI && mode === 'discussion') {
      setTargetAI(result.next_ai);
      setPasteTarget(result.next_ai);
    }
  };

  const handleCopy = () => { navigator.clipboard.writeText(prompt); };

  const handleAddPaste = async () => {
    if (!pasteContent.trim()) return;
    const isSummary = pasteTarget === '总结' || mode === 'summary';
    await onAddAIMessage(pasteTarget, pasteContent, isSummary);
    setPasteContent('');
  };

  const handleAutoCall = async () => {
    const res = await onAutoCall(targetAI, activeProfileId);
    if (res?.next_ai && res.next_ai !== targetAI) {
      setTargetAI(res.next_ai);
      setPasteTarget(res.next_ai);
    }
  };

  const openAiUrl = (name) => {
    api.getParticipantUrl(name).then(r => {
      if (r.valid) window.open(r.url, '_blank');
      else alert('该 AI 未设置网页地址');
    });
  };

  const openApiConfig = (name) => {
    setApiName(name);
    const existing = settings?.per_ai_api?.[name] || {};
    setApiProvider(existing.provider || 'deepseek');
    setApiKey(existing.api_key || '');
    setApiUrl(settings?.participant_urls?.[name] || '');
    setShowApiConfig(true);
  };

  const saveApiKey = async () => {
    await onUpdateApiKey?.(apiName, apiProvider, apiKey);
    if (apiUrl) await api.updateUrl(apiName, apiUrl);
    setShowApiConfig(false);
  };

  const onUpdateSettings = (key, value) => {
    api.updateSettings(key, value);
  };

  const options = [...participants, '总结'];
  const roundOptions = Array.from({ length: matrix.length }, (_, i) => i + 1);
  const turnOptions = Array.from({ length: matrix[0]?.length || 1 }, (_, i) => i + 1);

  return (
    <div className="prompt-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="prompt-panel-title">生成 Prompt</span>
        <button className="btn btn-ghost btn-icon" onClick={openTemplateDialog} title="管理 Prompt 模板">
          <Settings size={14} />
        </button>
      </div>

      <select className="select" value={activeProfileId} onChange={(e) => { setActiveProfileId(e.target.value); onUpdateSettings('active_prompt_profile_id', e.target.value); }}>
        {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>

      <select className="select" value={targetAI} onChange={(e) => setTargetAI(e.target.value)}>
        {options.map(n => <option key={n} value={n}>{n}</option>)}
      </select>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className={`btn btn-sm ${mode === 'discussion' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setMode('discussion')}>讨论</button>
        <button className={`btn btn-sm ${mode === 'summary' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setMode('summary')}>总结</button>
      </div>

      <textarea className="textarea textarea-lg" value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="点击「生成」获取 Prompt" />

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-secondary" onClick={handleGeneratePrompt} style={{ flex: 1 }}>生成 Prompt</button>
        <button className="btn btn-primary" onClick={handleCopy}><Copy size={14} /> 复制</button>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary btn-full" onClick={handleAutoCall} disabled={loading}>
          <Zap size={14} /> {loading ? '调用中...' : `自动调用 ${targetAI}`}
        </button>
        <button className="btn btn-secondary" onClick={() => openAiUrl(targetAI)} title="打开 AI 网页">
          <ExternalLink size={14} />
        </button>
      </div>

      <div className="divider" />

      <span className="prompt-panel-title">粘贴 AI 回复</span>

      <select className="select" value={pasteTarget} onChange={(e) => setPasteTarget(e.target.value)}>
        {options.map(n => <option key={n} value={n}>{n}</option>)}
      </select>

      <textarea className="textarea" value={pasteContent} onChange={(e) => setPasteContent(e.target.value)} placeholder="粘贴 AI 返回的内容" />

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary btn-full" onClick={handleAddPaste} disabled={!pasteContent.trim()}>
          <Send size={14} /> 加入对话记录
        </button>
        <button className="btn btn-secondary" onClick={() => openAiUrl(pasteTarget)} title="打开 AI 网页">
          <ExternalLink size={14} />
        </button>
      </div>

      <div className="divider" />

      <span className="prompt-panel-title">API 与网页配置</span>
    {[...participants, '总结'].map((name) => (
  <button key={name} className="btn btn-secondary btn-sm btn-full" onClick={() => openApiConfig(name)}>
    <Settings size={12} /> 配置 {name} 的 API Key 和网页
  </button>
))}

      {/* ====== Prompt 模板弹窗 ====== */}
      {showTemplateDialog && (
        <div className="modal-overlay" onClick={() => setShowTemplateDialog(false)}>
          <div className="modal-content template-dialog" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <h3 style={{ fontSize: 18, fontWeight: 700 }}>Prompt 模板</h3>
              <button className="btn btn-ghost btn-icon" onClick={() => setShowHelpDialog(true)}><HelpCircle size={16} /></button>
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>模板框留空时，会使用内置接力逻辑。</p>

            <select className="select" value={activeProfileId} onChange={(e) => {
              const nid = e.target.value; setActiveProfileId(nid);
              const p = profiles.find(x => x.id === nid);
              if (p) { setEditingName(p.name || ''); const m = p.prompt_matrix?.length ? normalizeMatrix(p.prompt_matrix) : (p.round_prompts?.length ? p.round_prompts.map(x => [x || '']) : [['']]); setMatrix(normalizeMatrix(m)); setSummaryPrompt(p.summary || ''); setCurrentRound(1); setCurrentTurn(1); }
            }}>
              {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>

            <input className="topic-input" placeholder="模板名称" value={editingName} onChange={(e) => setEditingName(e.target.value)} style={{ marginTop: 8 }} />

            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <select className="select" value={currentRound} onChange={(e) => { saveCurrentCell(); setCurrentRound(Number(e.target.value)); }} style={{ flex: 1 }}>
                {roundOptions.map(n => <option key={n} value={n}>第 {n} 轮</option>)}
              </select>
              <select className="select" value={currentTurn} onChange={(e) => { saveCurrentCell(); setCurrentTurn(Number(e.target.value)); }} style={{ flex: 1 }}>
                {turnOptions.map(n => <option key={n} value={n}>第 {n} 个 AI</option>)}
              </select>
            </div>

            <textarea className="textarea" style={{ marginTop: 8, minHeight: 100 }}
              value={matrix[currentRound - 1]?.[currentTurn - 1] || ''}
              onChange={(e) => { const nm = matrix.map(r => [...r]); if (nm[currentRound - 1]) nm[currentRound - 1][currentTurn - 1] = e.target.value; setMatrix(nm); }}
              placeholder={`第 ${currentRound} 轮 · 第 ${currentTurn} 个 AI 的 Prompt`}
            />

            <p style={{ marginTop: 12, fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>总结 Prompt</p>
            <textarea className="textarea" style={{ minHeight: 80 }} value={summaryPrompt} onChange={(e) => setSummaryPrompt(e.target.value)} placeholder="总结使用的 Prompt" />

            {/* 轮次组 */}
<div style={{ display: 'flex', gap: 6, marginTop: 12, flexDirection: 'column' }}>
  <div style={{ display: 'flex', gap: 4, border: '1px solid var(--border)', borderRadius: 6, padding: 4 }}>
    <button className="btn btn-secondary btn-sm" onClick={addRound}><Plus size={12} /> 增加轮次</button>
    <button className="btn btn-ghost btn-sm" onClick={removeRound} disabled={matrix.length <= 1}><Trash2 size={12} /> 删除最后一轮</button>
  </div>
  <div style={{ display: 'flex', gap: 4, border: '1px solid var(--border)', borderRadius: 6, padding: 4 }}>
    <button className="btn btn-secondary btn-sm" onClick={addTurn}><Plus size={12} /> 增加 AI 位置</button>
    <button className="btn btn-ghost btn-sm" onClick={removeTurn} disabled={matrix[0]?.length <= 1}><Trash2 size={12} /> 删除最后 AI 位</button>
  </div>
</div>

            <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button className="btn btn-danger btn-sm" onClick={deleteProfile} disabled={activeProfileId === 'default'}><Trash2 size={12} /> 删除当前</button>
              <button className="btn btn-secondary btn-sm" onClick={saveAsNew}><Save size={12} /> 另存为新模板</button>
              <button className="btn btn-primary btn-sm" onClick={saveProfile}><Save size={12} /> 保存当前模板</button>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowTemplateDialog(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {/* ====== 帮助 ====== */}
      {showHelpDialog && (
        <div className="modal-overlay" onClick={() => setShowHelpDialog(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 440 }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Prompt 占位符说明</h3>
            <div style={{ fontSize: 13, lineHeight: 1.7 }}>
              <p><code>{'{topic}'}</code>：当前讨论主题</p>
              <p><code>{'{target_ai}'}</code>：这次要发给哪个 AI</p>
              <p><code>{'{messages}'}</code>：自动整理好的接力上下文</p>
              <p><code>{'{latest_user_message}'}</code>：最近一次"我"的发言</p>
              <p><code>{'{round}'}</code>：当前是第几轮用户问题</p>
              <p><code>{'{turn}'}</code>：当前是这一轮里的第几个 AI 接力发言</p>
              <p><code>{'{separator}'}</code>：AI 发言分隔符</p>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn btn-primary btn-sm" onClick={() => setShowHelpDialog(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {/* ====== API 配置 ====== */}
      {showApiConfig && (
        <div className="modal-overlay" onClick={() => setShowApiConfig(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 400 }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>配置 {apiName}</h3>

            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>网页地址</label>
            <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
              <input className="topic-input" placeholder="https://..." value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} />
              <button className="btn btn-ghost btn-sm" onClick={() => apiUrl && window.open(apiUrl, '_blank')}><Globe size={14} /></button>
            </div>

            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginTop: 12, display: 'block' }}>服务商</label>
            <select className="select" value={apiProvider} onChange={(e) => setApiProvider(e.target.value)} style={{ marginTop: 4 }}>
              <option value="deepseek">DeepSeek</option>
              <option value="openai">OpenAI</option>
              <option value="zhipu">智谱 GLM</option>
              <option value="moonshot">Moonshot</option>
              <option value="minimax">MiniMax</option>
            </select>

            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginTop: 12, display: 'block' }}>API Key</label>
            <input className="topic-input" type="password" placeholder="sk-..." value={apiKey} onChange={(e) => setApiKey(e.target.value)} style={{ marginTop: 4 }} />

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowApiConfig(false)}>取消</button>
              <button className="btn btn-primary btn-sm" onClick={saveApiKey}>保存</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}