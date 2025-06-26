// pages/index.tsx
'use client'
import { useState, useCallback } from 'react'
import Head from 'next/head'
import { useDropzone, FileRejection } from 'react-dropzone'

interface OriginalImage {
  file: File
  preview: string
}

interface ProcessingState {
  isProcessing: boolean
  error: string | null
  processedImage: string | null
  processedImageDimensions: { width: number; height: number } | null
}

interface CheckState {
  isChecking: boolean
  error: string | null
  results: {
    background_check: boolean
    dimension_check: boolean
    alignment_check: boolean
    target_dimensions?: { width: number; height: number }
  } | null
}

interface FixOptions {
  fix_dimensions: boolean
  fix_background: boolean
  fix_alignment: boolean
}

interface DimensionSettings {
  width: number
  height: number
}

const Home: React.FC = () => {
  const [originalImage, setOriginalImage] = useState<OriginalImage | null>(null)
  const [originalDimensions, setOriginalDimensions] = useState<{ width: number; height: number } | null>(null)
  const [dimensions, setDimensions] = useState<DimensionSettings>({
    width: 1200,
    height: 1200
  })
  const [state, setState] = useState<ProcessingState>({
    isProcessing: false,
    error: null,
    processedImage: null,
    processedImageDimensions: null
  })
  const [checkState, setCheckState] = useState<CheckState>({
    isChecking: false,
    error: null,
    results: null
  })
  const [fixOptions, setFixOptions] = useState<FixOptions>({
    fix_dimensions: true,
    fix_background: true,
    fix_alignment: true
  })

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
    if (rejectedFiles.length > 0) {
      setState(prev => ({
        ...prev,
        error: 'Please upload a valid image file'
      }))
      return
    }

    const file = acceptedFiles[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = () => {
        const img = new Image()
        img.onload = () => {
          setOriginalImage({
            file,
            preview: reader.result as string
          })
          setOriginalDimensions({
            width: img.width,
            height: img.height
          })
          // Set dimensions to 1200x1200 by default
          setDimensions({
            width: 1200,
            height: 1200
          })
          setState({
            isProcessing: false,
            error: null,
            processedImage: null,
            processedImageDimensions: null
          })
          // Reset check state when new image is uploaded
          setCheckState({
            isChecking: false,
            error: null,
            results: null
          })
          // Reset fix options
          setFixOptions({
            fix_dimensions: true,
            fix_background: true,
            fix_alignment: true
          })
        }
        img.src = reader.result as string
      }
      reader.readAsDataURL(file)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.webp', '.bmp']
    },
    multiple: false,
    maxSize: 50 * 1024 * 1024
  })

  const handleDimensionChange = (field: 'width' | 'height', value: number) => {
    if (originalDimensions) {
      const aspectRatio = originalDimensions.width / originalDimensions.height
      
      if (field === 'width') {
        setDimensions({
          width: value,
          height: Math.round(value / aspectRatio)
        })
      } else {
        setDimensions({
          width: Math.round(value * aspectRatio),
          height: value
        })
      }
    } else {
      setDimensions(prev => ({
        ...prev,
        [field]: value
      }))
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDimensions = (width: number, height: number): string => {
    return `${width} × ${height}`
  }

  // UPDATED: Check Image Function with configurable dimensions
  const checkImage = async (): Promise<void> => {
    if (!originalImage) return

    setCheckState(prev => ({
      ...prev,
      isChecking: true,
      error: null
    }))

    try {
      const formData = new FormData()
      formData.append('file', originalImage.file)
      formData.append('target_width', dimensions.width.toString())
      formData.append('target_height', dimensions.height.toString())

      const response = await fetch('http://localhost:8000/check_image/', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Check failed: ${response.status} - ${errorText}`)
      }

      const results = await response.json()
      
      setCheckState(prev => ({
        ...prev,
        isChecking: false,
        results: results
      }))

      // Auto-select fixes for failed checks, keep successful ones unchecked
      setFixOptions({
        fix_dimensions: !results.dimension_check,  // Only fix if check failed
        fix_background: !results.background_check, // Only fix if check failed
        fix_alignment: !results.alignment_check    // Only fix if check failed
      })
    } catch (err) {
      setCheckState(prev => ({
        ...prev,
        isChecking: false,
        error: err instanceof Error ? err.message : 'Check failed'
      }))
    }
  }

  // UPDATED: Process Image Function with configurable dimensions
  const processImage = async (): Promise<void> => {
    if (!originalImage) return

    setState(prev => ({
      ...prev,
      isProcessing: true,
      error: null
    }))

    try {
      const formData = new FormData()
      formData.append('file', originalImage.file)
      formData.append('fix_dimensions', fixOptions.fix_dimensions.toString())
      formData.append('fix_background', fixOptions.fix_background.toString())
      formData.append('fix_alignment', fixOptions.fix_alignment.toString())
      formData.append('target_width', dimensions.width.toString())
      formData.append('target_height', dimensions.height.toString())

      const response = await fetch('http://localhost:8000/process-image/', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Processing failed: ${response.status} - ${errorText}`)
      }

      const blob = await response.blob()
      const processedUrl = URL.createObjectURL(blob)
      
      // Get processed image dimensions
      const img = new Image()
      img.onload = () => {
        setState(prev => ({
          ...prev,
          isProcessing: false,
          processedImage: processedUrl,
          processedImageDimensions: {
            width: img.width,
            height: img.height
          }
        }))
      }
      img.onerror = () => {
        setState(prev => ({
          ...prev,
          isProcessing: false,
          error: 'Failed to load processed image'
        }))
      }
      img.src = processedUrl
    } catch (err) {
      setState(prev => ({
        ...prev,
        isProcessing: false,
        error: err instanceof Error ? err.message : 'Processing failed'
      }))
    }
  }

  const downloadImage = (): void => {
    if (state.processedImage && originalImage) {
      const link = document.createElement('a')
      link.href = state.processedImage
      link.download = `processed_${originalImage.file.name.replace(/\.[^/.]+$/, '')}_${dimensions.width}x${dimensions.height}.jpg`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  }

  const reset = (): void => {
    setOriginalImage(null)
    setOriginalDimensions(null)
    setDimensions({
      width: 1200,
      height: 1200
    })
    setState({
      isProcessing: false,
      error: null,
      processedImage: null,
      processedImageDimensions: null
    })
    setCheckState({
      isChecking: false,
      error: null,
      results: null
    })
    setFixOptions({
      fix_dimensions: true,
      fix_background: true,
      fix_alignment: true
    })
    
    if (state.processedImage) {
      URL.revokeObjectURL(state.processedImage)
    }
  }

  // UPDATED: Check Results Component with dynamic dimensions display
  const CheckResults = () => {
    if (!checkState.results && !checkState.error && !checkState.isChecking) return null

    const getCheckIcon = (passed: boolean) => (
      <div className={`w-5 h-5 rounded-full flex items-center justify-center ${
        passed ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
      }`}>
        {passed ? '✓' : '✗'}
      </div>
    )

    const getOverallStatus = () => {
      if (!checkState.results) return null
      const { background_check, dimension_check, alignment_check } = checkState.results
      const allPassed = background_check && dimension_check && alignment_check
      return allPassed
    }

    const getDimensionLabel = () => {
      if (checkState.results?.target_dimensions) {
        const { width, height } = checkState.results.target_dimensions
        return `Dimensions (${width}×${height})`
      }
      return `Dimensions (${dimensions.width}×${dimensions.height})`
    }

    return (
      <div className="mt-6 p-4 border border-gray-200 rounded-lg bg-gray-50">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-light">Image Quality Checks</h3>
          {checkState.results && (
            <div className={`px-3 py-1 rounded-full text-xs font-medium ${
              getOverallStatus() 
                ? 'bg-green-100 text-green-700' 
                : 'bg-yellow-100 text-yellow-700'
            }`}>
              {getOverallStatus() ? 'All Checks Passed' : 'Needs Processing'}
            </div>
          )}
        </div>

        {checkState.isChecking && (
          <div className="text-center py-4">
            <div className="flex justify-center space-x-1 mb-2">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
            <p className="text-gray-600 text-sm">Running quality checks...</p>
          </div>
        )}

        {checkState.error && (
          <div className="text-center py-4">
            <div className="text-red-600 text-2xl mb-2">⚠</div>
            <p className="text-red-600 text-sm">{checkState.error}</p>
          </div>
        )}

        {checkState.results && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getCheckIcon(checkState.results.background_check)}
                <span className="text-sm">Background Quality</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">
                  {checkState.results.background_check ? 'Clean background' : 'Needs background removal'}
                </span>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={fixOptions.fix_background}
                    onChange={(e) => setFixOptions(prev => ({ ...prev, fix_background: e.target.checked }))}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-xs text-gray-600">Fix</span>
                </label>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getCheckIcon(checkState.results.dimension_check)}
                <span className="text-sm">{getDimensionLabel()}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">
                  {checkState.results.dimension_check ? 'Correct size' : 'Needs resizing'}
                </span>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={fixOptions.fix_dimensions}
                    onChange={(e) => setFixOptions(prev => ({ ...prev, fix_dimensions: e.target.checked }))}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-xs text-gray-600">Fix</span>
                </label>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getCheckIcon(checkState.results.alignment_check)}
                <span className="text-sm">Product Alignment</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500">
                  {checkState.results.alignment_check ? 'Well aligned' : 'Needs rearrangement'}
                </span>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={fixOptions.fix_alignment}
                    onChange={(e) => setFixOptions(prev => ({ ...prev, fix_alignment: e.target.checked }))}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-xs text-gray-600">Fix</span>
                </label>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-200">
              <div className="flex gap-2">
                <button
                  onClick={() => setFixOptions({ fix_dimensions: true, fix_background: true, fix_alignment: true })}
                  className="text-xs text-blue-600 hover:text-blue-800 underline"
                >
                  Select All
                </button>
                <button
                  onClick={() => setFixOptions({ fix_dimensions: false, fix_background: false, fix_alignment: false })}
                  className="text-xs text-gray-500 hover:text-gray-700 underline"
                >
                  None
                </button>
                <button
                  onClick={() => setFixOptions({
                    fix_dimensions: !checkState.results!.dimension_check,
                    fix_background: !checkState.results!.background_check,
                    fix_alignment: !checkState.results!.alignment_check
                  })}
                  className="text-xs text-orange-600 hover:text-orange-800 underline"
                >
                  Only Failed
                </button>
              </div>
              <div className="text-xs text-gray-500">
                {Object.values(fixOptions).filter(Boolean).length} selected
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }



  return (
    <>
      <Head>
        <title>AI Image Processor</title>
        <meta name="description" content="AI-powered image processing" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-white text-black">
        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Header */}
          <header className="text-center mb-8">
            <div className="inline-flex items-center gap-3 mb-3">
              <div className="w-6 h-6 bg-black rounded-full flex items-center justify-center">
                <div className="w-3 h-3 bg-white rounded-full animate-pulse"></div>
              </div>
              <h1 className="text-2xl font-light tracking-wide">Image Processor</h1>
            </div>
            <p className="text-gray-500 text-sm font-light">
              Transform your images with locked aspect ratio
            </p>
          </header>

          {/* Main Content */}
          <main>
            {!originalImage ? (
              /* Upload Area */
              <section
                {...getRootProps()}
                className={`relative border-2 border-dashed rounded-none p-16 text-center cursor-pointer transition-all duration-300 mx-auto max-w-xl
                  ${isDragActive 
                    ? 'border-black bg-gray-50' 
                    : 'border-gray-300 hover:border-gray-400'
                  }`}
              >
                <input {...getInputProps()} />
                <div className="space-y-6">
                  <div className="w-12 h-12 mx-auto border-2 border-black rounded-full flex items-center justify-center">
                    <div className="text-xl">+</div>
                  </div>
                  {isDragActive ? (
                    <p className="text-lg font-light">Drop your image here</p>
                  ) : (
                    <>
                      <p className="text-lg font-light">
                        Drop an image or click to select
                      </p>
                      <p className="text-xs text-gray-400 uppercase tracking-wider">
                        JPG • PNG • WebP • Max 50MB
                      </p>
                    </>
                  )}
                  {state.error && (
                    <div className="mt-6 p-4 border border-red-300 bg-red-50">
                      <p className="text-red-600 text-sm">{state.error}</p>
                    </div>
                  )}
                </div>
              </section>
            ) : (
              <>
                {/* UPDATED: Simplified Dimension Controls */}
                <section className="mb-6 mt-6">
                  <div className="flex justify-center">
                    <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
                      <div className="text-sm text-gray-600">Target Size</div>
                      <input
                        type="number"
                        min="1"
                        max="5000"
                        value={dimensions.width}
                        onChange={(e) => handleDimensionChange('width', parseInt(e.target.value) || 1)}
                        className="w-20 px-2 py-1 text-center border border-gray-300 rounded focus:border-blue-500 focus:outline-none text-sm"
                        placeholder="1200"
                      />
                      <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M7 17L17 7M17 7H7M17 7V17" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </div>
                      <input
                        type="number"
                        min="1"
                        max="5000"
                        value={dimensions.height}
                        onChange={(e) => handleDimensionChange('height', parseInt(e.target.value) || 1)}
                        className="w-20 px-2 py-1 text-center border border-gray-300 rounded focus:border-blue-500 focus:outline-none text-sm"
                        placeholder="1200"
                      />
                      <div className="flex items-center gap-2 ml-2 text-xs text-gray-500">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M12 1L12 23M1 12L23 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                        </svg>
                        Locked Ratio
                      </div>
                    </div>
                  </div>
                </section>

                {/* Check Results Section */}
                <CheckResults />

                {/* Horizontal Layout with Boundary */}
                <section className="relative">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start relative">
                    {/* Vertical Boundary Line */}
                    <div className="hidden lg:block absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-gray-200 via-gray-400 to-gray-200 transform -translate-x-1/2 z-10">
                      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-6 h-6 bg-white border-2 border-gray-400 rounded-full flex items-center justify-center">
                        <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                      </div>
                    </div>

                    {/* Original Image */}
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h2 className="text-lg font-light">Original</h2>
                        {originalDimensions && (
                          <div className="px-3 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-full">
                            {formatDimensions(originalDimensions.width, originalDimensions.height)}
                          </div>
                        )}
                      </div>
                      <div className="relative border border-gray-300 bg-gray-100 overflow-hidden" style={{
                        backgroundImage: `url("data:image/svg+xml,%3csvg width='20' height='20' xmlns='http://www.w3.org/2000/svg'%3e%3cdefs%3e%3cpattern id='a' patternUnits='userSpaceOnUse' width='20' height='20'%3e%3crect fill='%23f9fafb' width='10' height='10'/%3e%3crect fill='%23f3f4f6' x='10' y='10' width='10' height='10'/%3e%3c/pattern%3e%3c/defs%3e%3crect width='100%25' height='100%25' fill='url(%23a)'/%3e%3c/svg%3e")`,
                        backgroundSize: '20px 20px'
                      }}>
                        <img
                          src={originalImage.preview}
                          alt="Original"
                          className="w-full h-auto max-h-80 object-contain relative z-10"
                        />
                        
                        {/* Simple Glass Loading Overlay */}
                        {state.isProcessing && (
                          <div className="absolute inset-0 backdrop-blur-sm bg-white/30 flex items-center justify-center">
                            <div className="bg-white/80 backdrop-blur-md rounded-lg px-6 py-4 border border-gray-200/50 shadow-lg">
                              <div className="text-center">
                                <div className="flex justify-center space-x-1 mb-2">
                                  <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"></div>
                                  <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                  <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                </div>
                                <p className="text-gray-700 text-sm font-light">Processing...</p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                      
                      {/* File Info */}
                      <div className="text-xs text-gray-400 text-center">
                        {originalImage.file.name} • {formatFileSize(originalImage.file.size)}
                      </div>
                    </div>

                    {/* Processed Result */}
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h2 className="text-lg font-light">Processed</h2>
                        {state.processedImageDimensions && (
                          <div className="px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                            {formatDimensions(state.processedImageDimensions.width, state.processedImageDimensions.height)}
                          </div>
                        )}
                      </div>
                      <div className="border border-gray-300 bg-gray-100 min-h-80 flex items-center justify-center overflow-hidden" style={{
                        backgroundImage: `url("data:image/svg+xml,%3csvg width='20' height='20' xmlns='http://www.w3.org/2000/svg'%3e%3cdefs%3e%3cpattern id='a' patternUnits='userSpaceOnUse' width='20' height='20'%3e%3crect fill='%23f9fafb' width='10' height='10'/%3e%3crect fill='%23f3f4f6' x='10' y='10' width='10' height='10'/%3e%3c/pattern%3e%3c/defs%3e%3crect width='100%25' height='100%25' fill='url(%23a)'/%3e%3c/svg%3e")`,
                        backgroundSize: '20px 20px'
                      }}>
                        {state.processedImage ? (
                          <img
                            src={state.processedImage}
                            alt="Processed"
                            className="w-full h-auto max-h-80 object-contain relative z-10"
                          />
                        ) : state.error ? (
                          <div className="text-center p-8">
                            <div className="text-red-600 text-2xl mb-2">⚠</div>
                            <p className="text-red-600 text-sm">{state.error}</p>
                          </div>
                        ) : (
                          <div className="text-center text-gray-400">
                            <div className="w-12 h-12 mx-auto border-2 border-gray-300 rounded-full flex items-center justify-center mb-3">
                              <div className="text-xl">?</div>
                            </div>
                            <p className="text-sm font-light">
                              {state.isProcessing ? 'Processing...' : 'Waiting for processing'}
                            </p>
                          </div>
                        )}
                      </div>
                      
                      {/* Dimension Comparison */}
                      {state.processedImageDimensions && originalDimensions && (
                        <div className="text-xs text-gray-400 text-center">
                          {state.processedImageDimensions.width !== originalDimensions.width || 
                           state.processedImageDimensions.height !== originalDimensions.height ? (
                            <span className="text-blue-500">
                              Resized from {formatDimensions(originalDimensions.width, originalDimensions.height)}
                            </span>
                          ) : (
                            <span className="text-gray-500">Same dimensions</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Mobile Boundary */}
                  <div className="lg:hidden my-8 flex items-center">
                    <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
                    <div className="mx-4 w-6 h-6 bg-white border-2 border-gray-300 rounded-full flex items-center justify-center">
                      <div className="w-2 h-2 bg-gray-300 rounded-full"></div>
                    </div>
                    <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
                  </div>
                </section>
              </>
            )}

            {/* Action Buttons */}
            {originalImage && (
              <div className="flex justify-center gap-4 mt-8">
                {/* Check Image Button */}
                <button
                  onClick={checkImage}
                  disabled={checkState.isChecking}
                  className="px-8 py-3 bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 text-sm font-light tracking-wide uppercase"
                >
                  {checkState.isChecking ? 'Checking' : 'Check Quality'}
                </button>

                {/* Process Button - Only enabled after check is done */}
                <button
                  onClick={processImage}
                  disabled={state.isProcessing || !checkState.results}
                  className={`px-8 py-3 transition-colors duration-200 text-sm font-light tracking-wide uppercase ${
                    !checkState.results 
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-black text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed'
                  }`}
                  title={!checkState.results ? 'Please run quality check first' : ''}
                >
                  {state.isProcessing ? 'Processing' : 'Process'}
                </button>
                
                {state.processedImage && (
                  <button
                    onClick={downloadImage}
                    className="px-8 py-3 border border-black text-black hover:bg-black hover:text-white transition-colors duration-200 text-sm font-light tracking-wide uppercase"
                  >
                    Download
                  </button>
                )}
                
                <button
                  onClick={reset}
                  className="px-8 py-3 text-gray-500 hover:text-black transition-colors duration-200 text-sm font-light tracking-wide uppercase"
                >
                  Reset
                </button>
              </div>
            )}
          </main>
        </div>
      </div>
    </>
  )
}

export default Home