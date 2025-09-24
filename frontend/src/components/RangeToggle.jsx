export const RANGE_OPTS = ['LIVE', '1W', '1M', '6M', '1Y']
export const MODE_OPTS = ['line', 'candlestick']

export default function RangeToggle({ range, setRange, mode, setMode })
{
	return (
		<div className="row" style={{ alignItems: 'center' }}>
			<div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
				{RANGE_OPTS.map(r => (
					<button key={r}
						className={`btn small ${range === r ? 'primary' : ''}`}
						onClick={() => setRange(r)}>
						{r}
					</button>
				))}
			</div>
			<div style={{ flex: 1 }} />
			<div style={{ display: 'flex', gap: 6 }}>
				{MODE_OPTS.map(m => (
					<button key={m}
						className={`btn small ${mode === m ? 'primary' : ''}`}
						onClick={() => setMode(m)}>
						{m}
					</button>
				))}
			</div>
		</div>
	)
}
