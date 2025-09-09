const API_BASE = process.env.REACT_APP_API_BASE_URL || ''

export async function fetchTopStocks()
{
	const response = await fetch(`${API_BASE}/api/top-stocks`)
	if (!response.ok)
	{
		throw new Error('Failed to fetch top stocks')
	}
	return response.json()
}
