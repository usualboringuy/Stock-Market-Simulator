import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Auth({ mode = 'login' })
{
	const isLogin = mode === 'login'
	const [username, setUsername] = useState('')
	const [password, setPassword] = useState('')
	const [err, setErr] = useState('')
	const { login, signup } = useAuth()
	const navigate = useNavigate()

	const submit = async (e) =>
	{
		e.preventDefault()
		setErr('')
		try
		{
			if (isLogin) await login(username, password)
			else await signup(username, password)
			navigate('/')
		} catch (e2)
		{
			const msg = e2?.response?.data?.detail || 'Request failed'
			setErr(msg)
		}
	}

	return (
		<div className="grid" style={{ maxWidth: 420, margin: '24px auto' }}>
			<h2>{isLogin ? 'Login' : 'Signup'}</h2>
			<form className="grid" onSubmit={submit}>
				<label>Username</label>
				<input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
				<label>Password</label>
				<input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
				{err && <div className="card" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>{err}</div>}
				<div className="row">
					<button className="btn primary" type="submit">{isLogin ? 'Login' : 'Create account'}</button>
				</div>
			</form>
			<small className="muted">
				{isLogin ? "No account? " : "Have an account? "}
				<a href={isLogin ? '/signup' : '/login'}>{isLogin ? 'Signup' : 'Login'}</a>
			</small>
		</div>
	)
}
