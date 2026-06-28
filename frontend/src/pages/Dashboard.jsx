import { useState, useEffect, useCallback } from 'react'
import api from '../api'

export default function Dashboard() {
  const [tab, setTab] = useState('overview')
  const [stats, setStats] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [rules, setRules] = useState([])
  const [logs, setLogs] = useState([])

  const [kw, setKw] = useState('')
  const [msg, setMsg] = useState('')
  const [matchType, setMatchType] = useState('exact')
  const [selectedAccount, setSelectedAccount] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const load = useCallback(async () => {
    try {
      const [s, a, r, l] = await Promise.all([
        api.get('/api/stats'),
        api.get('/api/ig-accounts'),
        api.get('/api/rules'),
        api.get('/api/dm-logs?limit=100'),
      ])
      setStats(s.data)
      setAccounts(a.data)
      setRules(r.data)
      setLogs(l.data)
      if (a.data.length > 0 && !selectedAccount) setSelectedAccount(a.data[0].id)
    } catch (e) {
      console.error('Load error:', e)
    }
  }, [selectedAccount])

  useEffect(() => { load() }, [load])

  const addRule = async (e) => {
    e.preventDefault()
    if (!kw || !msg || !selectedAccount) return
    setError('')
    setSuccess('')
    try {
      await api.post('/api/rules', {
        ig_account_id: selectedAccount,
        keyword: kw,
        reply_message: msg,
        match_type: matchType,
      })
      setKw('')
      setMsg('')
      setSuccess('Rule added!')
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create rule')
    }
  }

  const toggleRule = async (ruleId, active) => {
    await api.put(`/api/rules/${ruleId}`, { is_active: !active })
    load()
  }

  const deleteRule = async (ruleId) => {
    await api.delete(`/api/rules/${ruleId}`)
    load()
  }

  const tabs = ['overview', 'rules', 'logs']

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🐝</span>
            <h1 className="text-xl font-bold text-purple-400">Hanubees DM Bot</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="bg-green-900/50 text-green-300 text-xs px-3 py-1 rounded-full">Live</span>
          </div>
        </div>
        <nav className="max-w-6xl mx-auto px-6 flex gap-1">
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-3 text-sm font-medium capitalize border-b-2 transition ${
                tab === t ? 'border-purple-500 text-purple-400' : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Overview Tab */}
        {tab === 'overview' && (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'IG Accounts', val: stats?.accounts || 0 },
                { label: 'Active Rules', val: stats?.rules || 0 },
                { label: 'Total DMs Sent', val: stats?.total_dms || 0 },
                { label: 'DMs Today', val: stats?.dms_sent_today || 0 },
              ].map((s, i) => (
                <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                  <div className="text-3xl font-bold text-white">{s.val}</div>
                  <div className="text-sm text-gray-500 mt-1">{s.label}</div>
                </div>
              ))}
            </div>

            {/* Connect Instagram */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">Instagram Account</h2>
              {accounts.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-400 mb-4">No Instagram account connected</p>
                  <a
                    href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/oauth/connect`}
                    target="_blank"
                    className="inline-block bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold px-6 py-3 rounded-lg hover:opacity-90 transition"
                  >
                    Connect Instagram
                  </a>
                  <p className="text-gray-600 text-xs mt-3">
                    Log in via Instagram to authorize. We never see your password.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {accounts.map((a) => (
                    <div key={a.id} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-purple-700 rounded-full flex items-center justify-center text-sm font-bold">@</div>
                        <div>
                          <div className="font-medium">@{a.ig_username}</div>
                          <div className="text-xs text-gray-500">Connected {a.connected_at ? new Date(a.connected_at).toLocaleDateString() : ''}</div>
                        </div>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded ${a.is_active ? 'bg-green-900 text-green-400' : 'bg-gray-800 text-gray-500'}`}>
                        {a.is_active ? 'Active' : 'Paused'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent DMs */}
            {logs.length > 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold mb-4">Recent DMs</h2>
                <div className="space-y-2">
                  {logs.slice(0, 10).map((l) => (
                    <div key={l.id} className="bg-gray-800 rounded-lg px-4 py-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-purple-400">@{l.from_username}</span>
                        <span className="text-gray-600 text-xs">{new Date(l.created_at).toLocaleString()}</span>
                      </div>
                      <div className="text-gray-400 mt-1">Comment: &ldquo;{l.comment_text}&rdquo;</div>
                      <div className="text-gray-300 mt-0.5">DM: &ldquo;{l.dm_text}&rdquo;</div>
                      <span className={`text-xs ${l.status === 'sent' ? 'text-green-500' : 'text-red-500'}`}>{l.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Rules Tab */}
        {tab === 'rules' && (
          <div className="space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">Create Automation Rule</h2>
              {error && <div className="bg-red-900/50 border border-red-700 text-red-200 rounded-lg p-3 text-sm mb-4">{error}</div>}
              {success && <div className="bg-green-900/50 border border-green-700 text-green-200 rounded-lg p-3 text-sm mb-4">{success}</div>}
              <form onSubmit={addRule} className="space-y-4">
                <div>
                  <label className="text-sm text-gray-400 mb-1 block">Instagram Account</label>
                  <select
                    value={selectedAccount}
                    onChange={(e) => setSelectedAccount(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="">Select an account...</option>
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>@{a.ig_username}</option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-gray-400 mb-1 block">Match Type</label>
                    <select
                      value={matchType}
                      onChange={(e) => setMatchType(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-purple-500"
                    >
                      <option value="exact">Exact match</option>
                      <option value="contains">Contains</option>
                      <option value="starts_with">Starts with</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-gray-400 mb-1 block">Keyword</label>
                    <input
                      type="text" required placeholder="e.g. LINK" value={kw}
                      onChange={(e) => setKw(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm text-gray-400 mb-1 block">Reply Message</label>
                  <textarea
                    required placeholder="e.g. Here's your free guide: https://..." value={msg}
                    onChange={(e) => setMsg(e.target.value)}
                    rows={2}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 resize-none"
                  />
                </div>
                <button type="submit" className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-6 py-3 rounded-lg transition">
                  Add Rule
                </button>
              </form>
            </div>

            {/* Rules list */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">Your Rules ({rules.length})</h2>
              {rules.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No rules yet. Create one above.</p>
              ) : (
                <div className="space-y-3">
                  {rules.map((r) => (
                    <div key={r.id} className="bg-gray-800 rounded-lg p-4 flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="bg-purple-700 text-purple-200 text-xs px-2 py-0.5 rounded font-mono">{r.match_type}</span>
                          <span className="font-semibold text-white">&ldquo;{r.keyword}&rdquo;</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${r.is_active ? 'bg-green-900 text-green-400' : 'bg-gray-700 text-gray-500'}`}>
                            {r.is_active ? 'ON' : 'OFF'}
                          </span>
                        </div>
                        <div className="text-gray-400 text-sm">→ {r.reply_message}</div>
                        <div className="text-gray-600 text-xs mt-1">{r.dm_count} DMs sent</div>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => toggleRule(r.id, r.is_active)}
                          className={`px-3 py-1.5 text-xs rounded-lg transition ${r.is_active ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-green-800 text-green-300 hover:bg-green-700'}`}
                        >
                          {r.is_active ? 'Pause' : 'Activate'}
                        </button>
                        <button
                          onClick={() => deleteRule(r.id)}
                          className="px-3 py-1.5 text-xs bg-red-900/50 text-red-300 hover:bg-red-800 rounded-lg transition"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Logs Tab */}
        {tab === 'logs' && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">DM Logs ({logs.length})</h2>
            {logs.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No DMs sent yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b border-gray-800">
                      <th className="pb-3 font-medium">Time</th>
                      <th className="pb-3 font-medium">User</th>
                      <th className="pb-3 font-medium">Comment</th>
                      <th className="pb-3 font-medium">DM Sent</th>
                      <th className="pb-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((l) => (
                      <tr key={l.id} className="border-b border-gray-800/50">
                        <td className="py-3 text-gray-500 whitespace-nowrap">{new Date(l.created_at).toLocaleString()}</td>
                        <td className="py-3 text-purple-400">@{l.from_username}</td>
                        <td className="py-3 text-gray-400 max-w-xs truncate">{l.comment_text}</td>
                        <td className="py-3 text-gray-300 max-w-xs truncate">{l.dm_text}</td>
                        <td className="py-3">
                          <span className={`text-xs px-2 py-0.5 rounded ${l.status === 'sent' ? 'bg-green-900 text-green-400' : 'bg-red-900 text-red-400'}`}>
                            {l.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
