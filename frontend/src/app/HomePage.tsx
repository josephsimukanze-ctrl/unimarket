import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import axios from 'axios'

interface HealthResponse {
  status: string
  version: string
  timestamp: string
}

interface Category {
  id: number
  name: string
  slug: string
  description: string
  icon: string
  display_order: number
  children: { id: number; name: string; slug: string; icon: string }[]
}

interface Stats {
  categories: number
  provinces: number
  users: number
  sellers: number
  products: number
}

export default function HomePage() {
  const health = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => (await axios.get('/api/v1/health/')).data,
  })

  const categories = useQuery<Category[]>({
    queryKey: ['public-categories'],
    queryFn: async () => (await axios.get('/api/v1/public/categories/')).data,
  })

  const stats = useQuery<Stats>({
    queryKey: ['public-stats'],
    queryFn: async () => (await axios.get('/api/v1/public/stats/')).data,
  })

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-600 text-white flex items-center justify-center font-bold">
              U
            </div>
            <span className="text-xl font-bold text-gray-900">UniMarket</span>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-600">
            <a href="#categories" className="hover:text-brand-600">Categories</a>
            <a href="#how" className="hover:text-brand-600">How it works</a>
            <a href="#trust" className="hover:text-brand-600">Trust & Safety</a>
          </nav>

          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-brand-600">
              Sign in
            </Link>
            <Link
              to="/register"
              className="text-sm font-medium bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg transition"
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      <section className="bg-gradient-to-b from-brand-50 to-white">
        <div className="max-w-7xl mx-auto px-6 py-20 md:py-28 text-center">
          <span className="inline-block text-xs font-semibold uppercase tracking-wider text-brand-700 bg-brand-100 px-3 py-1 rounded-full mb-4">
            Made in Zambia, ready for Africa
          </span>
          <h1 className="text-4xl md:text-6xl font-extrabold text-gray-900 leading-tight">
            Everything you need.{' '}
            <span className="text-brand-600">All in one place.</span>
          </h1>
          <p className="mt-6 text-lg text-gray-600 max-w-2xl mx-auto">
            Buy and sell retail, wholesale, and in bulk. Join auctions, request quotes,
            and connect with verified suppliers across Zambia and beyond.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/register"
              className="bg-brand-600 hover:bg-brand-700 text-white px-8 py-3 rounded-lg font-semibold shadow-lg shadow-brand-600/20 transition"
            >
              Start selling today
            </Link>
            <a
              href="#categories"
              className="border border-gray-300 hover:border-brand-600 text-gray-800 px-8 py-3 rounded-lg font-semibold transition"
            >
              Browse marketplace
            </a>
          </div>

          <div className="mt-12 grid grid-cols-3 gap-6 max-w-2xl mx-auto text-center">
            <div>
              <p className="text-2xl md:text-3xl font-bold text-gray-900">
                {stats.data ? stats.data.products : '—'}
              </p>
              <p className="text-xs text-gray-500 mt-1">Products listed</p>
            </div>
            <div>
              <p className="text-2xl md:text-3xl font-bold text-gray-900">
                {stats.data ? stats.data.users : '—'}
              </p>
              <p className="text-xs text-gray-500 mt-1">Registered users</p>
            </div>
            <div>
              <p className="text-2xl md:text-3xl font-bold text-gray-900">
                {stats.data ? stats.data.provinces : '—'}
              </p>
              <p className="text-xs text-gray-500 mt-1">Provinces served</p>
            </div>
          </div>
        </div>
      </section>

      <section id="categories" className="max-w-7xl mx-auto px-6 py-20">
        <div className="flex items-end justify-between mb-10">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Shop by category</h2>
            <p className="mt-2 text-gray-600">Find exactly what you need, fast.</p>
          </div>
          <Link to="/register" className="hidden sm:inline text-sm font-medium text-brand-600 hover:text-brand-700">
            Get started →
          </Link>
        </div>

        {categories.isLoading && <p className="text-gray-500">Loading categories…</p>}
        {categories.error && <p className="text-red-600">Could not load categories.</p>}

        {categories.data && categories.data.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {categories.data.map((cat) => (
              <div
                key={cat.id}
                className="group border border-gray-200 rounded-xl p-5 hover:border-brand-600 hover:shadow-md transition cursor-pointer"
              >
                <div className="text-3xl mb-3">{cat.icon || '📦'}</div>
                <h3 className="font-semibold text-gray-900 group-hover:text-brand-600">
                  {cat.name}
                </h3>
                {cat.children.length > 0 && (
                  <p className="text-xs text-gray-500 mt-1">
                    {cat.children.length} subcategories
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {categories.data && categories.data.length === 0 && (
          <p className="text-gray-500">No categories yet. Check back soon.</p>
        )}
      </section>

      <section id="how" className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900">How UniMarket works</h2>
            <p className="mt-2 text-gray-600">One account. Unlimited ways to buy and sell.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: 'Create your account',
                desc: 'Sign up in under a minute as an individual, retailer, or business. Verify once, trade everywhere.',
              },
              {
                step: '02',
                title: 'Buy, sell, or trade',
                desc: 'List retail products, run auctions, offer wholesale tiers, or send RFQs to verified suppliers.',
              },
              {
                step: '03',
                title: 'Get paid securely',
                desc: 'Pay with mobile money, bank transfer, or card. Track every order from dispatch to delivery.',
              },
            ].map((item) => (
              <div key={item.step} className="bg-white rounded-xl p-8 border border-gray-100 shadow-sm">
                <span className="text-4xl font-extrabold text-brand-100">{item.step}</span>
                <h3 className="text-lg font-semibold text-gray-900 mt-4">{item.title}</h3>
                <p className="mt-2 text-sm text-gray-600 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="trust" className="max-w-7xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Built on trust</h2>
            <p className="mt-4 text-gray-600 leading-relaxed">
              UniMarket verifies sellers, protects payments, and keeps every transaction
              auditable. Whether you're buying a phone or procuring industrial equipment,
              you know who you're dealing with.
            </p>

            <ul className="mt-6 space-y-3">
              {[
                'Verified business identities and documents',
                'Secure payments with mobile money and bank transfers',
                'Buyer protection and dispute resolution',
                'Transparent seller ratings from real transactions',
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-gray-700">
                  <span className="text-green-600 font-bold mt-0.5">✓</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-gray-50 rounded-2xl p-8 border border-gray-100">
            <h3 className="font-semibold text-gray-900 mb-4">System status</h3>
            {health.isLoading && <p className="text-sm text-gray-500">Checking…</p>}
            {health.error && <p className="text-sm text-red-600">Backend unreachable</p>}
            {health.data && (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">API</dt>
                  <dd className="font-medium text-green-600 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500"></span>
                    {health.data.status}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Version</dt>
                  <dd className="font-mono text-xs text-gray-700">{health.data.version}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Last check</dt>
                  <dd className="font-mono text-xs text-gray-700">
                    {new Date(health.data.timestamp).toLocaleTimeString()}
                  </dd>
                </div>
              </dl>
            )}
          </div>
        </div>
      </section>

      <section className="bg-brand-600 py-16">
        <div className="max-w-4xl mx-auto px-6 text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold">Ready to start trading?</h2>
          <p className="mt-4 text-brand-100 text-lg">
            Join buyers and sellers across Zambia. It's free to register.
          </p>
          <Link
            to="/register"
            className="inline-block mt-8 bg-white text-brand-700 px-8 py-3 rounded-lg font-semibold hover:bg-brand-50 transition"
          >
            Create your account
          </Link>
        </div>
      </section>

      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-lg bg-brand-600 text-white flex items-center justify-center font-bold">
                  U
                </div>
                <span className="text-white font-bold">UniMarket</span>
              </div>
              <p className="text-sm leading-relaxed">
                Everything you need. All in one place. Zambia's unified marketplace for
                retail and B2B trade.
              </p>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-3 text-sm">Marketplace</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#categories" className="hover:text-white">Categories</a></li>
                <li><a href="#" className="hover:text-white">Auctions</a></li>
                <li><a href="#" className="hover:text-white">Wholesale</a></li>
                <li><a href="#" className="hover:text-white">Suppliers</a></li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-3 text-sm">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">About</a></li>
                <li><a href="#" className="hover:text-white">Careers</a></li>
                <li><a href="#" className="hover:text-white">Press</a></li>
                <li><a href="#" className="hover:text-white">Contact</a></li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-3 text-sm">Support</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">Help center</a></li>
                <li><a href="#" className="hover:text-white">Trust & safety</a></li>
                <li><a href="#" className="hover:text-white">Privacy</a></li>
                <li><a href="#" className="hover:text-white">Terms</a></li>
              </ul>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t border-gray-800 flex flex-col md:flex-row justify-between items-center gap-4 text-xs">
            <p>© {new Date().getFullYear()} UniMarket. All rights reserved.</p>
            <p>Built in Zambia · Serving Africa</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
