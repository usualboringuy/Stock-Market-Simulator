// Chart.js v4 + chartjs-chart-financial 0.2.1
// Line color across ALL ranges = compare current (last close) vs range open (first bar's open)
// Green if current >= rangeOpen, Red otherwise. Live marker matches the line color.
// Stats row unchanged.
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
import
{
	CandlestickController,
	CandlestickElement,
	OhlcController,
	OhlcElement,
} from 'chartjs-chart-financial'
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Chart } from 'react-chartjs-2'

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

// Your original range visuals (unit/tooltip only drive axes/ticks)
function rangeConfig(range, small)
{
	const R = (range || '').toUpperCase()
	switch (R)
	{
		case 'LIVE': return { unit: 'hour', tooltip: 'HH:mm', pxPerBar: 10, minBars: small ? 60 : 90, maxBars: small ? 220 : 320, lineSmooth: 0.15 }
		case '1D': return { unit: 'day', tooltip: 'MMM d', pxPerBar: 10, minBars: small ? 60 : 90, maxBars: small ? 200 : 280, lineSmooth: 0.15 }
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

	// Prepare series
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

	// Summary (as you had)
	const summary = useMemo(() =>
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

	// Points
	const candleRaw = useMemo(() => rows.map(d => ({ x: d.t, o: d.o, h: d.h, l: d.l, c: d.c })), [rows])
	const linePts = useMemo(() => rows.map(d => ({ x: d.t, y: d.c })), [rows])

	// Key logic: compare current (last close) to rangeOpen (first bar's open)
	const { rangeOpen, currentPrice } = useMemo(() =>
	{
		if (!rows.length) return { rangeOpen: null, currentPrice: null }
		return { rangeOpen: rows[0].o, currentPrice: rows[rows.length - 1].c }
	}, [rows])

	const { lineColor, lineFill } = useMemo(() =>
	{
		if (!Number.isFinite(rangeOpen) || !Number.isFinite(currentPrice))
		{
			return { lineColor: '#0ea5e9', lineFill: 'rgba(14,165,233,0.15)' } // default
		}
		const up = currentPrice >= rangeOpen
		return up
			? { lineColor: '#10b981', lineFill: 'rgba(16,185,129,0.15)' }   // green
			: { lineColor: '#ef4444', lineFill: 'rgba(239,68,68,0.15)' }   // red
	}, [rangeOpen, currentPrice])

	// Candles density & thickness
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

	// Live marker (only in LIVE), match color
	const markerPoint = useMemo(() =>
	{
		if (!rows.length || effectiveRange !== 'LIVE') return null
		const last = rows[rows.length - 1]
		return { x: last.t, y: last.c }
	}, [rows, effectiveRange])

	const liveMarkerDataset = markerPoint ? [{
		type: 'line',
		label: 'live-marker',
		data: [markerPoint],
		parsing: false,
		showLine: false,
		pointRadius: 4,
		pointHoverRadius: 6,
		pointBackgroundColor: lineColor,
		pointBorderColor: lineColor,
		borderColor: lineColor
	}] : []

	const data = useMemo(() =>
	{
		if (isCandle)
		{
			return {
				datasets: [
					{
						label,
						data: candlePts,
						parsing: false,
						barThickness,
						borderWidth: 1,
						clip: 8,
						color: { up: '#10b981', down: '#ef4444', unchanged: '#94a3b8' },
						borderColor: { up: '#059669', down: '#dc2626', unchanged: '#64748b' },
					},
					...liveMarkerDataset
				]
			}
		}
		return {
			datasets: [
				{
					label,
					data: linePts,
					parsing: false,
					borderColor: lineColor,
					backgroundColor: lineFill,
					tension: cfg.lineSmooth,
					fill: false,
					pointRadius: 0,
					spanGaps: true,
					clip: 8,
				},
				...liveMarkerDataset
			]
		}
	}, [isCandle, candlePts, barThickness, label, linePts, cfg.lineSmooth, liveMarkerDataset, lineColor, lineFill])

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
			y: { ticks: { precision: 2 } },
		},
		elements: { point: { radius: 0 } },
	}), [isCandle, cfg, containerWidth, small])

	return (
		<div>
			<div ref={containerRef} className={`chart-container ${small ? 'small' : ''}`}>
				<Chart type={type} data={data} options={options} />
			</div>

			{summary && (
				<div className="stats-bar">
					<span className="stat" style={{ color: "#0ea5e9" }}>Current: <b>{fmtNum(currentPrice ?? summary.c)}</b></span>
					<span className="stat">Open: <b>{fmtNum(summary.o)}</b></span>
					<span className="stat">High: <b>{fmtNum(summary.h)}</b></span>
					<span className="stat">Low: <b>{fmtNum(summary.l)}</b></span>
					<span className="stat">Close: <b>{fmtNum(summary.c)}</b></span>
					<span className={`stat ${summary.chg >= 0 ? 'up' : 'down'}`}>
						Change: <b>{summary.chg >= 0 ? '+' : ''}{fmtNum(summary.chg)}</b> ({(summary.pct).toFixed(2)}%)
					</span>
					{summary.vol != null && <span className="stat">Vol: <b>{fmtNum(summary.vol)}</b></span>}
					<span className="stat pill">{effectiveRange}</span>
				</div>
			)}
		</div>
	)
}
