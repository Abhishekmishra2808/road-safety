import React, {useState, useEffect, useRef} from 'react'
import axios from 'axios'
import { BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import ResultsAnalytics from './ResultsAnalytics'

export default function App(){
  const [baseFile, setBaseFile] = useState(null)
  const [presentFile, setPresentFile] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [latestFrameUrl, setLatestFrameUrl] = useState(null)
  const [baseVideoMeta, setBaseVideoMeta] = useState(null)
  const [presentVideoMeta, setPresentVideoMeta] = useState(null)
  const [showFeatures, setShowFeatures] = useState(true)
  const pollingRef = useRef(null)
  const baseFileInputRef = useRef(null)
  const presentFileInputRef = useRef(null)

  const handleBaseFileChange = (e) => {
    const selectedFile = e.target.files[0]
    setBaseFile(selectedFile)
    if(selectedFile) {
      const video = document.createElement('video')
      video.preload = 'metadata'
      video.onloadedmetadata = () => {
        setBaseVideoMeta({
          duration: video.duration,
          width: video.videoWidth,
          height: video.videoHeight,
          size: selectedFile.size
        })
        window.URL.revokeObjectURL(video.src)
      }
      video.src = URL.createObjectURL(selectedFile)
      setShowFeatures(false)
    }
  }

  const handlePresentFileChange = (e) => {
    const selectedFile = e.target.files[0]
    setPresentFile(selectedFile)
    if(selectedFile) {
      const video = document.createElement('video')
      video.preload = 'metadata'
      video.onloadedmetadata = () => {
        setPresentVideoMeta({
          duration: video.duration,
          width: video.videoWidth,
          height: video.videoHeight,
          size: selectedFile.size
        })
        window.URL.revokeObjectURL(video.src)
      }
      video.src = URL.createObjectURL(selectedFile)
      setShowFeatures(false)
    }
  }

  const upload = async () =>{
    if(!baseFile || !presentFile) return alert('Please upload both base and present videos')
    const fd = new FormData()
    fd.append('base_video', baseFile)
    fd.append('present_video', presentFile)
    
    try {
      const res = await axios.post('http://localhost:8000/upload_comparison', fd, { headers: {'Content-Type':'multipart/form-data'} })
      setJobId(res.data.job_id)
      setStatus({progress: 0})
    } catch(err) {
      alert('Failed to upload. Make sure the API server is running on port 8000.')
      console.error(err)
    }
  }

  // Use WebSocket for live updates (status + frames)
  useEffect(()=>{
    if(!jobId) return
    const ws = new WebSocket(`ws://localhost:8000/ws/${jobId}`)
    ws.onopen = ()=> console.log('ws open')
    ws.onmessage = (ev)=>{
      try{
        const msg = JSON.parse(ev.data)
        if(msg.type === 'status'){
          setStatus(msg.status)
        }else if(msg.type === 'frame'){
          setLatestFrameUrl(`data:image/jpeg;base64,${msg.data}`)
        }else if(msg.type === 'error'){
          console.error(msg.message)
        }
      }catch(e){
        // sometimes binary or other messages
        // ignore
      }
    }
    ws.onclose = ()=> console.log('ws closed')
    ws.onerror = (e)=> console.error('ws error', e)
    pollingRef.current = ws
    return ()=>{ try{ pollingRef.current && pollingRef.current.close() }catch(e){} }
  }, [jobId])

  const formatFileSize = (bytes) => {
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDuration = (seconds) => {
    return seconds.toFixed(1) + 's'
  }

  return (
    <div className="page">
      {/* Hero Section */}
      <header className="hero">
        <div className="hero-content">
          <div className="brand-logo">
            <span className="brand-name">VISIONX</span>
          </div>
          <h1 className="hero-title">
            <span className="line">We detect</span>
            <span className="line highlight">road changes</span>
            <span className="line">through intelligent</span>
            <span className="line">comparison systems.</span>
          </h1>
          <p className="hero-subtitle">
            Advanced AI-powered road change detection platform. 
            Upload two videos (base and present) to identify and analyze changes in 
            traffic infrastructure, road conditions, damage, and safety elements over time.
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <div className="container">
          
          {/* Upload Section */}
          <section className="section">
            <h2 className="section-title">Upload Videos</h2>
            <p className="section-subtitle">Select base and present road surveillance videos to compare and detect changes.</p>
            
            {/* Base Video Upload */}
            <div className="upload-group">
              <h3 className="upload-group-title">Base Video (Reference)</h3>
              <div className="upload-area">
                <input 
                  ref={baseFileInputRef}
                  type="file" 
                  accept="video/*" 
                  onChange={handleBaseFileChange}
                  id="base-video-upload"
                  className="file-input"
                />
                <label htmlFor="base-video-upload" className="file-label">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                  <span className="file-label-text">{baseFile ? baseFile.name : 'Choose base video'}</span>
                  <span className="file-label-hint">The reference/baseline video for comparison</span>
                </label>
              </div>

              {baseVideoMeta && (
                <div className="video-meta-compact">
                  <span className="meta-item">{formatDuration(baseVideoMeta.duration)}</span>
                  <span className="meta-separator">•</span>
                  <span className="meta-item">{formatFileSize(baseVideoMeta.size)}</span>
                  <span className="meta-separator">•</span>
                  <span className="meta-item">{baseVideoMeta.width}×{baseVideoMeta.height}</span>
                </div>
              )}
            </div>

            <div className="divider" style={{margin: '2rem 0'}}/>

            {/* Present Video Upload */}
            <div className="upload-group">
              <h3 className="upload-group-title">Present Video (Current)</h3>
              <div className="upload-area">
                <input 
                  ref={presentFileInputRef}
                  type="file" 
                  accept="video/*" 
                  onChange={handlePresentFileChange}
                  id="present-video-upload"
                  className="file-input"
                />
                <label htmlFor="present-video-upload" className="file-label">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                  <span className="file-label-text">{presentFile ? presentFile.name : 'Choose present video'}</span>
                  <span className="file-label-hint">The current video to compare against base</span>
                </label>
              </div>

              {presentVideoMeta && (
                <div className="video-meta-compact">
                  <span className="meta-item">{formatDuration(presentVideoMeta.duration)}</span>
                  <span className="meta-separator">•</span>
                  <span className="meta-item">{formatFileSize(presentVideoMeta.size)}</span>
                  <span className="meta-separator">•</span>
                  <span className="meta-item">{presentVideoMeta.width}×{presentVideoMeta.height}</span>
                </div>
              )}
            </div>

            {baseFile && presentFile && (
              <>
                <div className="divider"/>
                <button onClick={upload} className="btn-primary" disabled={jobId}>
                  {jobId ? 'PROCESSING...' : 'START COMPARISON'}
                </button>
              </>
            )}
          </section>

          {/* Detection Results */}
          {jobId && (
            <>
              <div className="divider" style={{margin: '4rem 0'}}/>
              <section className="section">
                <h2 className="section-title">Real-Time Comparison</h2>
                
                <div className="detection-layout">
                  {/* Live Feed */}
                  <div className="detection-main">
                    <h3 className="subsection-title">Change Detection Feed</h3>
                    <div className="frame-container">
                      {latestFrameUrl ? (
                        <img src={latestFrameUrl} alt="Detection frame" className="frame-image" />
                      ) : (
                        <div className="frame-placeholder">
                          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
                            <line x1="7" y1="2" x2="7" y2="22"/>
                            <line x1="17" y1="2" x2="17" y2="22"/>
                            <line x1="2" y1="12" x2="22" y2="12"/>
                            <line x1="2" y1="7" x2="7" y2="7"/>
                            <line x1="2" y1="17" x2="7" y2="17"/>
                            <line x1="17" y1="17" x2="22" y2="17"/>
                            <line x1="17" y1="7" x2="22" y2="7"/>
                          </svg>
                          <p>Waiting for comparison frames...</p>
                        </div>
                      )}
                    </div>
                    
                    {/* Progress Bar */}
                    {status && (
                      <div className="progress-container">
                        <div className="progress-bar">
                          <div className="progress-fill" style={{width: `${(status.progress || 0) * 100}%`}}/>
                        </div>
                        <p className="progress-text">
                          Processing frame {status.processed_frames || 0} of {status.total_frames || '—'} | {((status.progress || 0) * 100).toFixed(0)}% complete
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Statistics Sidebar */}
                  <div className="detection-sidebar">
                    <h3 className="subsection-title">Changes Detected</h3>
                    <div className="stats-card">
                      {status && status.changes && Object.keys(status.changes).length > 0 ? (
                        <div className="badges-container">
                          {Object.entries(status.changes)
                            .sort((a, b) => b[1] - a[1])
                            .map(([key, value]) => (
                              <div key={key} className="badge">
                                <span className="badge-label">{key.replace('_', ' ')}</span>
                                <span className="badge-value">{value}</span>
                              </div>
                            ))}
                        </div>
                      ) : (
                        <p className="stats-empty">No changes detected yet</p>
                      )}
                    </div>

                    {status && status.completed && (
                      <div className="completion-card">
                        <h4>✓ Comparison Complete</h4>
                        <a href={`http://localhost:8000/results/${jobId}`} target="_blank" rel="noreferrer" className="btn-secondary">
                          DOWNLOAD RESULTS
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </section>

              {/* Comprehensive Analytics Section */}
              <ResultsAnalytics status={status} />
            </>
          )}

          {/* Features Section */}
          {showFeatures && (
            <>
              <div className="divider" style={{margin: '4rem 0'}}/>
              
              <section className="section">
                <div className="info-card">
                  <h3 className="info-title">How It Works</h3>
                  <ol className="info-list">
                    <li><strong>Upload Base Video</strong> — Select your reference/baseline road footage</li>
                    <li><strong>Upload Present Video</strong> — Select the current road footage to compare</li>
                    <li><strong>Start Comparison</strong> — Initiate the AI-powered change detection</li>
                    <li><strong>Monitor Progress</strong> — Watch real-time comparison results</li>
                    <li><strong>Analyze Changes</strong> — Review detected differences and changes</li>
                  </ol>
                </div>
              </section>

              <section className="section" style={{marginTop: '3rem'}}>
                <h2 className="section-title">Change Detection Capabilities</h2>
                <div className="capabilities-grid">
                  <div className="capability-card">
                    <h4>New Infrastructure</h4>
                    <p>Detects newly added traffic signs, signals, and road furniture</p>
                  </div>
                  <div className="capability-card">
                    <h4>Removed Elements</h4>
                    <p>Identifies missing or removed road infrastructure and markings</p>
                  </div>
                  <div className="capability-card">
                    <h4>Road Damage</h4>
                    <p>Spots new potholes, cracks, and surface deterioration</p>
                  </div>
                  <div className="capability-card">
                    <h4>Marking Changes</h4>
                    <p>Detects faded, repainted, or modified lane markings</p>
                  </div>
                  <div className="capability-card">
                    <h4>Structural Changes</h4>
                    <p>Identifies modifications to road layout and geometry</p>
                  </div>
                  <div className="capability-card">
                    <h4>Safety Elements</h4>
                    <p>Tracks changes in barriers, bollards, and safety equipment</p>
                  </div>
                </div>
              </section>

              <section className="section" style={{marginTop: '3rem'}}>
                <div className="info-card">
                  <h3 className="info-title">System Performance</h3>
                  <ul className="info-list">
                    <li><strong>Processing Speed</strong> — Efficient frame-by-frame comparison</li>
                    <li><strong>Hardware Acceleration</strong> — Automatic GPU utilization when available</li>
                    <li><strong>Change Detection Accuracy</strong> — Advanced computer vision algorithms</li>
                    <li><strong>Multi-Format Support</strong> — Compatible with MP4, AVI, MOV, MKV formats</li>
                  </ul>
                </div>
              </section>
            </>
          )}

        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <p>© 2025 Road Safety Detection Platform. Advanced AI-powered road monitoring system.</p>
        </div>
      </footer>
    </div>
  )
}
