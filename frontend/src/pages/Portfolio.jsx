import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import Sparkline from '../components/Sparkline'

function fmtINR(n)
{
	return Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
}
function fmtIST(iso)
{
	if (!iso) return ''
	const dt = new Date(iso)
	try
	{
		return dt.toLocaleString('en-IN', {
			timeZone: 'Asia/Kolkata',
			year: 'numeric', month: 'short', day: 'numeric',
			hour: '2-digit', minute: '2-digit', hour12: true
		})
	} catch
	{
		return dt.toString()
	}
}

export default function Portfolio()
{
	const [pf, setPf] = useState(null)
	const [trades, setTrades] = useState([])
	const [loading, setLoading] = useState(true)

	const [rows, setRows] = useState([])
	const [sparks, setSparks] = useState({})

	const [amt, setAmt] = useState('')
	const [msg, setMsg] = useState('')
	const [err, setErr] = useState('')

	const [holdingsSearch, setHoldingsSearch] = useState('')
	const [holdingsLimit, setHoldingsLimit] = useState('10')
	const [tradesLimit, setTradesLimit] = useState('10')
	const [sortBy, setSortBy] = useState('value')
	const [sortDir, setSortDir] = useState('desc')

	const navigate = useNavigate()
	const mapLimit = (v) => (v === 'all' ? 1000 : Number(v))

	const reload = async () =>
	{
		setLoading(true)
		setErr('')
		setMsg('')
		try
		{
			const [pfRes, trRes] = await Promise.all([
				api.get('/api/portfolio'),
				api.get('/api/trades/recent', { params: { limit: mapLimit(tradesLimit) } })
			])
			const pfData = pfRes.data
			setPf(pfData)
			setTrades(trRes.data || [])

			const pos = pfData?.positions || {}
			const tokens = Object.keys(pos).filter(t => (pos[t]?.quantity || 0) > 0)
			if (tokens.length === 0)
			{
				setRows([]); setSparks({}); return
			}

			const now = new Date()
			const from = new Date(now)
			from.setDate(from.getDate() - 60)
			const seriesMap = {}
			await Promise.all(tokens.map(async (tok) =>
			{
				try
				{
					const res = await api.get('/api/candles', {
						params: { token: tok, interval: 'ONE_DAY', from: from.toISOString(), to: now.toISOString() }
					})
					seriesMap[tok] = res.data?.series || []
				} catch
				{
					seriesMap[tok] = []
				}
			}))

			const baseRows = []
			const sparkMap = {}
			let sumCurrent = 0, sumPrev = 0, sumInvested = 0

			for (const tok of tokens)
			{
				const p = pos[tok]
				const qty = Number(p.quantity || 0)
				const avg = Number(p.avg_price || 0)
				const invested = qty * avg

				const series = seriesMap[tok] || []
				const n = series.length
				const lastClose = n >= 1 ? Number(series[n - 1].c) : avg
				const prevClose = n >= 2 ? Number(series[n - 2].c) : lastClose
				const dayOpen = n >= 1 ? Number(series[n - 1].o) : avg

				const current = qty * lastClose
				const prev = qty * prevClose
				const dayAbs = current - prev
				const dayPct = prev > 0 ? (dayAbs / prev) * 100 : 0
				const totalAbs = current - invested
				const totalPct = invested > 0 ? (totalAbs / invested) * 100 : 0

				baseRows.push({ token: tok, symbol: p.symbol, qty, avg, invested, prevClose, lastClose, dayOpen, current, dayAbs, dayPct, totalAbs, totalPct })
				sumCurrent += current
				sumPrev += prev
				sumInvested += invested
				sparkMap[tok] = series.slice(-40).map(s => Number(s.c)).filter(Number.isFinite)
			}

			const dir = sortDir === 'asc' ? 1 : -1
			baseRows.sort((a, b) => dir * (a.current - b.current))

			setRows(baseRows)
			setSparks(sparkMap)
		} finally
		{
			setLoading(false)
		}
	}

	useEffect(() => { reload() }, [])
	useEffect(() => { reload() }, [tradesLimit])

	const deposit = async () =>
	{
		setMsg(''); setErr('')
		const value = Number(amt)
		if (!Number.isFinite(value) || value <= 0) { setErr('Enter a positive amount'); return }
		if (pf)
		{
			const remaining = Math.max(0, 1_000_000 - Number(pf.cash || 0))
			if (value > remaining)
			{
				setErr(`You can add up to ₹ ${fmtINR(remaining)} only`)
				return
			}
		}
		try
		{
			const res = await api.post('/api/portfolio/deposit', { amount: value })
			setPf(res.data); setMsg(`Added ₹ ${value.toFixed(2)} to your cash`); setAmt('')
		} catch (e)
		{
			const m = e?.response?.data?.detail || 'Deposit failed'
			setErr(String(m))
		}
	}

	const resetPortfolio = async () =>
	{
		if (!window.confirm('Reset portfolio? This will clear trades, positions and set cash to ₹10,00,000.')) return
		try
		{
			await api.post('/api/portfolio/reset')
			await reload()
			alert('Portfolio reset complete.')
		} catch (e)
		{
			alert(e?.response?.data?.detail || 'Reset failed')
		}
	}

	const filteredHoldings = useMemo(() =>
	{
		const q = holdingsSearch.trim().toLowerCase()
		const list = rows.filter(r => !q || r.symbol.toLowerCase().includes(q))
		const n = holdingsLimit === 'all' ? list.length : Number(holdingsLimit)
		return list.slice(0, n)
	}, [rows, holdingsSearch, holdingsLimit])

	const displayRows = useMemo(() =>
	{
		const arr = [...filteredHoldings]
		const dir = sortDir === 'asc' ? 1 : -1
		arr.sort((a, b) =>
		{
			if (sortBy === 'symbol') return dir * String(a.symbol).localeCompare(String(b.symbol))
			const map = { value: 'current', day: 'dayAbs', total: 'totalAbs' }
			const key = map[sortBy] || 'current'
			return dir * (a[key] - b[key])
		})
		return arr
	}, [filteredHoldings, sortBy, sortDir])

	const summary = useMemo(() =>
	{
		if (!rows.length) return { value: 0, invested: 0, dayAbs: 0, dayPct: 0, totalAbs: 0, totalPct: 0 }
		let value = 0, invested = 0, prevSum = 0
		for (const r of rows)
		{
			value += r.current
			invested += r.invested
			prevSum += r.qty * r.prevClose
		}
		const dayAbs = value - prevSum
		const dayPct = prevSum > 0 ? (dayAbs / prevSum) * 100 : 0
		const totalAbs = value - invested
		const totalPct = invested > 0 ? (totalAbs / invested) * 100 : 0
		return { value, invested, dayAbs, dayPct, totalAbs, totalPct }
	}, [rows])

	return (
		<div className="grid">
			<h2>My Portfolio</h2>

			{loading && <div className="card">Loading…</div>}

			{!loading && pf && (
				<>
					<div className="card">
						<div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
							<div>
								<div><b>Cash:</b> ₹ {fmtINR(pf.cash)}</div>
								<div><b>Realized P&L:</b> {pf.realized_pl >= 0 ? '+' : ''}{fmtINR(pf.realized_pl)}</div>
								<div><small className="muted">Last updated: {fmtIST(pf.updated_at)}</small></div>
							</div>
							<div className="row" style={{ alignItems: 'center', gap: 8 }}>
								<input
									className="input"
									style={{ width: 160 }}
									placeholder="Add funds (₹)"
									type="number"
									min="1"
									value={amt}
									onChange={(e) => setAmt(e.target.value)}
								/>
								<button className="btn primary" onClick={deposit}>Add Funds</button>
								<button className="btn danger" onClick={resetPortfolio}>Reset Portfolio</button>
							</div>
						</div>
						{(msg || err) && (
							<div style={{ marginTop: 6, fontSize: 12, color: err ? 'var(--danger)' : 'var(--accent)' }}>
								{err || msg}
							</div>
						)}
					</div>

					<div className="card">
						<div className="section-title">Holdings</div>
						<div className="holdings-summary">
							<div className="metric">
								<div className="metric-title">Holdings value</div>
								<div className="metric-value">₹ {fmtINR(summary.value)}</div>
							</div>
							<div className="metric">
								<div className="metric-title">1D returns</div>
								<div className="metric-value" style={{ color: summary.dayAbs >= 0 ? 'var(--accent)' : 'var(--danger)' }}>
									{summary.dayAbs >= 0 ? '+' : ''}₹ {fmtINR(summary.dayAbs)} ({summary.dayPct.toFixed(2)}%)
								</div>
							</div>
							<div className="metric">
								<div className="metric-title">Total returns</div>
								<div className="metric-value" style={{ color: summary.totalAbs >= 0 ? 'var(--accent)' : 'var(--danger)' }}>
									{summary.totalAbs >= 0 ? '+' : ''}₹ {fmtINR(summary.totalAbs)} ({summary.totalPct.toFixed(2)}%)
								</div>
							</div>
							<div className="metric">
								<div className="metric-title">Invested</div>
								<div className="metric-value">₹ {fmtINR(summary.invested)}</div>
							</div>
						</div>
					</div>

					<div className="card">
						<div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
							<div className="section-title" style={{ margin: 0 }}>Stocks you hold</div>
							<div className="row" style={{ alignItems: 'center', gap: 8 }}>
								<input
									className="input" style={{ width: 180 }}
									placeholder="Search holdings..."
									value={holdingsSearch}
									onChange={(e) => setHoldingsSearch(e.target.value)}
								/>
								<small className="muted">Show</small>
								<select className="select" value={holdingsLimit} onChange={(e) => setHoldingsLimit(e.target.value)}>
									<option value="10">10</option>
									<option value="25">25</option>
									<option value="all">All</option>
								</select>
								<small className="muted">Sort</small>
								<select className="select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
									<option value="value">By value</option>
									<option value="day">By 1D P/L</option>
									<option value="total">By Total P/L</option>
									<option value="symbol">By Symbol</option>
								</select>
								<button className="btn small" onClick={() => setSortDir(sortDir === 'asc' ? 'desc' : 'asc')}>
									{sortDir === 'asc' ? 'Asc' : 'Desc'}
								</button>
							</div>
						</div>

						{displayRows.length === 0 && <small className="muted">No positions.</small>}
						{displayRows.map((r) => (
							<div key={r.token} className="row" style={{ justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px dashed var(--border)' }}>
								<div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
									<div onClick={() => navigate(`/stock/${encodeURIComponent(r.symbol)}`)} style={{ cursor: 'pointer' }}>
										<div style={{ fontWeight: 600 }}>{r.symbol}</div>
										<div style={{ fontSize: 12, color: 'var(--muted)' }}>
											{r.qty} shares • Avg ₹ {fmtINR(r.avg)} • Token {r.token}
										</div>
									</div>
									<div className="sparkline">
										<Sparkline values={sparks[r.token] || []} baseline={r.dayOpen} />
									</div>
								</div>
								<div style={{ textAlign: 'right' }}>
									<div style={{ fontWeight: 600 }}>₹ {fmtINR(r.current)}</div>
									<div style={{ fontSize: 12, color: 'var(--muted)' }}>
										Invested ₹ {fmtINR(r.invested)}
									</div>
									<div style={{ fontSize: 12, marginTop: 4, color: r.totalAbs >= 0 ? 'var(--accent)' : 'var(--danger)' }}>
										Total: {r.totalAbs >= 0 ? '+' : ''}₹ {fmtINR(r.totalAbs)} ({r.totalPct.toFixed(2)}%)
									</div>
									<div style={{ fontSize: 12, color: r.dayAbs >= 0 ? 'var(--accent)' : 'var(--danger)' }}>
										1D: {r.dayAbs >= 0 ? '+' : ''}₹ {fmtINR(r.dayAbs)} ({r.dayPct.toFixed(2)}%)
									</div>
								</div>
							</div>
						))}
					</div>

					<div className="card">
						<div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
							<div className="section-title" style={{ margin: 0 }}>Recent Trades</div>
							<div className="row" style={{ alignItems: 'center', gap: 8 }}>
								<small className="muted">Show</small>
								<select className="select" value={tradesLimit} onChange={(e) => setTradesLimit(e.target.value)}>
									<option value="10">10</option>
									<option value="25">25</option>
									<option value="all">All</option>
								</select>
							</div>
						</div>

						{trades.length === 0 && <small className="muted">No recent trades.</small>}
						{trades.map((t, i) => (
							<div key={i} className="row" style={{ justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px dashed var(--border)' }}>
								<div>
									<b>{t.symbol}</b> <span className="badge">{t.side}</span>
									<div><small className="muted">{fmtIST(t.executed_at)}</small></div>
								</div>
								<div style={{ textAlign: 'right' }}>
									<div>Qty: {t.quantity}</div>
									<div>Price: ₹ {Number(t.price).toFixed(2)}</div>
									<div>Amt: ₹ {Number(t.amount).toFixed(2)}</div>
								</div>
							</div>
						))}
					</div>
				</>
			)}
		</div>
	)
}
