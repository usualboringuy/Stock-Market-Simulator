import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

function fmtINR(n)
{
	return Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
}
function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x }

export default function Portfolio()
{
	const [pf, setPf] = useState(null)
	const [trades, setTrades] = useState([])
	const [loading, setLoading] = useState(true)

	// Add funds
	const [amt, setAmt] = useState('')
	const [msg, setMsg] = useState('')
	const [err, setErr] = useState('')

	// Holdings rows computed from positions + candles
	const [rows, setRows] = useState([]) // [{token,symbol,qty,avg,invested,lastClose,prevClose,current,dayAbs,dayPct,totalAbs,totalPct}]
	const [summary, setSummary] = useState(null) // {value, invested, dayAbs, dayPct, totalAbs, totalPct}
	const navigate = useNavigate()

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

			// Build holdings from positions
			const pos = pfData?.positions || {}
			const tokens = Object.keys(pos).filter(t => (pos[t]?.quantity || 0) > 0)
			if (tokens.length === 0)
			{
				setRows([])
				setSummary({ value: 0, invested: 0, dayAbs: 0, dayPct: 0, totalAbs: 0, totalPct: 0 })
				return
			}

			const now = new Date()
			const from = addDays(now, -45)

			// Fetch last ~45 days daily candles for each token (for lastClose & prevClose)
			const tokenData = {}
			await Promise.all(tokens.map(async (tok) =>
			{
				try
				{
					const res = await api.get('/api/candles', {
						params: { token: tok, interval: 'ONE_DAY', from: from.toISOString(), to: now.toISOString() }
					})
					const series = res.data?.series || []
					tokenData[tok] = series
				} catch
				{
					tokenData[tok] = []
				}
			}))

			// Build rows and compute summary aggregations
			const built = []
			let sumCurrent = 0
			let sumPrev = 0
			let sumInvested = 0

			for (const tok of tokens)
			{
				const p = pos[tok]
				const qty = Number(p.quantity || 0)
				const avg = Number(p.avg_price || 0)
				const invested = qty * avg
				const series = tokenData[tok] || []
				const n = series.length
				const lastClose = n >= 1 ? Number(series[n - 1].c) : avg
				const prevClose = n >= 2 ? Number(series[n - 2].c) : lastClose

				const current = qty * lastClose
				const prev = qty * prevClose

				const dayAbs = current - prev
				const dayPct = prev > 0 ? (dayAbs / prev) * 100 : 0

				const totalAbs = current - invested
				const totalPct = invested > 0 ? (totalAbs / invested) * 100 : 0

				built.push({
					token: tok,
					symbol: p.symbol,
					qty, avg, invested,
					lastClose, prevClose, current,
					dayAbs, dayPct, totalAbs, totalPct
				})

				sumCurrent += current
				sumPrev += prev
				sumInvested += invested
			}

			const dayAbs = sumCurrent - sumPrev
			const dayPct = sumPrev > 0 ? (dayAbs / sumPrev) * 100 : 0
			const totalAbs = sumCurrent - sumInvested
			const totalPct = sumInvested > 0 ? (totalAbs / sumInvested) * 100 : 0

			setRows(built.sort((a, b) => b.current - a.current))
			setSummary({
				value: sumCurrent,
				invested: sumInvested,
				dayAbs, dayPct, totalAbs, totalPct
			})
		} finally
		{
			setLoading(false)
		}
	}

	useEffect(() =>
	{
		let mounted = true
			; (async () => { if (mounted) await reload() })()
		return () => { mounted = false }
	}, [])

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
						<div><small className="muted">Last updated: {pf.updated_at}</small></div>
					</div>

					{/* Holdings Summary (positions only) */}
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

					{/* Holdings list */}
					<div className="card">
						<div className="section-title">Stocks you hold</div>
						{rows.length === 0 && <small className="muted">No positions.</small>}
						{rows.map((r) => (
							<div
								key={r.token}
								className="row"
								onClick={() => navigate(`/stock/${encodeURIComponent(r.symbol)}`)}
								style={{ justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px dashed var(--border)', cursor: 'pointer' }}
								title="Open stock details"
							>
								<div>
									<div style={{ fontWeight: 600 }}>{r.symbol}</div>
									<div style={{ fontSize: 12, color: 'var(--muted)' }}>
										{r.qty} shares • Avg ₹ {fmtINR(r.avg)} • Token {r.token}
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

					{/* Recent trades (unchanged) */}
					<div className="card">
						<div className="section-title">Recent Trades</div>
						{trades.length === 0 && <small className="muted">No recent trades.</small>}
						{trades.map((t, i) => (
							<div key={i} className="row" style={{ justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px dashed var(--border)' }}>
								<div>
									<b>{t.symbol}</b> <span className="badge">{t.side}</span>
									<div><small className="muted">{t.executed_at}</small></div>
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
