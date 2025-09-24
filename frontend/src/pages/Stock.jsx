import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api/client'
import ChartOHLC from '../components/ChartOHLC'
import RangeToggle from '../components/RangeToggle'
import { useAuth } from '../context/AuthContext'

function rangeToDays(range)
{
	switch (range)
	{
		case 'LIVE': return 1
		case '1W': return 7
		case '1M': return 30
		case '6M': return 180
		case '1Y': return 365
		default: return 30
	}
}

export default function Stock()
{
	const { symbol } = useParams()
	const [range, setRange] = useState('1M')
	const [mode, setMode] = useState('line')
	const [series, setSeries] = useState([])
	const [loading, setLoading] = useState(false)
	const [err, setErr] = useState('')
	const [side, setSide] = useState('BUY')
	const [qty, setQty] = useState(1)
	const { user } = useAuth()

	useEffect(() =>
	{
		let mounted = true
		const load = async () =>
		{
			setLoading(true); setErr('')
			try
			{
				const to = new Date()
				let from = new Date(to)
				if (range === 'LIVE')
				{
					from.setHours(9, 0, 0, 0)
				} else
				{
					from.setDate(from.getDate() - rangeToDays(range))
				}
				const params = {
					symbol,
					interval: range === 'LIVE' ? 'ONE_MINUTE' : 'ONE_DAY',
					from: from.toISOString(),
					to: to.toISOString()
				}
				const res = await api.get('/api/candles', { params })
				if (mounted) setSeries(res.data?.series || [])
			} catch (e)
			{
				if (mounted) setErr(e?.response?.data?.detail || 'Failed to load candles')
			} finally
			{
				if (mounted) setLoading(false)
			}
		}
		load()
		return () => { mounted = false }
	}, [symbol, range])

	const trade = async () =>
	{
		try
		{
			await api.post('/api/trades', { symbol, side, quantity: Number(qty) })
			alert('Trade executed')
		} catch (e)
		{
			alert(e?.response?.data?.detail || 'Trade failed')
		}
	}

	const summary = useMemo(() =>
	{
		if (!series || series.length === 0) return null
		const first = series[0].c
		const last = series[series.length - 1].c
		const pct = first > 0 ? (last / first) - 1 : 0
		return { first, last, pct }
	}, [series])

	return (
		<div className="grid">
			<div className="row" style={{ alignItems: 'baseline' }}>
				<h2 style={{ marginRight: 12 }}>{symbol}</h2>
				{summary && (
					<div style={{ color: summary.pct >= 0 ? 'var(--accent)' : 'var(--danger)' }}>
						{(summary.pct * 100).toFixed(2)}%
					</div>
				)}
			</div>
			<RangeToggle range={range} setRange={setRange} mode={mode} setMode={setMode} />
			{loading && <div className="card">Loading chart…</div>}
			{!loading && err && <div className="card" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>{err}</div>}
			{!loading && !err && (
				<div className="card">
					<ChartOHLC series={series} mode={mode} range={range} label={symbol} />
				</div>
			)}
			<div className="card">
				<div className="section-title">Trade</div>
				{!user && <small className="muted">Login to place virtual trades.</small>}
				<div className="row">
					<select className="select" value={side} onChange={(e) => setSide(e.target.value)}>
						<option>BUY</option>
						<option>SELL</option>
					</select>
					<input className="input" type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} />
					<button className="btn primary" disabled={!user} onClick={trade}>Submit</button>
				</div>
			</div>
		</div>
	)
}
