import React, { useState, useRef, useEffect } from "react";
import "./index.css";

const generateId = () => Math.random().toString(36).substr(2, 9);

const API_BASE_URL = "";

function App() {
  const [chats, setChats] = useState(() => {
    const saved = localStorage.getItem("selah_chats");
    return saved ? JSON.parse(saved) : [{ id: generateId(), title: "New Session", messages: [{ sender: "selah", text: "SELAH Core System Online. Awaiting input." }] }];
  });
  const [currentChatId, setCurrentChatId] = useState(() => chats[0]?.id);
  const [tempMessages, setTempMessages] = useState([]);
  const [isTemp, setIsTemp] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [activePersona, setActivePersona] = useState("os");
  const [telemetry, setTelemetry] = useState(null);
  const [isTelemetryOpen, setIsTelemetryOpen] = useState(true);
  const [screenAnalysis, setScreenAnalysis] = useState(null);
  const [isScanningScreen, setIsScanningScreen] = useState(false);
  const [osConsoleLogs, setOsConsoleLogs] = useState([]);
  const [osInput, setOsInput] = useState("");
  const [isOsRunning, setIsOsRunning] = useState(false);
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0, chatId: null });
  const [renamingChatId, setRenamingChatId] = useState(null);
  const [renamingTitle, setRenamingTitle] = useState("");
  const chatFeedRef = useRef(null);
  const osTerminalLogsRef = useRef(null);

  // Client-specific Gemini API settings
  const [customApiKey, setCustomApiKey] = useState(() => {
    return localStorage.getItem("selah_custom_api_key") || "";
  });
  const [modelPreference, setModelPreference] = useState(() => {
    return localStorage.getItem("selah_model_preference") || "normal";
  });

  useEffect(() => {
    localStorage.setItem("selah_custom_api_key", customApiKey);
  }, [customApiKey]);

  useEffect(() => {
    localStorage.setItem("selah_model_preference", modelPreference);
  }, [modelPreference]);

  const scanScreen = async () => {
    setIsScanningScreen(true);
    try {
      const headers = { "Content-Type": "application/json" };
      if (customApiKey) {
        headers["X-Gemini-API-Key"] = customApiKey;
      }
      headers["X-Gemini-Model-Preference"] = modelPreference;

      const res = await fetch(`${API_BASE_URL}/screen/analyze`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ persona: activePersona, model_preference: modelPreference }),
      });
      const data = await res.json();
      if (data.analysis) {
        setScreenAnalysis(data.analysis);
        updateCurrentChatMessages(prev => [...prev, { sender: "selah", text: `📷 **Screen Monitored**:\n\n${data.analysis}` }]);
      }
    } catch (err) {
      console.error("Screen analysis error:", err);
    }
    setIsScanningScreen(false);
  };

  const handleOsConsoleSubmit = async () => {
    if (!osInput.trim()) return;
    const cmd = osInput;
    setOsInput("");
    setOsConsoleLogs(prev => [...prev, `> ${cmd}`]);
    setIsOsRunning(true);

    try {
      const headers = { "Content-Type": "application/json" };
      if (customApiKey) {
        headers["X-Gemini-API-Key"] = customApiKey;
      }
      headers["X-Gemini-Model-Preference"] = modelPreference;

      const res = await fetch(`${API_BASE_URL}/agent/execute`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ message: cmd, model_preference: modelPreference }),
      });
      const data = await res.json();
      setOsConsoleLogs(prev => [...prev, data.response]);
      updateCurrentChatMessages(prev => [...prev, { sender: "selah", text: `⚙️ **OS Command Executed**: *"${cmd}"*\n\n\`\`\`\n${data.response}\n\`\`\`` }]);
      fetchTelemetry();
    } catch (err) {
      setOsConsoleLogs(prev => [...prev, "❌ Error: API connection severed."]);
    }
    setIsOsRunning(false);
  };

  const currentMessages = isTemp ? tempMessages : (chats.find(c => c.id === currentChatId)?.messages || []);

  const fetchTelemetry = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/telemetry`);
      const data = await res.json();
      if (!data.error) {
        setTelemetry(data);
      }
    } catch (err) {
      console.error("Telemetry server offline");
    }
  };

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!isTemp) localStorage.setItem("selah_chats", JSON.stringify(chats));
  }, [chats, isTemp]);

  useEffect(() => {
    if (osTerminalLogsRef.current) {
      osTerminalLogsRef.current.scrollTop = osTerminalLogsRef.current.scrollHeight;
    }
  }, [osConsoleLogs, isOsRunning]);

  useEffect(() => {
    const handleCloseContextMenu = () => {
      setContextMenu(prev => prev.visible ? { ...prev, visible: false } : prev);
    };
    window.addEventListener("click", handleCloseContextMenu);
    return () => window.removeEventListener("click", handleCloseContextMenu);
  }, []);

  const handleChatContextMenu = (e, chatId) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      chatId: chatId
    });
  };

  const saveChatTitle = (chatId) => {
    if (!renamingTitle.trim()) {
      setRenamingChatId(null);
      return;
    }
    setChats(prevChats => prevChats.map(chat => {
      if (chat.id === chatId) {
        return { ...chat, title: renamingTitle.trim() };
      }
      return chat;
    }));
    setRenamingChatId(null);
  };

  const createNewChat = () => {
    setIsTemp(false);
    const newId = generateId();
    setChats([{ id: newId, title: "New Session", messages: [{ sender: "selah", text: "SELAH Core System Online. Awaiting input." }] }, ...chats]);
    setCurrentChatId(newId);
    setIsSidebarOpen(false);
  };

  const createTempChat = () => {
    setIsTemp(true);
    setTempMessages([{ sender: "selah", text: "⚠️ Temp Mode Active. History will not be saved." }]);
    setIsSidebarOpen(false);
  };

  const deleteChat = (id, e) => {
    e.stopPropagation();
    const updatedChats = chats.filter(c => c.id !== id);
    if (updatedChats.length === 0) {
      const newId = generateId();
      const defaultChat = {
        id: newId,
        title: "New Session",
        messages: [{ sender: "selah", text: "SELAH Core System Online. Awaiting input." }]
      };
      setChats([defaultChat]);
      setCurrentChatId(newId);
    } else {
      setChats(updatedChats);
      if (currentChatId === id) {
        setCurrentChatId(updatedChats[0].id);
      }
    }
  };

  const updateCurrentChatMessages = (updater) => {
    if (isTemp) {
      setTempMessages(updater);
    } else {
      setChats(prevChats => prevChats.map(chat => {
        if (chat.id === currentChatId) {
          const newMessages = typeof updater === 'function' ? updater(chat.messages) : updater;
          // Auto-update title based on first user message
          const title = chat.title === "New Session" && newMessages.find(m => m.sender === 'user')
            ? newMessages.find(m => m.sender === 'user').text.substring(0, 20) + "..."
            : chat.title;
          return { ...chat, messages: newMessages, title };
        }
        return chat;
      }));
    }
  };

  const formatMessage = (text) => {
    const htmlText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.*?)`/g, '<code class="inline-cyber-code">$1</code>')
      .replace(/\n/g, '<br/>');
    return { __html: htmlText };
  };

  const renderMessageContent = (text) => {
    if (!text) return null;

    // Split by markdown code blocks: ```
    const parts = text.split(/```/g);
    if (parts.length === 1) {
      return <span dangerouslySetInnerHTML={formatMessage(text)} />;
    }

    return parts.map((part, idx) => {
      // Odd indices are code blocks
      if (idx % 2 === 1) {
        const lines = part.split("\n");
        let language = "";
        let code = part;

        if (lines.length > 0 && /^[a-zA-Z]+$/.test(lines[0].trim())) {
          language = lines[0].trim();
          code = lines.slice(1).join("\n").trim();
        } else {
          code = part.trim();
        }

        return (
          <div key={idx} className="cyber-code-block-container">
            <div className="cyber-code-header">
              <span className="cyber-code-lang">{language.toUpperCase() || "COMMAND"}</span>
              <span className="cyber-status-pulse"></span>
            </div>
            <pre className="cyber-code-pre">
              <code>{code}</code>
            </pre>
            <div className="cyber-code-actions">
              <button
                className="cyber-code-btn copy-btn"
                onClick={() => {
                  navigator.clipboard.writeText(code);
                }}
              >
                📋 Copy Command
              </button>
              <button
                className="cyber-code-btn run-btn"
                onClick={() => {
                  setOsInput(code);
                  setIsTelemetryOpen(true);
                  setTimeout(() => {
                    const shellInput = document.querySelector(".shell-input-field");
                    if (shellInput) {
                      shellInput.focus();
                    }
                  }, 100);
                }}
              >
                ⚡ Send to Terminal
              </button>
            </div>
          </div>
        );
      } else {
        return <span key={idx} dangerouslySetInnerHTML={formatMessage(part)} />;
      }
    });
  };

  const sendMessage = async (overrideInput) => {
    const textToSend = overrideInput || input;
    if (!textToSend.trim()) return;

    const userMessage = { sender: "user", text: textToSend };
    updateCurrentChatMessages(prev => [...prev, userMessage]);
    if (!overrideInput) setInput("");
    setIsTyping(true);

    try {
      const headers = { "Content-Type": "application/json" };
      if (customApiKey) {
        headers["X-Gemini-API-Key"] = customApiKey;
      }
      headers["X-Gemini-Model-Preference"] = modelPreference;

      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ 
          message: userMessage.text, 
          persona: activePersona,
          model_preference: modelPreference 
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        updateCurrentChatMessages(prev => [...prev, { sender: "selah", text: `⚠️ **Server Core Error**: ${errText || 'Core returned an invalid state.'}` }]);
        setIsTyping(false);
        return;
      }

      const data = await res.json();
      updateCurrentChatMessages(prev => [...prev, { sender: "selah", text: data.response }]);
      fetchTelemetry();
    } catch (err) {
      updateCurrentChatMessages(prev => [...prev, { sender: "selah", text: "Error: Connection to core severed." }]);
    }

    setIsTyping(false);
  };

  // Instant scroll when switching sessions to keep header/view perfectly stable
  useEffect(() => {
    if (chatFeedRef.current) {
      chatFeedRef.current.scrollTop = chatFeedRef.current.scrollHeight;
    }
  }, [currentChatId]);

  // Smooth scroll when sending/receiving messages or when typing state updates
  useEffect(() => {
    if (chatFeedRef.current) {
      chatFeedRef.current.scrollTo({
        top: chatFeedRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [currentMessages.length, isTyping]);

  return (
    <div className={`app-container ${activePersona}-theme`}>
      <div className="bg-glow top-left"></div>
      <div className="bg-glow bottom-right"></div>

      <div className={`hud-glass hud-layout ${isSidebarCollapsed ? 'sidebar-collapsed' : ''} ${isTelemetryOpen ? 'telemetry-open' : ''}`}>

        {/* Overlay to close sidebar on mobile/small screens */}
        {isSidebarOpen && <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)}></div>}

        {/* Sidebar */}
        <div className={`sidebar ${isSidebarOpen ? 'open' : ''} ${isSidebarCollapsed ? 'collapsed' : ''}`}>
          <div className="brand sidebar-brand">
            <div className="status-dot"></div>
            <h2>SELAH<span className="accent">_OS</span></h2>
            <button className="close-btn" onClick={() => setIsSidebarOpen(false)}>×</button>
          </div>
          <div className="sidebar-actions">
            <button onClick={createNewChat} className="hud-button full-width">⊕ New Session</button>
            <button onClick={createTempChat} className={`hud-button full-width temp-btn ${isTemp ? 'active' : ''}`}>🕵️ Temp Mode</button>
          </div>
          <div className="history-list">
            <div className="history-title">SESSION LOGS</div>
            {chats.map(chat => (
              <div
                key={chat.id}
                className={`history-item ${!isTemp && currentChatId === chat.id ? 'active' : ''}`}
                onClick={() => {
                  if (renamingChatId === chat.id) return;
                  setIsTemp(false);
                  setCurrentChatId(chat.id);
                  setIsSidebarOpen(false);
                }}
                onContextMenu={(e) => handleChatContextMenu(e, chat.id)}
              >
                {renamingChatId === chat.id ? (
                  <input
                    type="text"
                    value={renamingTitle}
                    onChange={(e) => setRenamingTitle(e.target.value)}
                    onBlur={() => saveChatTitle(chat.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveChatTitle(chat.id);
                      if (e.key === "Escape") setRenamingChatId(null);
                    }}
                    className="rename-chat-input"
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span className="history-item-title">{chat.title}</span>
                )}
                <button
                  className="delete-chat-btn"
                  onClick={(e) => deleteChat(chat.id, e)}
                  title="Terminate Session Log"
                  aria-label="Terminate Session Log"
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          {/* AI Settings Overlay panel in Sidebar */}
          <div className="cyber-settings-panel">
            <div className="history-title">NEURAL LINK</div>
            <div className="settings-field">
              <label className="settings-lbl">AI CORE SELECTOR</label>
              <div className="model-toggle-hud">
                <button
                  className={`toggle-btn ${modelPreference === "normal" ? "active" : ""}`}
                  onClick={() => setModelPreference("normal")}
                  title="Activate Standard Model (Gemini 1.5 Flash)"
                >
                  NORMAL (Flash)
                </button>
                <button
                  className={`toggle-btn ${modelPreference === "pro" ? "active" : ""}`}
                  onClick={() => setModelPreference("pro")}
                  title="Activate Ultra Reasoning Model (Gemini 1.5 Pro)"
                >
                  PRO (1.5 Pro)
                </button>
              </div>
            </div>
            <div className="settings-field">
              <label className="settings-lbl">CLIENT API KEY (OVERRIDE)</label>
              <div className="settings-input-container">
                <input
                  type="password"
                  placeholder="Enter GEMINI_API_KEY..."
                  value={customApiKey}
                  onChange={(e) => setCustomApiKey(e.target.value)}
                  className="hud-input settings-input"
                  title="Device API Key configuration overrides host machine keys"
                />
                {customApiKey && (
                  <button
                    className="clear-key-btn"
                    onClick={() => setCustomApiKey("")}
                    title="Purge Custom Device Key"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="main-chat">
          <div className="hud-header">
            <button
              className="sidebar-toggle"
              onClick={() => {
                setIsSidebarOpen(prev => !prev);
                setIsSidebarCollapsed(prev => !prev);
              }}
              title="Toggle Navigation Menu"
              aria-label="Toggle Navigation Menu"
            >
              <span className="toggle-icon">☰</span>
              <span className="toggle-text"> MENU</span>
            </button>
            <div className="header-left">
              <div className="session-info">
                {isTemp ? (
                  <span className="warning-text">⚠️ INCOGNITO PROTOCOL</span>
                ) : (
                  <span className="session-text">{chats.find(c => c.id === currentChatId)?.title || "Active"}
                  </span>
                )}
              </div>
            </div>
            <div className="system-telemetry">
              <span className="telemetry-item"><span className="label">SYS</span> <span className="value success">ONLINE</span></span>
              <span className="telemetry-item"><span className="label">VER</span> <span className="value">0.1.2</span></span>
              <span className="telemetry-item">
                <button
                  className="telemetry-toggle"
                  onClick={() => setIsTelemetryOpen(prev => !prev)}
                  title="Toggle HUD Telemetry Panel"
                  aria-label="Toggle HUD Telemetry Panel"
                >
                  <span className="telemetry-toggle-icon">⚡</span>
                  <span className="telemetry-toggle-text"> TELEMETRY</span>
                </button>
              </span>
            </div>
          </div>

          <div className="chat-feed" ref={chatFeedRef}>
            {currentMessages.map((msg, idx) => (
              <div key={idx} className={`message-row ${msg.sender}`}>
                {msg.sender === "selah" && <div className="avatar selah-avatar">S</div>}
                <div className={`message-bubble ${msg.sender}`}>
                  {renderMessageContent(msg.text)}
                </div>
                {msg.sender === "user" && <div className="avatar user-avatar">U</div>}
              </div>
            ))}

            {isTyping && (
              <div className="message-row selah">
                <div className="avatar selah-avatar pulse-anim">S</div>
                <div className="typing-indicator">
                  <span>.</span><span>.</span><span>.</span>
                </div>
              </div>
            )}
          </div>

          <div className="input-terminal">
            <div className="terminal-prefix">&gt;</div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Initialize command..."
              className="hud-input"
              autoFocus
            />
            <button onClick={() => sendMessage()} className="hud-button">
              EXECUTE
            </button>
          </div>
        </div>

        {/* Right HUD Telemetry Panel */}
        <div className={`telemetry-panel ${isTelemetryOpen ? 'open' : ''}`}>
          <div className="telemetry-panel-header">
            <h3>NEURAL TELEMETRY</h3>
            <button className="telemetry-close" onClick={() => setIsTelemetryOpen(false)}>×</button>
          </div>

          <div className="telemetry-panel-content">

            {/* Persona Selector Card */}
            <div className="hud-card persona-card">
              <div className="hud-card-header">ACTIVE PERSONA</div>
              <div className="persona-selector">
                <button
                  className={`persona-btn os-btn ${activePersona === 'os' ? 'active' : ''}`}
                  onClick={() => setActivePersona('os')}
                >
                  <span className="p-icon">🤖</span>
                  <span className="p-label">CORE OS</span>
                </button>
                <button
                  className={`persona-btn coach-btn ${activePersona === 'coach' ? 'active' : ''}`}
                  onClick={() => setActivePersona('coach')}
                >
                  <span className="p-icon">💜</span>
                  <span className="p-label">COACH</span>
                </button>
                <button
                  className={`persona-btn sage-btn ${activePersona === 'sage' ? 'active' : ''}`}
                  onClick={() => setActivePersona('sage')}
                >
                  <span className="p-icon">🔱</span>
                  <span className="p-label">SAGE</span>
                </button>
              </div>
              <div className="persona-desc">
                {activePersona === 'os' && "Advanced cybernetic personal operating system. Tone is cool, precise, structured, analyzes telemetry as raw inputs."}
                {activePersona === 'coach' && "Empathetic mental wellness coach. Tone is exceptionally warm, gentle, compassionate, focused on self-care."}
                {activePersona === 'sage' && "Socratic philosophical companion. Tone is reflective, thoughtful, deep, asking gentle introspective questions."}
              </div>
            </div>

            {/* Quick Action Chips Card */}
            <div className="hud-card action-chips-card">
              <div className="hud-card-header">INTELLIGENCE ACTIONS</div>
              <div className="action-chips">
                <button className="action-chip" onClick={() => setInput("reframe: ")}>
                  🧠 Reframe Thought
                </button>
                <button className="action-chip" onClick={() => setInput("dream: ")}>
                  🌙 Interpret Dream
                </button>
                <button className="action-chip" onClick={() => {
                  sendMessage("weekly wisdom");
                }}>
                  📝 Weekly Wisdom
                </button>
                <button className="action-chip" onClick={() => {
                  sendMessage("help me stabilize");
                }}>
                  🔋 Stabilize System
                </button>
              </div>
            </div>

            {/* Monitor Screen Vision Card */}
            <div className="hud-card screen-scanner-card">
              <div className="hud-card-header">MONITOR SCREEN</div>

              <div className="scanner-radar-hud">
                <button
                  className={`hud-button full-width ${isScanningScreen ? 'scanning-btn' : ''}`}
                  onClick={scanScreen}
                  disabled={isScanningScreen}
                >
                  {isScanningScreen ? "📡 MONITORING SCREEN..." : "📸 MONITOR SCREEN"}
                </button>
              </div>

              {screenAnalysis && (
                <div className="screen-analysis-result slide-in-hud">
                  <div className="analysis-text-block" dangerouslySetInnerHTML={formatMessage(screenAnalysis)}></div>
                </div>
              )}
            </div>

            {/* Live Telemetry stats Card */}
            {telemetry ? (
              <>
                <div className="hud-card telemetry-metrics-card">
                  <div className="hud-card-header">PSYCHOLOGICAL LIFE TELEMETRY</div>
                  <div className="metric-row-hud">
                    <span className="m-label">STABILITY</span>
                    <span className={`m-val ${telemetry.stability.includes('volatile') || telemetry.stability.includes('instability') ? 'danger' : telemetry.stability.includes('variable') ? 'warning' : 'success'}`}>
                      {telemetry.stability.replace('Emotional Stability:', '').replace('stability:', '').replace('pattern', '').trim()}
                    </span>
                  </div>
                  <div className="metric-row-hud">
                    <span className="m-label">BURNOUT RISK</span>
                    <span className={`m-val ${telemetry.burnout.includes('🔴') || telemetry.burnout.includes('likely') ? 'danger' : telemetry.burnout.includes('🟡') || telemetry.burnout.includes('rising') ? 'warning' : 'success'}`}>
                      {telemetry.burnout.replace('🔴', '').replace('🟡', '').replace('🟢', '').replace('Burnout risk currently', '').trim()}
                    </span>
                  </div>
                </div>

                <div className="hud-card goals-progress-card">
                  <div className="hud-card-header">GOAL MATRIX HUD</div>
                  <div className="goals-meters">
                    <div className="g-meter-col">
                      <div className="g-meter-val success">{telemetry.completed_goals}</div>
                      <div className="g-meter-lbl">COMPLETED</div>
                    </div>
                    <div className="g-meter-col">
                      <div className="g-meter-val primary">{telemetry.active_goals}</div>
                      <div className="g-meter-lbl">ACTIVE</div>
                    </div>
                    <div className="g-meter-col">
                      <div className="g-meter-val warning">{telemetry.deferred_goals}</div>
                      <div className="g-meter-lbl">DEFERRED</div>
                    </div>
                  </div>
                </div>

                <div className="hud-card anchors-card">
                  <div className="hud-card-header">LIFE ANCHORS DETECTED</div>
                  <div className="anchors-list">
                    {telemetry.anchors && telemetry.anchors.length > 0 ? (
                      telemetry.anchors.map((anchor, i) => (
                        <span key={i} className="anchor-tag">⚓ {anchor}</span>
                      ))
                    ) : (
                      <span className="no-data">Scanning for grounding anchors...</span>
                    )}
                  </div>
                </div>

                <div className="hud-card triggers-card">
                  <div className="hud-card-header">ACTIVE FATIGUE TRIGGERS</div>
                  <div className="triggers-list">
                    {telemetry.triggers && telemetry.triggers.length > 0 ? (
                      telemetry.triggers.map((trigger, i) => (
                        <span key={i} className="trigger-tag">⚠️ {trigger}</span>
                      ))
                    ) : (
                      <span className="no-data success-text">🟢 No warning triggers detected</span>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="hud-loading">
                <div className="loading-bar-hud">
                  <div className="loading-progress-hud"></div>
                </div>
                <span>INITIALIZING NEURAL TELEMETRY HUD...</span>
              </div>
            )}

            {/* OS Control Terminal Console Card */}
            <div className="hud-card os-terminal-card">
              <div className="hud-card-header">OS AGENT TERMINAL</div>
              <div className="os-terminal-shell">
                <div className="terminal-logs-hud" ref={osTerminalLogsRef}>
                  <div className="log-line-system">[SYS_READY] SELAH_OS Agent Terminal Online.</div>
                  {osConsoleLogs.map((log, i) => (
                    <div key={i} className={log.startsWith('>') ? 'log-line-user' : 'log-line-result'}>
                      {log}
                    </div>
                  ))}
                  {isOsRunning && <div className="log-line-system pulse-anim">Executing system dispatcher automation...</div>}
                </div>
                <div className="terminal-shell-input">
                  <span className="shell-symbol">&gt;</span>
                  <input
                    type="text"
                    value={osInput}
                    onChange={(e) => setOsInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleOsConsoleSubmit()}
                    placeholder="Enter OS agent command..."
                    className="shell-input-field"
                    disabled={isOsRunning}
                  />
                </div>
              </div>
            </div>

          </div>
        </div>

      </div>
      {contextMenu.visible && (
        <div
          className="cyber-context-menu"
          style={{ top: contextMenu.y, left: contextMenu.x }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="context-menu-item"
            onClick={() => {
              setRenamingChatId(contextMenu.chatId);
              const chatToRename = chats.find(c => c.id === contextMenu.chatId);
              setRenamingTitle(chatToRename ? chatToRename.title : "");
              setContextMenu({ visible: false, x: 0, y: 0, chatId: null });
            }}
          >
            ✏️ Rename Session
          </button>
          <button
            className="context-menu-item danger"
            onClick={(e) => {
              deleteChat(contextMenu.chatId, e);
              setContextMenu({ visible: false, x: 0, y: 0, chatId: null });
            }}
          >
            ❌ Terminate Session
          </button>
        </div>
      )}
    </div>
  );
}

export default App;