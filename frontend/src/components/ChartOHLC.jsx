// Chart.js v4 + chartjs-chart-financial 0.2.1 with adaptive rendering + stats bar
import
{
	CategoryScale,
	Chart as ChartJS,
	Decimation,
	Filler,
	Legend,
	LinearScale,
	LineElement,
	PointElement,
	TimeScale,
	Tooltip,
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Chart } from 'react-chartjs-2'

// Explicit registration for ESM builds
import
{
	CandlestickController,
	CandlestickElement,
	OhlcController,
	OhlcElement,
} from 'chartjs-chart-financial'

ChartJS.register(
	CategoryScale,
	LinearScale,
	TimeScale,
	LineElement,
	PointElement,
	Filler,
	Tooltip,
	Legend,
	Decimation,
	CandlestickController,
	CandlestickElement,
	OhlcController,
	OhlcElement
)

// Observe container width to size bars
function useContainerWidth()
{
	const ref = useRef(null)
	const [w, setW] = useState(0)
	useLayoutEffect(() =>
	{
		if (!ref.current) return
		const ro = new ResizeObserver(entries =>
		{
			const rect = entries?.[0]?.contentRect
			if (rect?.width != null) setW(rect.width)
		})
		ro.observe(ref.current)
		return () => ro.disconnect()
	}, [])
	return [ref, w]
}

// Bucket OHLC into <= maxBars points
function downsampleOHLC(points, maxBars)
{
	const n = points.length
	if (n <= maxBars) return points
	const step = Math.ceil(n / maxBars)
	const out = []
	for (let i = 0; i < n; i += step)
	{
		const bucket = points.slice(i, i + step)
		if (!bucket.length) continue
		const o = bucket[0].o
		const c = bucket[bucket.length - 1].c
		let h = -Infinity, l = Infinity
		for (const b of bucket) { if (b.h > h) h = b.h; if (b.l < l) l = b.l }
		const x = bucket[bucket.length - 1].x
		out.push({ x, o, h, l, c })
	}
	return out
}

// Decide visuals per range
function rangeConfig(range, small)
{
	const R = (range || '').toUpperCase()
	switch (R)
	{
		case 'LIVE': return { unit: 'hour', tooltip: 'MMM d, HH:mm', pxPerBar: 10, minBars: small ? 60 : 90, maxBars: small ? 220 : 320, lineSmooth: 0.15 }
		case '1W': return { unit: 'day', tooltip: 'MMM d', pxPerBar: 10, minBars: small ? 60 : 90, maxBars: small ? 200 : 280, lineSmooth: 0.15 }
		case '1M': return { unit: 'week', tooltip: 'MMM d', pxPerBar: 10, minBars: small ? 60 : 90, maxBars: small ? 200 : 260, lineSmooth: 0.15 }
		case '6M': return { unit: 'month', tooltip: 'MMM yyyy', pxPerBar: 10, minBars: small ? 50 : 80, maxBars: small ? 160 : 220, lineSmooth: 0.15 }
		case '1Y': return { unit: 'month', tooltip: 'MMM yyyy', pxPerBar: 10, minBars: small ? 45 : 70, maxBars: small ? 140 : 200, lineSmooth: 0.05 }
		default: return { unit: 'day', tooltip: 'MMM d', pxPerBar: 10, minBars: small ? 60 : 90, maxBars: small ? 200 : 260, lineSmooth: 0.15 }
	}
}

function inferRange(rows)
{
	if (!rows.length) return '1M'
	const spanMs = rows[rows.length - 1].t - rows[0].t
	const d = spanMs / 86400000
	if (d <= 2) return 'LIVE'
	if (d <= 10) return '1W'
	if (d <= 45) return '1M'
	if (d <= 220) return '6M'
	return '1Y'
}

// Format helpers
function fmtNum(v) { return Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }) }
function fmtVol(v)
{
	if (!v || v <= 0) return null
	if (v >= 1e9) return (v / 1e9).toFixed(2) + 'B'
	if (v >= 1e6) return (v / 1e6).toFixed(2) + 'M'
	if (v >= 1e3) return (v / 1e3).toFixed(2) + 'K'
	return fmtNum(v)
}

export default function ChartOHLC({ series, mode = 'line', small = false, label = 'Price', range })
{
	const [containerRef, containerWidth] = useContainerWidth()

	// Prepare/sort; use numeric timestamps
	const rows = useMemo(() =>
	{
		return (series || [])
			.map(d => ({
				t: new Date(d.t).getTime(),
				o: Number(d.o ?? d.c ?? 0),
				h: Number(d.h ?? d.c ?? 0),
				l: Number(d.l ?? d.c ?? 0),
				c: Number(d.c ?? 0),
				v: d.v != null ? Number(d.v) : null
			}))
			.filter(d => Number.isFinite(d.t) && Number.isFinite(d.c))
			.sort((a, b) => a.t - b.t)
	}, [series])

	// Stats for the visible range
	const stats = useMemo(() =>
	{
		if (!rows.length) return null
		const o = rows[0].o
		const c = rows[rows.length - 1].c
		let h = -Infinity, l = Infinity, vol = 0, anyVol = false
		for (const r of rows)
		{
			if (r.h > h) h = r.h
			if (r.l < l) l = r.l
			if (r.v != null) { vol += r.v; anyVol = true }
		}
		const chg = c - o
		const pct = o ? (chg / o) * 100 : 0
		return { o, h, l, c, chg, pct, vol: anyVol ? vol : null }
	}, [rows])

	const effectiveRange = useMemo(() => range || inferRange(rows), [range, rows])
	const cfg = useMemo(() => rangeConfig(effectiveRange, small), [effectiveRange, small])

	// Build points
	const candleRaw = useMemo(() => rows.map(d => ({ x: d.t, o: d.o, h: d.h, l: d.l, c: d.c })), [rows])
	const linePts = useMemo(() => rows.map(d => ({ x: d.t, y: d.c })), [rows])

	// Candle budget & thickness
	const desiredBars = useMemo(() =>
	{
		const w = containerWidth || (small ? 520 : 1000)
		const est = Math.floor(w / cfg.pxPerBar)
		return Math.max(cfg.minBars, Math.min(cfg.maxBars, est))
	}, [containerWidth, small, cfg])

	const candlePts = useMemo(() => downsampleOHLC(candleRaw, desiredBars), [candleRaw, desiredBars])

	const barThickness = useMemo(() =>
	{
		const w = containerWidth || (small ? 520 : 1000)
		const n = Math.max(1, candlePts.length)
		const t = Math.floor((w / n) * 0.75)
		return Math.max(1, Math.min(small ? 6 : 12, t))
	}, [containerWidth, small, candlePts.length])

	const isCandle = mode === 'candlestick'
	const type = isCandle ? 'candlestick' : 'line'

	const data = useMemo(() =>
	{
		if (isCandle)
		{
			return {
				datasets: [{
					label,
					data: candlePts,
					parsing: false,
					barThickness,
					borderWidth: 1,
					clip: 8,
					color: { up: '#10b981', down: '#ef4444', unchanged: '#94a3b8' },
					borderColor: { up: '#059669', down: '#dc2626', unchanged: '#64748b' },
				}]
			}
		}
		return {
			datasets: [{
				label,
				data: linePts,
				parsing: false,
				borderColor: '#0ea5e9',
				backgroundColor: 'rgba(14,165,233,0.15)',
				tension: cfg.lineSmooth,
				fill: false,
				pointRadius: 0,
				spanGaps: true,
				clip: 8,
			}]
		}
	}, [isCandle, candlePts, barThickness, label, linePts, cfg.lineSmooth])

	const options = useMemo(() => ({
		responsive: true,
		maintainAspectRatio: false,
		normalized: true,
		animation: false,
		plugins: {
			legend: { display: false },
			tooltip: { mode: 'index', intersect: false },
			decimation: !isCandle ? {
				enabled: true,
				algorithm: 'lttb',
				samples: Math.max(cfg.minBars, Math.min(cfg.maxBars,
					Math.floor((containerWidth || (small ? 520 : 1000)) / cfg.pxPerBar) * 1.5)),
			} : undefined,
		},
		scales: {
			x: {
				type: 'time',
				time: { unit: cfg.unit, tooltipFormat: cfg.tooltip },
				ticks: { maxTicksLimit: small ? 5 : 10 },
			},
			y: {
				ticks: { precision: 2 },
			},
		},
		elements: { point: { radius: 0 } },
	}), [isCandle, cfg, containerWidth, small])

	return (
		<div>
			<div ref={containerRef} className={`chart-container ${small ? 'small' : ''}`}>
				<Chart type={type} data={data} options={options} />
			</div>

			{/* Stats footer */}
			{stats && (
				<div className="stats-bar">
					<span className="stat">Open: <b>{fmtNum(stats.o)}</b></span>
					<span className="stat">High: <b>{fmtNum(stats.h)}</b></span>
					<span className="stat">Low: <b>{fmtNum(stats.l)}</b></span>
					<span className="stat">Close: <b>{fmtNum(stats.c)}</b></span>
					<span className={`stat ${stats.chg >= 0 ? 'up' : 'down'}`}>
						Change: <b>{stats.chg >= 0 ? '+' : ''}{fmtNum(stats.chg)}</b> ({(stats.pct).toFixed(2)}%)
					</span>
					{stats.vol != null && <span className="stat">Vol: <b>{fmtVol(stats.vol)}</b></span>}
					<span className="stat pill">{effectiveRange}</span>
				</div>
			)}
		</div>
	)
}
