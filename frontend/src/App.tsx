import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type DocumentItem = {
  document_id: string
  filename: string
  chunk_count: number
}

type Citation = {
  document_id: string
  filename: string
  chunk_id: string
  score: number
  snippet: string
}

type ChatResponse = {
  grounded: boolean
  refused: boolean
  answer: string
  confidence: number
  citations: Citation[]
  retrieval: {
    max_score: number
    threshold: number
    top_k: number
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [query, setQuery] = useState('')
  const [chat, setChat] = useState<ChatResponse | null>(null)
  const [uploading, setUploading] = useState(false)
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasDocs = useMemo(() => documents.length > 0, [documents])

  async function loadDocuments() {
    try {
      const res = await fetch(`${API_BASE}/documents`)
      if (!res.ok) throw new Error('Failed to load documents')
      setDocuments(await res.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    const input = (e.currentTarget.elements.namedItem('file') as HTMLInputElement) || null
    const file = input?.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    try {
      const res = await fetch(`${API_BASE}/documents/upload`, { method: 'POST', body: formData })
      if (!res.ok) {
        const body = await res.json()
        throw new Error(body.detail ?? 'Upload failed')
      }
      await loadDocuments()
      input.value = ''
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setUploading(false)
    }
  }

  async function onAsk(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!query.trim()) return
    setAsking(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      if (!res.ok) {
        const body = await res.json()
        throw new Error(body.detail ?? 'Chat failed')
      }
      setChat(await res.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setAsking(false)
    }
  }

  return (
    <main className="layout">
      <header>
        <h1>CampusGPT Portfolio Dashboard</h1>
        <p>Grounded, citation-first campus document assistant using local TF-IDF retrieval.</p>
      </header>

      <section className="grid two">
        <article className="card">
          <h2>Upload Documents</h2>
          <form onSubmit={onUpload}>
            <input name="file" type="file" accept=".pdf,.txt,.md" />
            <button type="submit" disabled={uploading}>{uploading ? 'Uploading…' : 'Upload'}</button>
          </form>
          {!hasDocs ? <p className="empty">No documents indexed yet.</p> : null}
          <ul>
            {documents.map((doc) => (
              <li key={doc.document_id}>
                <strong>{doc.filename}</strong>
                <span>{doc.chunk_count} chunks</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h2>Ask CampusGPT</h2>
          <form onSubmit={onAsk}>
            <textarea
              placeholder="Ask about uploaded policies, rules, schedules…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" disabled={asking || !hasDocs}>{asking ? 'Thinking…' : 'Ask'}</button>
          </form>

          {!chat && <p className="empty">Answers, refusal status, citations, and confidence will appear here.</p>}

          {chat && (
            <div className="chat-result">
              <p className={chat.refused ? 'pill refused' : 'pill grounded'}>
                {chat.refused ? 'Refused (insufficient evidence)' : 'Grounded Answer'}
              </p>
              <p>{chat.answer}</p>
              <small>
                confidence={chat.confidence.toFixed(3)} | max_score={chat.retrieval.max_score.toFixed(3)} |
                threshold={chat.retrieval.threshold.toFixed(3)}
              </small>
              <h3>Citations</h3>
              {chat.citations.length === 0 ? <p className="empty">No citations for refusal response.</p> : null}
              <ul>
                {chat.citations.map((c) => (
                  <li key={c.chunk_id}>
                    <b>{c.filename}</b> ({c.chunk_id}) score={c.score.toFixed(3)}
                    <p>{c.snippet}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </article>
      </section>

      <section className="grid one">
        <article className="card">
          <h2>Architecture / About</h2>
          <p>
            Backend: FastAPI + local JSON index + TF-IDF lexical retrieval + extractive grounded answer + optional
            OpenAI-compatible provider through environment variables only.
          </p>
          <p>
            Frontend: React + TypeScript + Vite dashboard with upload, listing, chat, refusal indicators, citations,
            confidence, and retrieval metadata.
          </p>
        </article>
      </section>

      {error ? <p className="error">{error}</p> : null}
    </main>
  )
}

export default App
