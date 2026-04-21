import CodeGenPanel from '../CodeGenPanel'

export default function Step7CodeGen() {
  return (
    <div className="space-y-6">
      <div
        className="rounded-xl p-6 space-y-2"
        style={{ background: 'rgba(244,130,31,0.06)', border: '1px solid rgba(244,130,31,0.15)' }}
      >
        <h3 className="text-lg font-bold font-headline text-white flex items-center gap-2">
          <span className="material-symbols-outlined" style={{ color: '#f4821f' }}>code</span>
          Code 생성
        </h3>
        <p className="text-sm" style={{ color: '#888' }}>
          생성된 Spec을 기반으로 Spring Boot + Vue3 코드를 자동 생성합니다.
        </p>
      </div>

      <CodeGenPanel />
    </div>
  )
}
