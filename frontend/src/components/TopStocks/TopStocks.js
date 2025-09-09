import { useEffect, useState } from 'react'
import { fetchTopStocks } from '../../api/stockApi'
import ErrorMsg from '../common/ErrorMsg'
import Loader from '../common/Loader'
import TopStocksChart from './TopStocksChart'

function TopStocks()
{
	const [stocks, setStocks] = useState([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)

	useEffect(() =>
	{
		fetchTopStocks()
			.then(data => setStocks(data))
			.catch(err => setError(err.message))
			.finally(() => setLoading(false))
	}, [])

	if (loading) return <Loader />
	if (error) return <ErrorMsg message={error} />

	return (
		<div>
			<h2>Top 10 Performing Stocks</h2>
			<table style={{ width: '100%', borderCollapse: 'collapse' }}>
				<thead>
					<tr>
						<th>Symbol</th>
						<th>Price</th>
						<th>Change (%)</th>
						<th>Volume</th>
						<th>Recent Trend</th>
					</tr>
				</thead>
				<tbody>
					{stocks.map(stock =>
					{
						const chartData = stock.historical_ohlc
							? stock.historical_ohlc.map(item => ({
								date: item.DATE && (item.DATE.$date || item.DATE)
									? new Date(item.DATE.$date || item.DATE).toISOString().slice(0, 10)
									: '',
								close: Number(item.CLOSE ?? 0),
							}))
							: [];
						console.log('Chart data for', stock.symbol, chartData);
						return (
							<tr key={stock.symbol} style={{ borderBottom: '1px solid #ccc' }}>
								<td>{stock.symbol}</td>
								<td>{stock.lastPrice}</td>
								<td style={{ color: stock.pChange >= 0 ? 'green' : 'red' }}>
									{stock.pChange.toFixed(2)}
								</td>
								<td>{stock.live_volume}</td>
								<td style={{ width: 300, height: 100, padding: '5px' }}>
									{chartData.length > 0 ? (
										<TopStocksChart data={chartData} />
									) : (
										<span style={{ fontSize: 12, color: '#888' }}>No Data</span>
									)}
								</td>
							</tr>
						)
					})}
				</tbody>
			</table>
		</div>
	)
}

export default TopStocks
