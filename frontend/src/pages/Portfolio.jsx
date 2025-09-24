import { useEffect, useMemo, useState } from 'react'
import api from '../api/client'
import ChartOHLC from '../components/ChartOHLC'

function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x }

export default function Portfolio()
{
	const [pf, setPf] = useState(null)
	const [trades, setTrades] = useState([])
	const [loading, setLoading] = useState(true)
	const [equity, setEquity] = useState([]) // [{t, v}]

	useEffect(() =>
	{
		let mounted = true
		const load = async () =>
		{
			setLoading(true)
			try
			{
				const [pfRes, trRes] = await Promise.all([
					api.get('/api/portfolio'),
					api.get('/api/trades/recent', { params: { limit: 20 } })
				])
				if (!mounted) return
				setPf(pfRes.data)
				setTrades(trRes.data || [])

				// Equity curve (approx): current cash + sum(qty * price(t)) for last 180 days
				const positions = pfRes.data?.positions || {}
				const tokens = Object.keys(positions).filter(t => positions[t].quantity > 0)
				const to = new Date()
				const from = addDays(to, -180)
				const candlesByToken = {}
				await Promise.all(tokens.map(async (tok) =>
				{
					try
					{
						const res = await api.get('/api/candles', {
							params: { token: tok, interval: 'ONE_DAY', from: from.toISOString(), to: to.toISOString() }
						})
						candlesByToken[tok] = (res.data?.series || []).map(d => ({ t: new Date(d.t), c: d.c }))
					} catch
					{
						candlesByToken[tok] = []
					}
				}))
				// Build union of dates, forward-fill last close
				const allDatesSet = new Set()
				Object.values(candlesByToken).forEach(arr => arr.forEach(d => allDatesSet.add(d.t.toDateString())))
				const allDates = Array.from(allDatesSet).map(s => new Date(s)).sort((a, b) => a - b)
				const lastClose = {}
				const series = allDates.map(date =>
				{
					let val = pfRes.data.cash
					for (const tok of tokens)
					{
						const qty = positions[tok].quantity
						const arr = candlesByToken[tok]
						const hit = arr.find(d => d.t.toDateString() === date.toDateString())
						if (hit) lastClose[tok] = hit.c
						if (lastClose[tok] != null) val += qty * lastClose[tok]
					}
					return { t: date.toISOString(), v: val }
				})
				if (mounted) setEquity(series)
			} finally
			{
				if (mounted) setLoading(false)
			}
		}
		load()
		return () => { mounted = false }
	}, [])

	const equityLine = useMemo(() =>
	{
		return equity.map(d => ({ t: d.t, o: d.v, h: d.v, l: d.v, c: d.v }))
	}, [equity])

	return (
		<div className="grid">
			<h2>My Portfolio</h2>
			{loading && <div className="card">Loading…</div>}
			{!loading && pf && (
				<>
					<div className="card">
						<div className="row" style={{ justifyContent: 'space-between' }}>
							<div>
								<div><b>Cash:</b> ₹ {pf.cash.toFixed(2)}</div>
								<div><b>Realized P&L:</b> {pf.realized_pl >= 0 ? '+' : ''}{pf.realized_pl.toFixed(2)}</div>
							</div>
							<div><small className="muted">Last updated: {pf.updated_at}</small></div>
						</div>
					</div>

					<div className="card">
						<div className="section-title">Equity Curve</div>
						{equity.length === 0 ? <small className="muted">No equity history available.</small> :
							<ChartOHLC series={equityLine} mode="line" label="Equity" />
						}
					</div>

					<div className="grid cols-2">
						<div className="card">
							<div className="section-title">Positions</div>
							{Object.keys(pf.positions || {}).length === 0 && <small className="muted">No positions.</small>}
							{Object.entries(pf.positions || {}).map(([tok, p]) => (
								<div key={tok} className="row" style={{ justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px dashed var(--border)' }}>
									<div>
										<b>{p.symbol}</b>
										<div><small className="muted">Token: {tok}</small></div>
									</div>
									<div style={{ textAlign: 'right' }}>
										<div>Qty: {p.quantity}</div>
										<div>Avg: ₹ {Number(p.avg_price).toFixed(2)}</div>
									</div>
								</div>
							))}
						</div>
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
					</div>
				</>
			)}
		</div>
	)
}
