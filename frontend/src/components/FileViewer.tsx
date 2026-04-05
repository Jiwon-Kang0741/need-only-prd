import { useState } from 'react'
import type { GeneratedFile } from '../types'

interface Props {
  files: GeneratedFile[]
}

export default function FileViewer({ files }: Props) {
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [filter, setFilter] = useState<'all' | 'backend' | 'frontend'>('all')

  const filtered = filter === 'all' ? files : files.filter((f) => f.layer === filter)
  const selected = filtered[selectedIndex] ?? filtered[0]

  const backendCount = files.filter((f) => f.layer === 'backend').length
  const frontendCount = files.filter((f) => f.layer === 'frontend').length

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text)
  }

  function downloadAllAsZip() {
    // Simple approach: download each file content as a combined text
    // For a real ZIP, we'd use jszip — keeping it simple for now
    if (!selected) return
    const blob = new Blob([selected.content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = selected.file_path.split('/').pop() ?? 'file.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (files.length === 0) {
    return <p className="text-sm text-white/50">No files generated yet.</p>
  }

  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="bg-black/30 border-b border-white/10 px-3 py-2 flex items-center gap-3">
        <div className="flex gap-1">
          {(['all', 'backend', 'frontend'] as const).map((f) => (
            <button
              key={f}
              onClick={() => { setFilter(f); setSelectedIndex(0) }}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                filter === f ? 'bg-primary/20 text-primary' : 'text-white/40 hover:bg-white/5'
              }`}
            >
              {f === 'all' ? `All (${files.length})` : f === 'backend' ? `Backend (${backendCount})` : `Frontend (${frontendCount})`}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        {selected && (
          <>
            <button
              onClick={() => copyToClipboard(selected.content)}
              className="text-xs text-white/40 hover:text-white/60"
              title="Copy to clipboard"
            >
              Copy
            </button>
            <button
              onClick={downloadAllAsZip}
              className="text-xs text-white/40 hover:text-white/60"
              title="Download file"
            >
              Download
            </button>
          </>
        )}
      </div>

      <div className="flex" style={{ height: '400px' }}>
        {/* File tree */}
        <div className="w-64 border-r border-white/10 overflow-y-auto bg-black/20 flex-shrink-0 no-scrollbar">
          {filtered.map((f, i) => (
            <button
              key={i}
              onClick={() => setSelectedIndex(i)}
              className={`w-full text-left px-3 py-1.5 text-xs border-b border-white/5 transition-colors ${
                i === selectedIndex ? 'bg-primary/10 text-primary' : 'text-white/70 hover:bg-white/5'
              }`}
            >
              <div className="font-mono truncate">{f.file_path.split('/').pop()}</div>
              <div className="text-white/30 truncate text-[10px]">{f.file_path}</div>
            </button>
          ))}
        </div>

        {/* Code display */}
        <div className="flex-1 overflow-auto">
          {selected ? (
            <div>
              <div className="bg-black/60 text-white/40 px-3 py-1.5 text-xs font-mono sticky top-0">
                {selected.file_path}
                <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  selected.layer === 'backend' ? 'bg-emerald-900/50 text-emerald-300' : 'bg-blue-900/50 text-blue-300'
                }`}>
                  {selected.layer}
                </span>
              </div>
              <pre className="bg-black/40 text-gray-100 text-xs p-3 font-mono whitespace-pre-wrap">
                {selected.content}
              </pre>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-white/40">
              Select a file to view
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
