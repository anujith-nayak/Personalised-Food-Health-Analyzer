import { useRef, useState, useEffect, useCallback } from 'react'
import { Camera, RefreshCw, X, AlertTriangle, Upload } from 'lucide-react'

/**
 * CameraCapture — live webcam modal using MediaDevices API.
 *
 * Props:
 *   onCapture(file) — called with a File blob when user captures a photo
 *   onFallback()    — called when camera is unavailable / denied
 *   onClose()       — called when user cancels
 */
export default function CameraCapture({ onCapture, onFallback, onClose }) {
  const videoRef    = useRef(null)
  const canvasRef   = useRef(null)
  const streamRef   = useRef(null)

  const [phase,    setPhase]    = useState('starting') // starting | live | captured | error
  const [snapshot, setSnapshot] = useState(null)       // data URL for preview
  const [errMsg,   setErrMsg]   = useState('')
  const [facing,   setFacing]   = useState('environment') // rear camera first

  // ── Start stream ──────────────────────────────────────────────────────────
  const startCamera = useCallback(async (facingMode = 'environment') => {
    // Stop any existing stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    setPhase('starting')
    setSnapshot(null)

    if (!navigator.mediaDevices?.getUserMedia) {
      setErrMsg('Camera not supported in this browser.')
      setPhase('error')
      return
    }

    try {
      const constraints = {
        video: {
          facingMode,
          width:  { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setPhase('live')
    } catch (err) {
      console.error('Camera error:', err)
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrMsg('Camera permission denied. Please allow camera access in your browser settings.')
      } else if (err.name === 'NotFoundError') {
        setErrMsg('No camera found on this device.')
      } else {
        setErrMsg(`Camera error: ${err.message}`)
      }
      setPhase('error')
    }
  }, [])

  useEffect(() => {
    startCamera(facing)
    return () => {
      // Cleanup stream on unmount
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Flip camera (front / rear) ────────────────────────────────────────────
  const flipCamera = () => {
    const next = facing === 'environment' ? 'user' : 'environment'
    setFacing(next)
    startCamera(next)
  }

  // ── Capture frame ─────────────────────────────────────────────────────────
  const capture = () => {
    const video  = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    canvas.width  = video.videoWidth  || 1280
    canvas.height = video.videoHeight || 720
    canvas.getContext('2d').drawImage(video, 0, 0)

    const dataUrl = canvas.toDataURL('image/jpeg', 0.92)
    setSnapshot(dataUrl)
    setPhase('captured')

    // Stop the live stream to free camera
    streamRef.current?.getTracks().forEach((t) => t.stop())
  }

  // ── Retake ────────────────────────────────────────────────────────────────
  const retake = () => {
    setSnapshot(null)
    startCamera(facing)
  }

  // ── Use captured photo ────────────────────────────────────────────────────
  const useCaptured = () => {
    if (!snapshot) return
    // Convert data URL → Blob → File
    const arr  = snapshot.split(',')
    const mime = arr[0].match(/:(.*?);/)[1]
    const bstr = atob(arr[1])
    const u8   = new Uint8Array(bstr.length)
    for (let i = 0; i < bstr.length; i++) u8[i] = bstr.charCodeAt(i)
    const blob = new Blob([u8], { type: mime })
    const file = new File([blob], `capture-${Date.now()}.jpg`, { type: mime })
    onCapture(file)
  }

  // ── Close / cleanup ───────────────────────────────────────────────────────
  const handleClose = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
         onClick={handleClose}>
      <div
        className="bg-black w-full max-w-lg mx-2 rounded-2xl overflow-hidden shadow-2xl
                   flex flex-col"
        style={{ maxHeight: '95vh' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-gray-900">
          <p className="text-white font-semibold text-sm">
            {phase === 'captured' ? 'Preview — Use this photo?' : '📷 Camera'}
          </p>
          <div className="flex items-center gap-2">
            {phase === 'live' && (
              <button onClick={flipCamera}
                className="text-gray-300 hover:text-white p-1.5 rounded-lg hover:bg-gray-700"
                title="Flip camera">
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
            <button onClick={handleClose}
              className="text-gray-300 hover:text-white p-1.5 rounded-lg hover:bg-gray-700">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Video / Preview area */}
        <div className="relative bg-black flex-1 flex items-center justify-center"
             style={{ minHeight: 240 }}>

          {/* Starting spinner */}
          {phase === 'starting' && (
            <div className="flex flex-col items-center gap-3 text-gray-400">
              <div className="w-8 h-8 border-2 border-gray-600 border-t-white
                              rounded-full animate-spin" />
              <span className="text-sm">Starting camera…</span>
            </div>
          )}

          {/* Error state */}
          {phase === 'error' && (
            <div className="flex flex-col items-center gap-4 p-6 text-center">
              <AlertTriangle className="w-10 h-10 text-orange-400" />
              <p className="text-white text-sm">{errMsg}</p>
              <button onClick={onFallback}
                className="flex items-center gap-2 bg-white text-gray-900 font-semibold
                           px-5 py-2.5 rounded-xl text-sm hover:bg-gray-100 transition">
                <Upload className="w-4 h-4" /> Upload from Files Instead
              </button>
            </div>
          )}

          {/* Live video */}
          <video ref={videoRef}
            className={`w-full max-h-96 object-cover ${phase === 'live' ? 'block' : 'hidden'}`}
            playsInline muted autoPlay />

          {/* Snapshot preview */}
          {phase === 'captured' && snapshot && (
            <img src={snapshot} alt="Captured"
              className="w-full max-h-96 object-contain" />
          )}

          {/* Hidden canvas for capture */}
          <canvas ref={canvasRef} className="hidden" />
        </div>

        {/* Controls */}
        <div className="bg-gray-900 px-4 py-4 flex items-center justify-center gap-3">

          {phase === 'live' && (
            <>
              <button onClick={handleClose}
                className="flex-1 py-3 rounded-xl border border-gray-600 text-gray-300
                           hover:bg-gray-700 font-medium text-sm transition">
                Cancel
              </button>
              {/* Shutter button */}
              <button onClick={capture}
                className="w-16 h-16 rounded-full bg-white hover:bg-gray-200
                           flex items-center justify-center shadow-lg transition
                           flex-shrink-0">
                <div className="w-12 h-12 rounded-full border-4 border-gray-400 bg-white" />
              </button>
              <div className="flex-1" /> {/* spacer */}
            </>
          )}

          {phase === 'captured' && (
            <>
              <button onClick={retake}
                className="flex-1 py-3 rounded-xl border border-gray-600 text-gray-300
                           hover:bg-gray-700 font-medium text-sm transition flex items-center
                           justify-center gap-2">
                <RefreshCw className="w-4 h-4" /> Retake
              </button>
              <button onClick={useCaptured}
                className="flex-1 py-3 rounded-xl bg-primary-600 hover:bg-primary-700
                           text-white font-semibold text-sm transition flex items-center
                           justify-center gap-2">
                <Camera className="w-4 h-4" /> Use This Photo
              </button>
            </>
          )}

          {phase === 'error' && (
            <button onClick={handleClose}
              className="flex-1 py-3 rounded-xl border border-gray-600 text-gray-300
                         hover:bg-gray-700 font-medium text-sm transition">
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
