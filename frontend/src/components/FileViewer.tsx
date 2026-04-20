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
    return <p className="text-sm text-neutral-600">아직 생성된 파일이 없습니다.</p>
  }

  return (
    <div className="border border-neutral-200 rounded-lg overflow-hidden bg-white">
      {/* Toolbar */}
      <div className="bg-neutral-100 border-b border-neutral-200 px-3 py-2 flex items-center gap-3">
        <div className="flex gap-1">
          {(['all', 'backend', 'frontend'] as const).map((f) => (
            <button
              key={f}
              onClick={() => { setFilter(f); setSelectedIndex(0) }}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                filter === f ? 'bg-primary/15 text-primary font-bold' : 'text-neutral-600 hover:bg-neutral-200'
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
              className="text-xs text-neutral-600 hover:text-neutral-900"
              title="Copy to clipboard"
            >
              Copy
            </button>
            <button
              onClick={downloadAllAsZip}
              className="text-xs text-neutral-600 hover:text-neutral-900"
              title="Download file"
            >
              Download
            </button>
          </>
        )}
      </div>

      <div className="flex" style={{ height: '400px' }}>
        {/* File tree */}
        <div className="w-64 border-r border-neutral-200 overflow-y-auto bg-neutral-50 flex-shrink-0 no-scrollbar">
          {filtered.map((f, i) => (
            <button
              key={i}
              onClick={() => setSelectedIndex(i)}
              className={`w-full text-left px-3 py-1.5 text-xs border-b border-neutral-100 transition-colors ${
                i === selectedIndex ? 'bg-primary/10 text-neutral-900 font-medium' : 'text-neutral-800 hover:bg-neutral-100'
              }`}
            >
              <div className="font-mono truncate">{f.file_path.split('/').pop()}</div>
              <div className="text-neutral-500 truncate text-[10px]">{f.file_path}</div>
            </button>
          ))}
        </div>

        {/* Code display */}
        <div className="flex-1 overflow-auto bg-white">
          {selected ? (
            <div>
              <div className="bg-neutral-100 text-neutral-700 px-3 py-1.5 text-xs font-mono sticky top-0 border-b border-neutral-200">
                {selected.file_path}
                <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  selected.layer === 'backend' ? 'bg-emerald-100 text-emerald-900' : 'bg-sky-100 text-sky-900'
                }`}>
                  {selected.layer}
                </span>
              </div>
              <pre className="bg-neutral-50 text-neutral-900 text-xs p-3 font-mono whitespace-pre-wrap border-t border-neutral-100">
                {selected.content}
              </pre>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-neutral-500">
              파일을 선택하세요
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
