import axios from 'axios'
import { getCookie } from '../utils/cookies'

const api = axios.create({
	baseURL: '',
	withCredentials: true
})

api.interceptors.request.use((config) =>
{
	const method = (config.method || 'get').toLowerCase()
	if (['post', 'put', 'patch', 'delete'].includes(method))
	{
		const csrf = getCookie('app_csrf')
		if (csrf)
		{
			config.headers['X-CSRF-Token'] = csrf
		}
	}
	return config
})

export default api
