import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

interface HealthResponse {
  status: string
  version: string
  timestamp: string
}

function App() {
  const { data, isLoading, error } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await axios.get('/api/v1/health/')
      return res.data
    },
  })

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white shadow-lg rounded-xl p-8 max-w-md w-full">
        <h1 className="text-2xl font-bold text-brand-700 mb-2">UniMarket</h1>
        <p className="text-gray-600 mb-6">Everything you need. All in one place.</p>

        <div className="border-t pt-4">
          <h2 className="text-sm font-semibold text-gray-500 uppercase mb-2">
            Backend Health
          </h2>
          {isLoading && <p className="text-gray-500">Checking…</p>}
          {error && <p className="text-red-600">Cannot reach backend.</p>}
          {data && (
            <dl className="space-y-1 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Status</dt>
                <dd className="font-medium text-green-600">{data.status}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Version</dt>
                <dd className="font-medium">{data.version}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Timestamp</dt>
                <dd className="font-mono text-xs">{data.timestamp}</dd>
              </div>
            </dl>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
