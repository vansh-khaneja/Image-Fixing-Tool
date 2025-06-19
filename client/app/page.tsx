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

const Home: React.FC = () => {
  const [originalImage, setOriginalImage] = useState<OriginalImage | null>(null)
  const [originalDimensions, setOriginalDimensions] = useState<{ width: number; height: number } | null>(null)
  const [state, setState] = useState<ProcessingState>({
    isProcessing: false,
    error: null,
    processedImage: null,
    processedImageDimensions: null
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
          setState({
            isProcessing: false,
            error: null,
            processedImage: null,
            processedImageDimensions: null
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

      const response = await fetch('http://localhost:8000/process-image/', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Processing failed: ${response.status}`)
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
      link.download = `processed_${originalImage.file.name}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  }

  const reset = (): void => {
    setOriginalImage(null)
    setOriginalDimensions(null)
    setState({
      isProcessing: false,
      error: null,
      processedImage: null,
      processedImageDimensions: null
    })
    
    if (state.processedImage) {
      URL.revokeObjectURL(state.processedImage)
    }
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
          <header className="text-center mb-12">
            <div className="inline-flex items-center gap-3 mb-4">
              <div className="w-8 h-8 bg-black rounded-full flex items-center justify-center">
                <div className="w-4 h-4 bg-white rounded-full animate-pulse"></div>
              </div>
              <h1 className="text-3xl font-light tracking-wide">Image Processor</h1>
            </div>
            <p className="text-gray-500 text-sm font-light">
              Transform your images
            </p>
          </header>

          {/* Main Content */}
          <main>
            {!originalImage ? (
              /* Upload Area */
              <section
                {...getRootProps()}
                className={`relative border-2 border-dashed rounded-none p-20 text-center cursor-pointer transition-all duration-300 mx-auto max-w-2xl
                  ${isDragActive 
                    ? 'border-black bg-gray-50' 
                    : 'border-gray-300 hover:border-gray-400'
                  }`}
              >
                <input {...getInputProps()} />
                <div className="space-y-6">
                  <div className="w-16 h-16 mx-auto border-2 border-black rounded-full flex items-center justify-center">
                    <div className="text-2xl">+</div>
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
              /* Horizontal Layout with Boundary */
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
                        className="w-full h-auto max-h-96 object-contain relative z-10"
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
                    <div className="border border-gray-300 bg-gray-100 min-h-96 flex items-center justify-center overflow-hidden" style={{
                      backgroundImage: `url("data:image/svg+xml,%3csvg width='20' height='20' xmlns='http://www.w3.org/2000/svg'%3e%3cdefs%3e%3cpattern id='a' patternUnits='userSpaceOnUse' width='20' height='20'%3e%3crect fill='%23f9fafb' width='10' height='10'/%3e%3crect fill='%23f3f4f6' x='10' y='10' width='10' height='10'/%3e%3c/pattern%3e%3c/defs%3e%3crect width='100%25' height='100%25' fill='url(%23a)'/%3e%3c/svg%3e")`,
                      backgroundSize: '20px 20px'
                    }}>
                      {state.processedImage ? (
                        <img
                          src={state.processedImage}
                          alt="Processed"
                          className="w-full h-auto max-h-96 object-contain relative z-10"
                        />
                      ) : state.error ? (
                        <div className="text-center p-8">
                          <div className="text-red-600 text-2xl mb-2">⚠</div>
                          <p className="text-red-600 text-sm">{state.error}</p>
                        </div>
                      ) : (
                        <div className="text-center text-gray-400">
                          <div className="w-16 h-16 mx-auto border-2 border-gray-300 rounded-full flex items-center justify-center mb-4">
                            <div className="text-2xl">?</div>
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
            )}

            {/* Action Buttons */}
            {originalImage && (
              <div className="flex justify-center gap-4 mt-12">
                <button
                  onClick={processImage}
                  disabled={state.isProcessing}
                  className="px-8 py-3 bg-black text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 text-sm font-light tracking-wide uppercase"
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