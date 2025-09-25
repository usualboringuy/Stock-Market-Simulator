import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import Sparkline from '../components/Sparkline'

function fmtINR(n)
{
	return Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
}
function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x }
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

	// Holdings rows (positions only) and summary
	const [rows, setRows] = useState([])  // [{token,symbol,qty,avg,invested,prevClose,lastClose,current,dayAbs,dayPct,totalAbs,totalPct}]
	const [summary, setSummary] = useState(null)
	const [sparks, setSparks] = useState({}) // token -> [values]

	// Add funds
	const [amt, setAmt] = useState('')
	const [msg, setMsg] = useState('')
	const [err, setErr] = useState('')

	// Sorting
	const [sortBy, setSortBy] = useState('value')
	const [sortDir, setSortDir] = useState('desc')

	// Live
	const [marketOpen, setMarketOpen] = useState(false)
	const [liveNote, setLiveNote] = useState('')
	const priceTimerRef = useRef(null)
	const healthTimerRef = useRef(null)

	const navigate = useNavigate()

	function buildRowsAndSummary(baseRows, liveMap = null, sparkMap = null)
	{
		if (!Array.isArray(baseRows) || baseRows.length === 0)
		{
			setRows([])
			if (sparkMap) setSparks(sparkMap)
			setSummary({ value: 0, invested: 0, dayAbs: 0, dayPct: 0, totalAbs: 0, totalPct: 0 })
			return
		}
		let sumCurrent = 0, sumPrev = 0, sumInvested = 0
		const updated = baseRows.map(r =>
		{
			const priceNow = (liveMap && liveMap[r.token] != null) ? Number(liveMap[r.token]) : Number(r.lastClose)
			const current = r.qty * priceNow
			const prev = r.qty * r.prevClose
			const dayAbs = current - prev
			const dayPct = prev > 0 ? (dayAbs / prev) * 100 : 0
			const totalAbs = current - r.invested
			const totalPct = r.invested > 0 ? (totalAbs / r.invested) * 100 : 0
			sumCurrent += current
			sumPrev += prev
			sumInvested += r.invested
			return { ...r, lastClose: priceNow, current, dayAbs, dayPct, totalAbs, totalPct }
		})
		setRows(updated)
		if (sparkMap) setSparks(sparkMap)
		const dayAbs = sumCurrent - sumPrev
		const dayPct = sumPrev > 0 ? (dayAbs / sumPrev) * 100 : 0
		const totalAbs = sumCurrent - sumInvested
		const totalPct = sumInvested > 0 ? (totalAbs / sumInvested) * 100 : 0
		setSummary({ value: sumCurrent, invested: sumInvested, dayAbs, dayPct, totalAbs, totalPct })
	}

	const reload = async () =>
	{
		setLoading(true)
		try
		{
			const [pfRes, trRes] = await Promise.all([
				api.get('/api/portfolio'),
				api.get('/api/trades/recent', { params: { limit: 20 } })
			])
			const pfData = pfRes.data
			setPf(pfData)
			setTrades(trRes.data || [])

			const pos = pfData?.positions || {}
			const tokens = Object.keys(pos).filter(t => (pos[t]?.quantity || 0) > 0)
			if (tokens.length === 0)
			{
				buildRowsAndSummary([])
				return
			}

			// Baseline: daily prev/last close + seed sparkline from last 40 daily closes
			const now = new Date()
			const from = addDays(now, -60)
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

			const sparkMap = {}
			const baseRows = tokens.map(tok =>
			{
				const p = pos[tok]
				const qty = Number(p.quantity || 0)
				const avg = Number(p.avg_price || 0)
				const invested = qty * avg
				const series = seriesMap[tok] || []
				const n = series.length
				const lastCloseDaily = n >= 1 ? Number(series[n - 1].c) : avg
				const prevClose = n >= 2 ? Number(series[n - 2].c) : lastCloseDaily
				// Seed sparkline with last 40 daily closes
				sparkMap[tok] = series.slice(-40).map(s => Number(s.c)).filter(Number.isFinite)
				return {
					token: tok, symbol: p.symbol, qty, avg, invested,
					prevClose, lastClose: lastCloseDaily,
					current: qty * lastCloseDaily,
					dayAbs: (qty * lastCloseDaily) - (qty * prevClose),
					dayPct: prevClose > 0 ? ((lastCloseDaily - prevClose) / prevClose) * 100 : 0,
					totalAbs: (qty * lastCloseDaily) - invested,
					totalPct: invested > 0 ? (((qty * lastCloseDaily) - invested) / invested) * 100 : 0
				}
			})

			buildRowsAndSummary(baseRows, null, sparkMap)
		} finally
		{
			setLoading(false)
		}
	}

	const checkMarket = async () =>
	{
		try
		{
			const res = await api.get('/api/health')
			const open = !!res.data?.market_open
			setMarketOpen(open)
			setLiveNote(open ? 'Live: auto-refreshing prices' : '')
			return open
		} catch
		{
			setMarketOpen(false)
			setLiveNote('')
			return false
		}
	}

	const pollLive = async () =>
	{
		try
		{
			if (!marketOpen || rows.length === 0) return
			const tokens = rows.map(r => r.token)
			const res = await api.post('/api/prices/live', { tokens, minutes: 15, include_series: true, series_points: 40 })
			const prices = res.data?.prices || {}

			const liveMap = {}
			const sparkMap = { ...sparks }
			for (const tok of tokens)
			{
				const item = prices[tok]
				if (!item) continue
				if (item.last != null) liveMap[tok] = Number(item.last)
				if (Array.isArray(item.series) && item.series.length >= 2)
				{
					sparkMap[tok] = item.series.map(p => Number(p.c)).filter(Number.isFinite)
				}
			}
			buildRowsAndSummary(rows, Object.keys(liveMap).length ? liveMap : null, sparkMap)
		} catch
		{
			// ignore
		}
	}

	const deposit = async () =>
	{
		setMsg(''); setErr('')
		const value = Number(amt)
		if (!Number.isFinite(value) || value <= 0)
		{
			setErr('Enter a positive amount'); return
		}
		try
		{
			const res = await api.post('/api/portfolio/deposit', { amount: value })
			setPf(res.data)
			setMsg(`Added ₹ ${value.toFixed(2)} to your cash`)
			setAmt('')
		} catch (e)
		{
			const m = e?.response?.data?.detail || 'Deposit failed'
			setErr(String(m))
		}
	}

	// Effects
	useEffect(() =>
	{
		let mounted = true
			; (async () => { if (mounted) await reload() })()
		return () => { mounted = false }
	}, [])

	useEffect(() =>
	{
		let stopped = false
		const start = async () =>
		{
			const open = await checkMarket()
			if (stopped) return

			if (open)
			{
				if (priceTimerRef.current) clearInterval(priceTimerRef.current)
				priceTimerRef.current = setInterval(pollLive, 5000)
				pollLive()
			} else
			{
				if (priceTimerRef.current) clearInterval(priceTimerRef.current)
				priceTimerRef.current = null
			}

			if (healthTimerRef.current) clearInterval(healthTimerRef.current)
			healthTimerRef.current = setInterval(async () =>
			{
				const nowOpen = await checkMarket()
				if (!nowOpen && priceTimerRef.current)
				{
					clearInterval(priceTimerRef.current); priceTimerRef.current = null
				} else if (nowOpen && !priceTimerRef.current)
				{
					priceTimerRef.current = setInterval(pollLive, 5000); pollLive()
				}
			}, 60000)
		}
		start()
		return () =>
		{
			stopped = true
			if (priceTimerRef.current) clearInterval(priceTimerRef.current)
			if (healthTimerRef.current) clearInterval(healthTimerRef.current)
			priceTimerRef.current = null
			healthTimerRef.current = null
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [rows.length])

	// Sorting
	const displayRows = useMemo(() =>
	{
		const arr = [...rows]
		const dir = sortDir === 'asc' ? 1 : -1
		arr.sort((a, b) =>
		{
			if (sortBy === 'symbol') return dir * String(a.symbol).localeCompare(String(b.symbol))
			const map = { value: 'current', day: 'dayAbs', total: 'totalAbs' }
			const key = map[sortBy] || 'current'
			return dir * (a[key] - b[key])
		})
		return arr
	}, [rows, sortBy, sortDir])

	return (
		<div className="grid">
			<h2>My Portfolio</h2>

			{loading && <div className="card">Loading…</div>}

			{!loading && pf && (
				<>
					{/* Cash + Add funds */}
					<div className="card">
						<div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
							<div>
								<div><b>Cash:</b> ₹ {fmtINR(pf.cash)}</div>
								<div><b>Realized P&L:</b> {pf.realized_pl >= 0 ? '+' : ''}{fmtINR(pf.realized_pl)}</div>
								<div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
									Last updated: {fmtIST(pf.updated_at)}
								</div>
								{liveNote && <div style={{ fontSize: 12, color: '#0ea5e9', marginTop: 2 }}>{liveNote}</div>}
							</div>
							<div>
								<div className="row" style={{ alignItems: 'center' }}>
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
								</div>
								{(msg || err) && (
									<div style={{ marginTop: 6, fontSize: 12, color: err ? 'var(--danger)' : 'var(--accent)' }}>
										{err || msg}
									</div>
								)}
							</div>
						</div>
					</div>

					{/* Holdings Summary */}
					<div className="card">
						<div className="section-title">Holdings</div>
						{summary ? (
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
						) : (
							<small className="muted">No holdings.</small>
						)}
					</div>

					{/* Holdings list + sorting + sparklines */}
					<div className="card">
						<div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
							<div className="section-title" style={{ margin: 0 }}>Stocks you hold</div>
							<div className="row" style={{ alignItems: 'center', gap: 8 }}>
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
							<div
								key={r.token}
								className="row"
								style={{ justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px dashed var(--border)' }}
							>
								<div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
									<div onClick={() => navigate(`/stock/${encodeURIComponent(r.symbol)}`)} style={{ cursor: 'pointer' }}>
										<div style={{ fontWeight: 600 }}>{r.symbol}</div>
										<div style={{ fontSize: 12, color: 'var(--muted)' }}>
											{r.qty} shares • Avg ₹ {fmtINR(r.avg)} • Token {r.token}
										</div>
									</div>
									<div className="sparkline">
										<Sparkline values={sparks[r.token] || []} />
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

					{/* Recent trades with readable time */}
					<div className="card">
						<div className="section-title">Recent Trades</div>
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
