'use client';

import { useSearchParams } from 'next/navigation';
import { useState, useEffect, Suspense, useRef } from 'react';
import './analysis.css';
import { API_URL, apiFetch } from '../../lib/api';
import { logError } from '../../lib/logger';
import { Detection } from '../../lib/detection';
import { useDetection } from './use-detection';

// Class ID to Name mapping
const CLASS_NAMES: Record<number, string> = {
  1: 'Manual Valve',
  2: 'Ball Valve',
  3: 'Globe Valve',
  4: 'Gate Valve',
  5: 'Diaphragm Valve',
  6: 'Butterfly Valve',
  7: 'Plug Valve',
  8: 'Check Valve',
  9: 'Angle Valve',
  10: 'Needle Valve',
  11: 'Three-Way Valve',
  12: 'Closed Valve',
  13: 'Closed Ball',
  14: 'Control Valve',
  15: 'Rotary Valve',
  16: 'Rotary Closed Valve',
  17: 'Open Disc',
  18: 'Closed Spectacle Blind',
  19: 'Open Spectacle Blind',
  20: 'Reducer',
  21: 'Flange',
  22: 'Filter',
  23: 'Exchanger',
  24: 'Mid Arrow',
  25: 'Instrument',
  26: 'Instrument',
  27: 'Instrument',
  28: 'Instrument',
  29: 'Instrument',
  30: 'Instrument Tag',
  31: 'Shared Indicator',
  32: 'Line Label',
};

// Colors for different classes
const CLASS_COLORS: Record<number, string> = {
  2: '#FF6B6B', // Ball Valve - Red
  5: '#4ECDC4', // Diaphragm Valve - Teal
  6: '#45B7D1', // Butterfly Valve - Blue
  11: '#96CEB4', // Three-Way Valve - Green
  14: '#FFEAA7', // Control Valve - Yellow
  17: '#DDA0DD', // Open Disc - Plum
  21: '#98D8C8', // Flange - Mint
  25: '#F7DC6F', // Instrument - Gold
  30: '#BB8FCE', // Instrument Tag - Purple
};

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface DiagramOverlayProps {
  fileUrl: string;
  fileName: string | null;
  activeTab: 'all' | 'tags' | 'components';
  detections: Detection[];
}

function DiagramOverlay({ fileUrl, fileName, activeTab, detections }: DiagramOverlayProps) {
  const [imageLoaded, setImageLoaded] = useState(false);

  return (
    <div className="diagram-overlay">
      <div className="image-with-boxes">
        <img
          src={`${API_URL}${fileUrl}`}
          alt={fileName || 'P&ID Diagram'}
          className="diagram-overlay-image"
          onLoad={() => setImageLoaded(true)}
        />
        {/* Component bounding boxes */}
        {imageLoaded &&
          (activeTab === 'all' || activeTab === 'components') &&
          detections.map((det, index) => {
            const [origH, origW] = det.image_hw;
            const color = CLASS_COLORS[det.class_id] || '#00FF00';

            return (
              <div
                key={`comp-${index}`}
                className="bounding-box component-box"
                style={{
                  left: `${(det.x1 / origW) * 100}%`,
                  top: `${(det.y1 / origH) * 100}%`,
                  width: `${((det.x2 - det.x1) / origW) * 100}%`,
                  height: `${((det.y2 - det.y1) / origH) * 100}%`,
                  borderColor: color,
                }}
                title={`C${index} - ${CLASS_NAMES[det.class_id] || `Class ${det.class_id}`} (match score ${det.conf.toFixed(3)})`}
              >
                <span className="box-id-badge" style={{ backgroundColor: color }}>
                  C{index}
                </span>
                <span className="box-label" style={{ backgroundColor: color }}>
                  {CLASS_NAMES[det.class_id] || `Class ${det.class_id}`}
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
}

function DetectionSummary({ detection }: { detection: ReturnType<typeof useDetection> }) {
  const detections = detection.result?.detections || [];
  return (
    <div className="summary-container">
      <div className="summary-header">
        <h2 className="summary-title">Summary</h2>
        <span className="detection-count">{detections.length} components detected</span>
      </div>
      <div className="summary-content">
        <p>Template matching only: original scale and orientation; scores are not probabilities.</p>
        {detection.loading && <p role="status">Detecting components...</p>}
        {detection.error && (
          <div role="alert">
            {detection.error} <button onClick={detection.retry}>Try again</button>
          </div>
        )}
        {detection.result && detections.length === 0 && (
          <p role="status">No matching components found.</p>
        )}
        {detection.result?.limit_reached && <p>Result limit reached: showing up to 100 matches.</p>}
        <div className="summary-sections">
          <div className="components-section">
            <h3>Components ({detections.length})</h3>
            <div className="components-list">
              {detections.map((det, index) => (
                <div key={index} className="component-item">
                  <div
                    className="component-count"
                    style={{ backgroundColor: CLASS_COLORS[det.class_id] || '#00879F' }}
                  >
                    {det.class_id}
                  </div>
                  <span>{CLASS_NAMES[det.class_id] || `Class ${det.class_id}`}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="detected-texts-section">
            <h3>Detected Texts (0)</h3>
            <p>OCR is unavailable. No text recognition was performed.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function storedUploadName(storedName: string | null, fileUrl: string | null) {
  return storedName || fileUrl?.split('/').pop() || null;
}

function AnalysisContent() {
  const searchParams = useSearchParams();
  const fileUrl = searchParams.get('file');
  const fileName = searchParams.get('name');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('ALLAM');
  const storedName = storedUploadName(searchParams.get('stored_name'), fileUrl);
  const detection = useDetection(storedName);
  const detections = detection.result?.detections || [];
  const [activeTab, setActiveTab] = useState<'all' | 'tags' | 'components'>('components');

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatEnabled, setChatEnabled] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch('/api/features', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Features unavailable');
        return response.json() as Promise<{ chat: boolean }>;
      })
      .then((features) => setChatEnabled(features.chat === true))
      .catch(() => setChatEnabled(false));
    return () => controller.abort();
  }, []);

  const models = ['ALLAM', 'Llama', 'Qwen', 'GPT-OSS'];

  const handleModelSelect = (model: string) => {
    setSelectedModel(model);
    setIsDropdownOpen(false);
  };

  // Send chat message to Groq API
  const sendMessage = async () => {
    if (!chatInput.trim() || isLoading || !chatEnabled) return;

    const userMessage: ChatMessage = { role: 'user', content: chatInput.trim() };
    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput('');
    setIsLoading(true);

    try {
      const response = await apiFetch('/api/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...chatMessages, userMessage],
          model: selectedModel,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();
      const assistantMessage: ChatMessage = { role: 'assistant', content: data.response };
      setChatMessages((prev) => [...prev, assistantMessage]);
    } catch {
      logError('chat_failed');
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Enter key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatMessages]);

  return (
    <div className="analysis-page">
      <div className="analysis-wrapper">
        {/* Main Container */}
        <div className="analysis-container">
          {/* P&ID Section (Left) */}
          <div className="pid-section">
            <div className="right-section-wrapper">
              <img
                src="/right_screen_second.svg"
                alt="P&ID Highlight"
                className="right-section-bg"
              />
              {/* Tabs */}
              <div className="pid-tabs">
                <button
                  className={`pid-tab ${activeTab === 'all' ? 'active' : ''}`}
                  onClick={() => setActiveTab('all')}
                >
                  All
                </button>
                <button
                  className={`pid-tab ${activeTab === 'tags' ? 'active' : ''}`}
                  onClick={() => setActiveTab('tags')}
                >
                  Tags <span className="tab-count">0</span>
                </button>
                <button
                  className={`pid-tab ${activeTab === 'components' ? 'active' : ''}`}
                  onClick={() => setActiveTab('components')}
                >
                  Components <span className="tab-count">{detections.length}</span>
                </button>
              </div>
              {fileUrl && (
                <DiagramOverlay
                  key={fileUrl}
                  fileUrl={fileUrl}
                  fileName={fileName}
                  activeTab={activeTab}
                  detections={detections}
                />
              )}
            </div>
          </div>

          {/* Chat Section (Right) */}
          <div className="chat-section">
            {/* Chat Header with Model Selector */}
            <div className="chat-header">
              <div
                className="dropdown-trigger-area"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              >
                <span>{selectedModel}</span>
                {/* Dropdown menu */}
                {isDropdownOpen && (
                  <div className="model-dropdown-overlay" onClick={(e) => e.stopPropagation()}>
                    <div className="dropdown-items">
                      {models.map((model, index) => (
                        <div
                          key={index}
                          className={`dropdown-item ${model === selectedModel ? 'selected' : ''}`}
                          onClick={() => handleModelSelect(model)}
                        >
                          <span>{model}</span>
                          {model === selectedModel && (
                            <svg
                              className="check-icon"
                              viewBox="0 0 20 20"
                              fill="none"
                              xmlns="http://www.w3.org/2000/svg"
                            >
                              <path
                                d="M16.6667 5L7.50004 14.1667L3.33337 10"
                                stroke="#00879F"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Chat messages area */}
            <div className="chat-messages-area" ref={chatContainerRef}>
              {chatMessages.length === 0 ? (
                <div className="chat-placeholder">
                  <p>Ask me anything about this P&ID diagram...</p>
                </div>
              ) : (
                chatMessages.map((msg, index) => (
                  <div key={index} className={`chat-message ${msg.role}`}>
                    <div className="message-content">{msg.content}</div>
                  </div>
                ))
              )}
              {isLoading && (
                <div className="chat-message assistant">
                  <div className="message-content loading">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </div>
                </div>
              )}
            </div>

            {/* Chat input area */}
            <div className="chat-input-area">
              <input
                type="text"
                className="chat-input"
                placeholder={chatEnabled ? 'Type your message...' : 'Chat is currently unavailable'}
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading || !chatEnabled}
              />
              <button
                className="chat-send-btn"
                aria-label="Send message"
                onClick={sendMessage}
                disabled={isLoading || !chatInput.trim() || !chatEnabled}
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M22 2L11 13"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M22 2L15 22L11 13L2 9L22 2Z"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <DetectionSummary detection={detection} />
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AnalysisContent />
    </Suspense>
  );
}
