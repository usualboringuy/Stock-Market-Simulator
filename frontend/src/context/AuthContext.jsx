import { createContext, useContext, useEffect, useState } from 'react'
import api from '../api/client'

const AuthCtx = createContext(null)

export function AuthProvider({ children })
{
	const [user, setUser] = useState(null)
	const [loading, setLoading] = useState(true)

	useEffect(() =>
	{
		let mounted = true
		api.get('/api/auth/me')
			.then((res) => mounted && setUser(res.data))
			.catch(() => mounted && setUser(null))
			.finally(() => mounted && setLoading(false))
		return () => { mounted = false }
	}, [])

	const login = async (username, password) =>
	{
		const res = await api.post('/api/auth/login', { username, password })
		setUser(res.data)
		return res.data
	}
	const signup = async (username, password) =>
	{
		const res = await api.post('/api/auth/signup', { username, password })
		setUser(res.data)
		return res.data
	}
	const logout = async () =>
	{
		await api.post('/api/auth/logout')
		setUser(null)
	}

	return (
		<AuthCtx.Provider value={{ user, loading, login, signup, logout }}>
			{children}
		</AuthCtx.Provider>
	)
}

export function useAuth()
{
	return useContext(AuthCtx)
}
