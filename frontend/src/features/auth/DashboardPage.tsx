import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { fetchMe } from './api'
import { useAuthStore } from './store'

interface Stats {
  categories: number
  provinces: number
  users: number
  sellers: number
  products: number
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user, setUser, logout } = useAuthStore()

  const me = useQuery({
    queryKey: ['me'],
    queryFn: fetchMe,
    retry: 1,
  })

  const stats = useQuery<Stats>({
    queryKey: ['public-stats'],
    queryFn: async () => (await axios.get('/api/v1/public/stats/')).data,
  })

  useEffect(() => {
    if (me.data) setUser(me.data)
  }, [me.data, setUser])

  useEffect(() => {
    if (me.error && (me.error as { response?: { status?: number } }).response?.status === 401) {
      logout()
      navigate('/login', { replace: true })
    }
  }, [me.error, logout, navigate])

  const current = me.data ?? user

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-600 text-white flex items-center justify-center font-bold">
              U
            </div>
            <span className="text-lg font-bold text-gray-900">UniMarket</span>
          </Link>

          <div className="flex items-center gap-4">
            <span className="hidden sm:block text-sm text-gray-600">
              {current?.full_name}
            </span>
            <button
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="text-sm font-medium text-gray-600 hover:text-red-600"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Body */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back{current?.first_name ? `, ${current.first_name}` : ''}
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Your UniMarket account overview.
          </p>
        </div>

        {/* Personal stats (these reflect YOUR activity) */}
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          {[
            { label: 'Your orders', value: '0', hint: 'No orders yet' },
            { label: 'Your listings', value: '0', hint: 'No products listed' },
            { label: 'Your messages', value: '0', hint: 'No unread messages' },
          ].map((stat) => (
            <div key={stat.label} className="bg-white border border-gray-200 rounded-xl p-5">
              <p className="text-sm text-gray-500">{stat.label}</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
              <p className="text-xs text-gray-400 mt-1">{stat.hint}</p>
            </div>
          ))}
        </div>

        {/* Account details */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Account</h2>
          {current ? (
            <dl className="grid sm:grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-gray-500">Full name</dt>
                <dd className="font-medium text-gray-900 mt-1">{current.full_name}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Email</dt>
                <dd className="font-mono text-gray-900 mt-1">{current.email}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Phone</dt>
                <dd className="font-medium text-gray-900 mt-1">
                  {current.phone || 'Not set'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">User ID</dt>
                <dd className="font-mono text-xs text-gray-700 mt-1">{current.id}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-gray-500">Loading profile…</p>
          )}
        </div>

        {/* Marketplace stats (real numbers from the DB) */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Marketplace</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {stats.data ? (
              <>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stats.data.categories}</p>
                  <p className="text-xs text-gray-500 mt-1">Categories</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stats.data.provinces}</p>
                  <p className="text-xs text-gray-500 mt-1">Provinces</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stats.data.users}</p>
                  <p className="text-xs text-gray-500 mt-1">Registered users</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stats.data.products}</p>
                  <p className="text-xs text-gray-500 mt-1">Products listed</p>
                </div>
              </>
            ) : (
              <p className="text-sm text-gray-500 col-span-4">Loading…</p>
            )}
          </div>
        </div>

        {/* Next steps */}
        <div className="bg-brand-50 border border-brand-100 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-gray-900">What's next?</h2>
          <p className="text-sm text-gray-600 mt-1">
            Your account is ready. In upcoming phases you'll be able to browse products,
            create listings, and start selling.
          </p>
        </div>
      </main>
    </div>
  )
}
