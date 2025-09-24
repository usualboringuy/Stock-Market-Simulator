import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import ChartOHLC from '../components/ChartOHLC'
import RangeToggle from '../components/RangeToggle'

const CURATED_SYMBOLS = ['Nifty 50', 'Nifty Bank', 'Nifty IT', 'Nifty Fin Service']

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

export default function Dashboard()
{
	const [range, setRange] = useState('1M')
	const [mode, setMode] = useState('line')
	const [cards, setCards] = useState([]) // [{symbol, series, returnPct}]
	const [loading, setLoading] = useState(false)
	const navigate = useNavigate()

	useEffect(() =>
	{
		let mounted = true
		const fetchAll = async () =>
		{
			setLoading(true)
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
				const reqs = CURATED_SYMBOLS.map(async (sym) =>
				{
					try
					{
						const params = {
							symbol: sym,
							interval: range === 'LIVE' ? 'ONE_MINUTE' : 'ONE_DAY',
							from: from.toISOString(),
							to: to.toISOString()
						}
						const res = await api.get('/api/candles', { params })
						const series = res.data?.series || []
						let ret = 0
						if (series.length >= 2)
						{
							const first = series[0].c
							const last = series[series.length - 1].c
							if (first > 0) ret = (last / first) - 1
						}
						return { symbol: sym, series, returnPct: ret }
					} catch
					{
						return { symbol: sym, series: [], returnPct: -Infinity }
					}
				})
				const out = (await Promise.all(reqs))
					.filter(c => c.series.length > 0)
					.sort((a, b) => b.returnPct - a.returnPct)
					.slice(0, 5)
				if (mounted) setCards(out)
			} finally
			{
				if (mounted) setLoading(false)
			}
		}
		fetchAll()
		return () => { mounted = false }
	}, [range])

	return (
		<div className="grid">
			<div className="row" style={{ alignItems: 'baseline' }}>
				<h2 style={{ marginRight: 12 }}>Dashboard</h2>
			</div>
			<RangeToggle range={range} setRange={setRange} mode={mode} setMode={setMode} />
			<div className="grid cols-2">
				{loading && <div className="card">Loading Data…</div>}
				{!loading && cards.length === 0 && <div className="card">No data for symbols in your CSV.</div>}
				{cards.map((c) => (
					<div key={c.symbol} className="card" onClick={() => navigate(`/stock/${encodeURIComponent(c.symbol)}`)} style={{ cursor: 'pointer' }}>
						<div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
							<div><b>{c.symbol}</b></div>
							<div style={{ color: c.returnPct >= 0 ? 'var(--accent)' : 'var(--danger)' }}>
								{(c.returnPct * 100).toFixed(2)}%
							</div>
						</div>
						<ChartOHLC series={c.series} mode={mode} range={range} small label={c.symbol} />
					</div>
				))}
			</div>
		</div>
	)
}
