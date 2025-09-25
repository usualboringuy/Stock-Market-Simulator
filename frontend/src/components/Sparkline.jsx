import
{
	CategoryScale,
	Chart as ChartJS,
	Legend,
	LinearScale,
	LineElement,
	PointElement,
	Tooltip
} from 'chart.js'
import { useMemo } from 'react'
import { Chart } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, LineElement, PointElement, Tooltip, Legend)

export default function Sparkline({ values = [], width = 120, height = 28 })
{
	const sanitized = Array.isArray(values)
		? values.map(v => Number(v)).filter(v => Number.isFinite(v))
		: []

	const color = useMemo(() =>
	{
		if (sanitized.length < 2) return '#94a3b8'
		return sanitized[sanitized.length - 1] >= sanitized[0] ? '#10b981' : '#ef4444'
	}, [sanitized])

	const data = useMemo(() => ({
		labels: sanitized.map((_, i) => i),
		datasets: [{
			data: sanitized,
			borderColor: color,
			backgroundColor: 'transparent',
			borderWidth: 1.5,
			tension: 0.25,
			pointRadius: 0
		}]
	}), [sanitized, color])

	const options = {
		responsive: false,
		maintainAspectRatio: false,
		plugins: { legend: { display: false }, tooltip: { enabled: false } },
		scales: { x: { display: false }, y: { display: false } },
		elements: { point: { radius: 0 } },
		animation: false
	}

	return (
		<div style={{ width, height, pointerEvents: 'none' }}>
			{sanitized.length >= 2 ? (
				<Chart type="line" data={data} options={options} width={width} height={height} />
			) : (
				<div style={{ width, height }} />
			)}
		</div>
	)
}
