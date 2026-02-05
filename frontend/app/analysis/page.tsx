'use client';

import { useSearchParams } from 'next/navigation';
import { useState, useEffect, Suspense, useRef } from 'react';
import './analysis.css';

// Class ID to Name mapping
const CLASS_NAMES: Record<number, string> = {
  1: "Manual Valve",
  2: "Ball Valve",
  3: "Globe Valve",
  4: "Gate Valve",
  5: "Diaphragm Valve",
  6: "Butterfly Valve",
  7: "Plug Valve",
  8: "Check Valve",
  9: "Angle Valve",
  10: "Needle Valve",
  11: "Three-Way Valve",
  12: "Closed Valve",
  13: "Closed Ball",
  14: "Control Valve",
  15: "Rotary Valve",
  16: "Rotary Closed Valve",
  17: "Open Disc",
  18: "Closed Spectacle Blind",
  19: "Open Spectacle Blind",
  20: "Reducer",
  21: "Flange",
  22: "Filter",
  23: "Exchanger",
  24: "Mid Arrow",
  25: "Instrument",
  26: "Instrument",
  27: "Instrument",
  28: "Instrument",
  29: "Instrument",
  30: "Instrument Tag",
  31: "Shared Indicator",
  32: "Line Label",
};

// Sample OCR results from pnid_orig
const SAMPLE_OCR = [
  { text: "KL-57680", conf: 0.973, box: [193, 730, 333, 773] },
  { text: "KL-08359", conf: 0.952, box: [193, 883, 340, 927] },
  { text: "-1038", conf: 0.889, box: [0, 910, 90, 950] },
  { text: "5\"-JF-4524", conf: 0.935, box: [642, 915, 795, 948] },
  { text: "75579", conf: 0.999, box: [0, 1377, 87, 1420] },
  { text: "ERV-4-67", conf: 0.335, box: [812, 23, 855, 160] },
  { text: "CD-36264", conf: 0.991, box: [810, 755, 857, 902] },
  { text: "CV-20158", conf: 0.966, box: [417, 748, 467, 902] },
  { text: "6\"", conf: 0.654, box: [322, 1023, 368, 1073] },
  { text: "IJ-51122", conf: 0.395, box: [813, 265, 857, 408] },
];

// Sample detections from pnid_orig with crop image paths
const SAMPLE_DETECTIONS = [
  { class_id: 5, conf: 0.926, x1: 853, y1: 305, x2: 906, y2: 384, image_hw: [1500, 1500], crop: '/crops/000_cls05_5.png' },
  { class_id: 2, conf: 0.922, x1: 853, y1: 762, x2: 906, y2: 829, image_hw: [1500, 1500], crop: '/crops/001_cls02_2.png' },
  { class_id: 6, conf: 0.918, x1: 218, y1: 925, x2: 292, y2: 978, image_hw: [1500, 1500], crop: '/crops/002_cls06_6.png' },
  { class_id: 14, conf: 0.917, x1: 307, y1: 777, x2: 418, y2: 869, image_hw: [1500, 1500], crop: '/crops/003_cls14_14.png' },
  { class_id: 30, conf: 0.911, x1: 0, y1: 657, x2: 62, y2: 750, image_hw: [1500, 1500], crop: '/crops/004_cls30_30.png' },
  { class_id: 17, conf: 0.906, x1: 313, y1: 1127, x2: 417, y2: 1165, image_hw: [1500, 1500], crop: '/crops/005_cls17_17.png' },
  { class_id: 25, conf: 0.902, x1: 845, y1: 81, x2: 916, y2: 152, image_hw: [1500, 1500], crop: '/crops/006_cls25_25.png' },
  { class_id: 6, conf: 0.898, x1: 227, y1: 676, x2: 325, y2: 730, image_hw: [1500, 1500], crop: '/crops/007_cls06_6.png' },
  { class_id: 21, conf: 0.862, x1: 364, y1: 1487, x2: 416, y2: 1500, image_hw: [1500, 1500], crop: '/crops/008_cls21_21.png' },
  { class_id: 11, conf: 0.600, x1: 0, y1: 1421, x2: 30, y2: 1473, image_hw: [1500, 1500], crop: '/crops/009_cls11_11.png' },
];

// Colors for different classes
const CLASS_COLORS: Record<number, string> = {
  2: '#FF6B6B',   // Ball Valve - Red
  5: '#4ECDC4',   // Diaphragm Valve - Teal
  6: '#45B7D1',   // Butterfly Valve - Blue
  11: '#96CEB4', // Three-Way Valve - Green
  14: '#FFEAA7', // Control Valve - Yellow
  17: '#DDA0DD', // Open Disc - Plum
  21: '#98D8C8', // Flange - Mint
  25: '#F7DC6F', // Instrument - Gold
  30: '#BB8FCE', // Instrument Tag - Purple
};

interface Detection {
  class_id: number;
  conf: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  image_hw: number[];
  crop?: string;
}

interface OcrItem {
  text: string;
  conf: number;
  box: number[]; // [x1, y1, x2, y2]
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

function AnalysisContent() {
  const searchParams = useSearchParams();
  const fileUrl = searchParams.get('file');
  const fileName = searchParams.get('name');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('ALLAM');
  const [detections, setDetections] = useState<Detection[]>([]);
  const [ocrItems, setOcrItems] = useState<OcrItem[]>([]);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'tags' | 'components'>('components');
  const [originalDimensions, setOriginalDimensions] = useState({ width: 1500, height: 1500 });
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Load detections and OCR when component mounts
  useEffect(() => {
    // For now, use sample data
    // Later this can come from an API
    setDetections(SAMPLE_DETECTIONS);
    setOcrItems(SAMPLE_OCR);
  }, [fileName]);

  const handleImageLoad = () => {
    if (imageRef.current) {
      setOriginalDimensions({
        width: imageRef.current.naturalWidth,
        height: imageRef.current.naturalHeight
      });
      setImageLoaded(true);
    }
  };

  const models = ['ALLAM', 'Llama', 'Qwen', 'GPT-OSS'];

  const handleModelSelect = (model: string) => {
    setSelectedModel(model);
    setIsDropdownOpen(false);
  };

  // Send chat message to Groq API
  const sendMessage = async () => {
    if (!chatInput.trim() || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: chatInput.trim() };
    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/chat/completions`, {
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
      setChatMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
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

  // Group detections by class for summary
  const groupedDetections = detections.reduce((acc, det) => {
    const className = CLASS_NAMES[det.class_id] || `Class ${det.class_id}`;
    if (!acc[className]) {
      acc[className] = [];
    }
    acc[className].push(det);
    return acc;
  }, {} as Record<string, Detection[]>);

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
                  Tags <span className="tab-count">{ocrItems.length}</span>
                </button>
                <button 
                  className={`pid-tab ${activeTab === 'components' ? 'active' : ''}`}
                  onClick={() => setActiveTab('components')}
                >
                  Components <span className="tab-count">{detections.length}</span>
                </button>
              </div>
              {fileUrl && (
                <div className="diagram-overlay" ref={containerRef}>
                  <div className="image-with-boxes">
                    <img 
                      ref={imageRef}
                      src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}${decodeURIComponent(fileUrl)}`}
                      alt={fileName ? decodeURIComponent(fileName) : 'P&ID Diagram'}
                      className="diagram-overlay-image"
                      onLoad={handleImageLoad}
                    />
                    {/* Component bounding boxes */}
                    {imageLoaded && imageRef.current && (activeTab === 'all' || activeTab === 'components') && detections.map((det, index) => {
                      const [origH, origW] = det.image_hw;
                      const color = CLASS_COLORS[det.class_id] || '#00FF00';
                      const displayedWidth = imageRef.current!.clientWidth;
                      const displayedHeight = imageRef.current!.clientHeight;
                      const scaleX = displayedWidth / origW;
                      const scaleY = displayedHeight / origH;
                      
                      return (
                        <div
                          key={`comp-${index}`}
                          className="bounding-box component-box"
                          style={{
                            left: `${det.x1 * scaleX}px`,
                            top: `${det.y1 * scaleY}px`,
                            width: `${(det.x2 - det.x1) * scaleX}px`,
                            height: `${(det.y2 - det.y1) * scaleY}px`,
                            borderColor: color,
                          }}
                          title={`C${index} - ${CLASS_NAMES[det.class_id] || `Class ${det.class_id}`} (${(det.conf * 100).toFixed(1)}%)`}
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
                    {/* OCR/Tag bounding boxes */}
                    {imageLoaded && imageRef.current && (activeTab === 'all' || activeTab === 'tags') && ocrItems.map((item, index) => {
                      const origW = 1500, origH = 1500; // OCR was done on 1500x1500 image
                      const displayedWidth = imageRef.current!.clientWidth;
                      const displayedHeight = imageRef.current!.clientHeight;
                      const scaleX = displayedWidth / origW;
                      const scaleY = displayedHeight / origH;
                      const [x1, y1, x2, y2] = item.box;
                      
                      return (
                        <div
                          key={`ocr-${index}`}
                          className="bounding-box ocr-box"
                          style={{
                            left: `${x1 * scaleX}px`,
                            top: `${y1 * scaleY}px`,
                            width: `${(x2 - x1) * scaleX}px`,
                            height: `${(y2 - y1) * scaleY}px`,
                            borderColor: '#FF9800',
                          }}
                          title={`"${item.text}" (${(item.conf * 100).toFixed(0)}%)`}
                        >
                          <span className="box-label" style={{ backgroundColor: '#FF9800' }}>
                            {item.text}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
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
                            <svg className="check-icon" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                              <path d="M16.6667 5L7.50004 14.1667L3.33337 10" stroke="#00879F" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
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
                placeholder="Type your message..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
              />
              <button 
                className="chat-send-btn"
                onClick={sendMessage}
                disabled={isLoading || !chatInput.trim()}
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Summary Container */}
        <div className="summary-container">
          <div className="summary-header">
            <h2 className="summary-title">Summary</h2>
            <span className="detection-count">{detections.length} components detected</span>
          </div>
          <div className="summary-content">
            <div className="summary-sections">
              {/* Components */}
              <div className="components-section">
                <h3>Components ({detections.length})</h3>
                <div className="components-list">
                  {detections.map((det, index) => (
                    <div key={index} className="component-item">
                      {det.crop ? (
                        <img 
                          src={det.crop} 
                          alt={CLASS_NAMES[det.class_id] || `Class ${det.class_id}`}
                          className="component-crop-image"
                        />
                      ) : (
                        <div 
                          className="component-count"
                          style={{ backgroundColor: CLASS_COLORS[det.class_id] || '#00879F' }}
                        >
                          {det.class_id}
                        </div>
                      )}
                      <span>{CLASS_NAMES[det.class_id] || `Class ${det.class_id}`}</span>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Detected Texts */}
              <div className="detected-texts-section">
                <h3>Detected Texts ({ocrItems.length})</h3>
                <div className="text-items">
                  {ocrItems.map((item, index) => (
                    <div 
                      key={index} 
                      className="text-badge"
                      onClick={() => navigator.clipboard.writeText(item.text)}
                      title={`Click to copy • Confidence: ${(item.conf * 100).toFixed(0)}%`}
                    >
                      <span>{item.text}</span>
                      <svg className="copy-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect x="5" y="5" width="9" height="9" rx="1" stroke="#00B8D4" strokeWidth="1.5"/>
                        <path d="M3 11V3C3 2.44772 3.44772 2 4 2H10" stroke="#00B8D4" strokeWidth="1.5"/>
                      </svg>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
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
