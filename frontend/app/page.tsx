'use client';

import Image from 'next/image';
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';

interface UploadedFile {
  id: string;
  original_name: string;
  stored_name: string;
  size: number;
  url: string;
  type: string;
}

export default function Page() {
  const router = useRouter();
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i)) + ' ' + sizes[i];
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    await uploadFile(file);
  };

  const uploadFile = async (file: File) => {
    console.log('Uploading file:', file.name);
    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 100);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await response.json();
      console.log('Upload successful:', data);
      setUploadProgress(100);
      
      setTimeout(() => {
        setUploadedFile(data.file);
        console.log('File state set:', data.file);
        setIsUploading(false);
        setUploadProgress(0);
      }, 500);
    } catch (error) {
      console.error('Upload error:', error);
      alert(error instanceof Error ? error.message : 'Failed to upload file');
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      await uploadFile(file);
    }
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!scrollContainerRef.current) return;
    setIsDragging(true);
    setStartX(e.pageX - scrollContainerRef.current.offsetLeft);
    setScrollLeft(scrollContainerRef.current.scrollLeft);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !scrollContainerRef.current) return;
    e.preventDefault();
    const x = e.pageX - scrollContainerRef.current.offsetLeft;
    const walk = (x - startX) * 2; // Scroll speed multiplier
    scrollContainerRef.current.scrollLeft = scrollLeft - walk;
  };

  const handleConfigure = () => {
    console.log('Process clicked, uploadedFile:', uploadedFile);
    if (uploadedFile) {
      const url = `/analysis?file=${encodeURIComponent(uploadedFile.url)}&name=${encodeURIComponent(uploadedFile.original_name)}`;
      console.log('Navigating to:', url);
      router.push(url);
    } else {
      alert('Please upload a file first');
    }
  };

  return (
    <main className="page">
      <div className="card">
        <section className="left">
          <div style={{width: '430px', overflow: 'visible'}}>
            <Image src="/title.svg" alt="P&ID Digitization" width={430} height={64} style={{display: 'block', transform: 'scale(2.5)', transformOrigin: 'left top', marginBottom: '100px', marginLeft: '-300px'}} />
          </div>
          <Image src="/text.svg" alt="Description" width={430} height={60} style={{display: 'block'}} />
          <div className="actions">
              <svg width="150" height="34" viewBox="0 0 150 34" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="0.5" y="1" width="149" height="32" rx="16" fill="#EBFFF6"/>
                <rect x="0.5" y="1" width="149" height="32" rx="16" stroke="#A3FAD8" strokeWidth="0.5"/>
                <circle cx="11.5" cy="17" r="3" fill="#008A6A"/>
                <path d="M19.592 22V13.54H21.692L25.376 19.996L25.364 13.54H26.852V22H24.956L21.08 15.196V22H19.592ZM31.4041 22.18C29.4481 22.18 28.3441 20.908 28.3441 19.024C28.3441 17.128 29.5081 15.844 31.3921 15.844C33.4081 15.844 34.5361 17.296 34.3921 19.336H29.7721C29.8081 20.452 30.3841 21.112 31.3801 21.112C32.2441 21.112 32.6521 20.668 32.8681 20.128H34.2961C34.0921 21.004 33.2761 22.18 31.4041 22.18ZM29.8081 18.4H32.9281C32.8801 17.368 32.1961 16.888 31.3921 16.888C30.4921 16.888 29.9161 17.404 29.8081 18.4ZM38.698 22.18C36.802 22.18 35.422 20.896 35.422 19C35.422 17.128 36.802 15.844 38.698 15.844C40.606 15.844 41.974 17.128 41.974 19C41.974 20.896 40.606 22.18 38.698 22.18ZM36.898 19C36.898 20.2 37.606 21.04 38.698 21.04C39.802 21.04 40.498 20.188 40.498 19C40.498 17.812 39.814 16.984 38.71 16.984C37.594 16.984 36.898 17.788 36.898 19ZM42.9083 19.06L46.4723 13.54H48.4523V18.88H49.5203V20.02H48.4523V22H47.0483V20.02H42.9083V19.06ZM44.3843 18.88H47.0483V14.788L44.3843 18.88ZM50.0834 24.04V22.912H50.2994C50.6714 22.912 50.9234 22.708 50.9234 22.192V16.024H52.3634V22.012C52.3634 23.44 51.7154 24.04 50.6234 24.04H50.0834ZM50.7434 14.104C50.7434 13.648 51.0674 13.264 51.6194 13.264C52.1714 13.264 52.5074 13.648 52.5074 14.104C52.5074 14.56 52.1714 14.968 51.6194 14.968C51.0674 14.968 50.7434 14.56 50.7434 14.104ZM61.0355 22.18C58.4795 22.18 56.7755 20.368 56.7755 17.764C56.7755 15.244 58.4435 13.36 61.0475 13.36C63.7235 13.36 64.9835 15.124 65.1875 16.756H63.6035C63.3755 15.688 62.6555 14.668 61.0235 14.668C59.5115 14.668 58.3715 15.772 58.3715 17.764C58.3715 19.744 59.5115 20.86 61.0235 20.86C62.6555 20.86 63.3995 19.852 63.6155 18.76H65.2115C65.0315 20.392 63.7475 22.18 61.0355 22.18ZM69.4714 22.18C67.5754 22.18 66.1954 20.896 66.1954 19C66.1954 17.128 67.5754 15.844 69.4714 15.844C71.3794 15.844 72.7474 17.128 72.7474 19C72.7474 20.896 71.3794 22.18 69.4714 22.18ZM67.6714 19C67.6714 20.2 68.3794 21.04 69.4714 21.04C70.5754 21.04 71.2714 20.188 71.2714 19C71.2714 17.812 70.5874 16.984 69.4834 16.984C68.3674 16.984 67.6714 17.788 67.6714 19ZM74.1617 22V16.024H75.5657V16.816C75.7817 16.456 76.4057 15.844 77.4617 15.844C78.7457 15.844 79.7057 16.624 79.7057 18.16V22H78.2657V18.352C78.2657 17.368 77.7857 17.008 77.0297 17.008C76.0097 17.008 75.6137 17.8 75.6137 18.868V22H74.1617ZM81.4391 22V16.024H82.8431V16.816C83.0591 16.456 83.6831 15.844 84.7391 15.844C86.0231 15.844 86.9831 16.624 86.9831 18.16V22H85.5431V18.352C85.5431 17.368 85.0631 17.008 84.3071 17.008C83.2871 17.008 82.8911 17.8 82.8911 18.868V22H81.4391ZM91.3924 22.18C89.4364 22.18 88.3324 20.908 88.3324 19.024C88.3324 17.128 89.4964 15.844 91.3804 15.844C93.3964 15.844 94.5244 17.296 94.3804 19.336H89.7604C89.7964 20.452 90.3724 21.112 91.3684 21.112C92.2324 21.112 92.6404 20.668 92.8564 20.128H94.2844C94.0804 21.004 93.2644 22.18 91.3924 22.18ZM89.7964 18.4H92.9164C92.8684 17.368 92.1844 16.888 91.3804 16.888C90.4804 16.888 89.9044 17.404 89.7964 18.4ZM98.5903 22.18C96.6943 22.18 95.4223 20.836 95.4223 19.036C95.4223 17.164 96.7663 15.844 98.5903 15.844C100.582 15.844 101.566 17.068 101.686 18.256H100.234C100.066 17.452 99.5623 16.984 98.6023 16.984C97.5823 16.984 96.8983 17.74 96.8983 19.024C96.8983 20.272 97.6063 21.04 98.6023 21.04C99.5863 21.04 100.102 20.476 100.246 19.708H101.686C101.602 20.788 100.678 22.18 98.5903 22.18ZM105.185 22C104.033 22 103.397 21.328 103.397 20.104V17.068H102.377V16.024H103.397V14.512H104.837V16.024H106.181V17.068H104.837V20.08C104.837 20.656 105.113 20.836 105.617 20.836H106.181V22H105.185ZM110.131 22.18C108.175 22.18 107.071 20.908 107.071 19.024C107.071 17.128 108.235 15.844 110.119 15.844C112.135 15.844 113.263 17.296 113.119 19.336H108.499C108.535 20.452 109.111 21.112 110.107 21.112C110.971 21.112 111.379 20.668 111.595 20.128H113.023C112.819 21.004 112.003 22.18 110.131 22.18ZM108.535 18.4H111.655C111.607 17.368 110.923 16.888 110.119 16.888C109.219 16.888 108.643 17.404 108.535 18.4ZM117.065 22.18C115.325 22.18 114.161 20.896 114.161 19C114.161 17.176 115.313 15.868 117.065 15.868C118.157 15.868 118.805 16.36 119.117 16.756V13.54H120.569V22H119.165V21.172C118.985 21.436 118.313 22.18 117.065 22.18ZM115.637 19.012C115.625 20.248 116.333 21.04 117.413 21.04C118.469 21.04 119.213 20.26 119.213 19.012C119.213 17.776 118.469 16.996 117.413 16.996C116.333 16.996 115.637 17.776 115.637 19.012Z" fill="#008A6A"/>
                <path d="M139.667 17C139.667 13.5942 136.906 10.8333 133.5 10.8333C130.094 10.8333 127.333 13.5942 127.333 17C127.333 20.4057 130.094 23.1666 133.5 23.1666C136.906 23.1666 139.667 20.4057 139.667 17ZM135.146 15.3131C135.342 15.1179 135.658 15.1179 135.854 15.3131C136.049 15.5084 136.049 15.8249 135.854 16.0202L133.187 18.6868C132.992 18.8821 132.675 18.8821 132.48 18.6868L131.146 17.3535C130.951 17.1582 130.951 16.8417 131.146 16.6465C131.342 16.4512 131.658 16.4512 131.854 16.6465L132.833 17.6263L135.146 15.3131ZM140.667 17C140.667 20.958 137.458 24.1666 133.5 24.1666C129.542 24.1666 126.333 20.958 126.333 17C126.333 13.0419 129.542 9.83331 133.5 9.83331C137.458 9.83331 140.667 13.0419 140.667 17Z" fill="#008A6A"/>
              </svg>
              <button onClick={handleConfigure} style={{background: 'none', border: 'none', padding: 0, cursor: uploadedFile ? 'pointer' : 'not-allowed', opacity: uploadedFile ? 1 : 0.5}}>
                <svg width="105" height="32" viewBox="0 0 105 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="0.5" y="0.5" width="104" height="31" rx="15.5" fill="#00879F"/>
                  <rect x="0.5" y="0.5" width="104" height="31" rx="15.5" stroke="#00879F"/>
                  <path d="M16 10L22 16L16 22M22 16H10" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <text x="36" y="20.5" fill="white" fontSize="14" fontWeight="500" fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif">Process</text>
                </svg>
              </button>
            </div>
          <div className="humain-branding">
            <span style={{color: '#666', fontSize: '12px', marginRight: '8px'}}>Powered by</span>
            <Image src="/humain_logo.png" alt="HUMAIN" width={120} height={30} style={{objectFit: 'contain'}} />
          </div>
        </section>
        <section className="right">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.dwg,.dgn,.jpg,.jpeg,.png,.zip,.svg,.xml"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          
          {!uploadedFile && !isUploading && (
            <>
              <div 
                className="uploader"
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{ cursor: 'pointer' }}
              >
                <div className="uploader-content">
                  <div className="uploader-header">
                    <div className="icon">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 15V3M12 3L8 7M12 3L16 7M3 15V18C3 19.6569 4.34315 21 6 21H18C19.6569 21 21 19.6569 21 18V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                    <div className="title">Upload Your Diagram</div>
                  </div>
                  <div className="sub">
                    Drag & drop or <a onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>choose file</a> to upload
                  </div>
                </div>
              </div>
              <div className="or-section">
                <div className="or">
                  <span className="or-text">OR FROM</span>
                </div>
                <div className="providers">
                  <Image src="/one_drive.svg" alt="OneDrive" width={295} height={65} />
                  <Image src="/google_drive.svg" alt="Google Drive" width={295} height={65} />
                </div>
              </div>
              <div className="urlinput">
                <span className="linkicon">🔗</span>
                <input placeholder="Paste source URL" />
              </div>
            </>
          )}

          {isUploading && (
            <div className="uploaded-preview">
              <div className="uploaded-header">
                <div className="uploaded-info">
                  <div className="file-icon">📄</div>
                  <div className="file-details">
                    <div className="file-name">Uploading...</div>
                    <div className="file-meta">
                      <span className="uploading-spinner">⏳</span>
                      <span>Uploading</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="upload-progress">
                <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }}></div>
              </div>
            </div>
          )}

          {uploadedFile && (
            <>
              <div className="uploaded-preview">
                <div className="uploaded-header">
                  <div className="uploaded-info">
                    <div className="file-icon">📄</div>
                    <div className="file-details">
                      <div className="file-name">{uploadedFile.original_name}</div>
                      <div className="file-meta">
                        <span>{formatFileSize(uploadedFile.size)}</span>
                        <span>•</span>
                        <span style={{ color: '#008A6A' }}>✓</span>
                        <span>Uploaded</span>
                      </div>
                    </div>
                  </div>
                  <button className="close-btn" onClick={handleRemoveFile}>×</button>
                </div>
                <div 
                  className="diagram-preview"
                  ref={scrollContainerRef}
                  onMouseDown={handleMouseDown}
                  onMouseLeave={handleMouseLeave}
                  onMouseUp={handleMouseUp}
                  onMouseMove={handleMouseMove}
                >
                  <button className="expand-btn" onClick={() => setIsFullscreen(true)}>⛶</button>
                  <Image 
                    src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}${uploadedFile.url}`}
                    alt={uploadedFile.original_name}
                    fill
                    style={{ objectFit: 'cover' }}
                    unoptimized
                    draggable={false}
                  />
                </div>
              </div>

              {isFullscreen && (
                <div className="fullscreen-modal" onClick={() => setIsFullscreen(false)}>
                  <div className="fullscreen-header">
                    <div className="fullscreen-title">{uploadedFile.original_name}</div>
                    <button className="fullscreen-close" onClick={() => setIsFullscreen(false)}>×</button>
                  </div>
                  <div className="fullscreen-content" onClick={(e) => e.stopPropagation()}>
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}${uploadedFile.url}`}
                      alt={uploadedFile.original_name}
                      className="fullscreen-image"
                    />
                  </div>
                </div>
              )}
            </>
          )}
          
          <div className="filetypes-section">
            <div className="filetypes-label">Supported file types:</div>
            <div className="filetypes">
              <span className="badge">.pdf</span>
              <span className="badge">.dwg</span>
              <span className="badge">.dgn</span>
              <span className="badge">.jpg</span>
              <span className="badge">.png</span>
              <span className="badge">.zip</span>
              <span className="badge">.svg</span>
              <span className="badge">.xml</span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
