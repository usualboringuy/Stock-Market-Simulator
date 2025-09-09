import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function TopStocksChart({ data })
{
	return (
		<ResponsiveContainer width="100%" height={100}>
			<LineChart data={data}>
				<XAxis dataKey="date" hide />
				<YAxis domain={['auto', 'auto']} hide />
				<Tooltip />
				<Line type="monotone" dataKey="close" stroke="#8884d8" dot={false} strokeWidth={2} />
			</LineChart>
		</ResponsiveContainer>
	)
}
