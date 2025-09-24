import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const USERNAME_RE = /^[a-zA-Z0-9_.-]+$/ // must match backend schema

function extractErrorMessage(err)
{
	// Axios error with FastAPI 422 body
	const data = err?.response?.data
	const detail = data?.detail
	if (!detail) return 'Request failed'
	if (typeof detail === 'string') return detail
	if (Array.isArray(detail))
	{
		// FastAPI validation errors: [{loc, msg, type, ...}, ...]
		const msgs = detail.map(d =>
		{
			if (typeof d === 'string') return d
			if (d?.msg) return d.msg
			try { return JSON.stringify(d) } catch { return 'Validation error' }
		})
		return msgs.join('; ')
	}
	if (typeof detail === 'object')
	{
		if (detail.msg) return detail.msg
		try { return JSON.stringify(detail) } catch { return 'Validation error' }
	}
	return 'Request failed'
}

export default function Auth({ mode = 'login' })
{
	const isLogin = mode === 'login'
	const [username, setUsername] = useState('')
	const [password, setPassword] = useState('')
	const [err, setErr] = useState('')
	const { login, signup } = useAuth()
	const navigate = useNavigate()

	// Client-side validation to avoid 422 and show friendly errors
	const validation = useMemo(() =>
	{
		if (!username) return { ok: false, msg: '' }
		if (username.length < 3) return { ok: false, msg: 'Username must be at least 3 characters' }
		if (!USERNAME_RE.test(username)) return { ok: false, msg: 'Username can contain letters, numbers, ., _, - only' }
		if (password.length < 6) return { ok: false, msg: 'Password must be at least 6 characters' }
		return { ok: true, msg: '' }
	}, [username, password])

	const submit = async (e) =>
	{
		e.preventDefault()
		setErr('')
		if (!validation.ok)
		{
			setErr(validation.msg || 'Fix the validation errors above')
			return
		}
		try
		{
			if (isLogin)
			{
				await login(username.trim(), password)
			} else
			{
				await signup(username.trim(), password)
			}
			navigate('/')
		} catch (e2)
		{
			setErr(extractErrorMessage(e2))
		}
	}

	return (
		<div className="grid" style={{ maxWidth: 420, margin: '24px auto' }}>
			<h2>{isLogin ? 'Login' : 'Signup'}</h2>
			<form className="grid" onSubmit={submit} noValidate>
				<label>Username</label>
				<input
					className="input"
					value={username}
					onChange={(e) => setUsername(e.target.value)}
					placeholder="letters, numbers, . _ -"
				/>
				<label>Password</label>
				<input
					className="input"
					type="password"
					value={password}
					onChange={(e) => setPassword(e.target.value)}
					placeholder="min 6 characters"
				/>

				{(err || (!validation.ok && validation.msg)) && (
					<div className="card" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>
						{err || validation.msg}
					</div>
				)}

				<div className="row">
					<button className="btn primary" type="submit">
						{isLogin ? 'Login' : 'Create account'}
					</button>
				</div>
			</form>

			<small className="muted">
				{isLogin ? "No account? " : "Have an account? "}
				<Link to={isLogin ? '/signup' : '/login'}>{isLogin ? 'Signup' : 'Login'}</Link>
			</small>
		</div>
	)
}
