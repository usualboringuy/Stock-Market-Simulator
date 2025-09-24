import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function Navbar()
{
	const { user, logout } = useAuth()
	const [q, setQ] = useState('')
	const [results, setResults] = useState([])
	const [open, setOpen] = useState(false)
	const navigate = useNavigate()
	const boxRef = useRef(null)
	const timerRef = useRef(null)

	useEffect(() =>
	{
		const handler = (e) =>
		{
			if (!boxRef.current?.contains(e.target)) setOpen(false)
		}
		document.addEventListener('click', handler)
		return () => document.removeEventListener('click', handler)
	}, [])

	const onChange = (v) =>
	{
		setQ(v)
		setOpen(true)
		clearTimeout(timerRef.current)
		if (v.trim().length < 2)
		{
			setResults([]); return
		}
		timerRef.current = setTimeout(async () =>
		{
			try
			{
				const res = await api.get('/api/instruments/search', { params: { q: v, limit: 10 } })
				setResults(res.data || [])
			} catch
			{
				setResults([])
			}
		}, 200)
	}

	const pick = (sym) =>
	{
		setOpen(false)
		setQ(sym)
		navigate(`/stock/${encodeURIComponent(sym)}`)
	}

	return (
		<div className="navbar">
			<Link to="/" className="nav-brand">Stock Simulator</Link>
			<div className="nav-links">
				<Link to="/">Dashboard</Link>
				<Link to="/portfolio">Portfolio</Link>
			</div>
			<div className="nav-spacer" />
			<div className="search-box" ref={boxRef}>
				<input className="input" placeholder="Search symbol or name..."
					value={q} onChange={(e) => onChange(e.target.value)} onFocus={() => setOpen(true)} />
				{open && results.length > 0 && (
					<div className="search-results">
						{results.map((r) => (
							<div key={r.token} className="search-item" onClick={() => pick(r.symbol)}>
								<div>{r.symbol} <span className="badge">{r.exchange}</span></div>
								<small className="muted">{r.name}</small>
							</div>
						))}
					</div>
				)}
			</div>
			<div style={{ width: 8 }} />
			{!user ? (
				<>
					<Link to="/login" className="btn small">Login</Link>
					<Link to="/signup" className="btn small">Signup</Link>
				</>
			) : (
				<>
					<span><small className="muted">Hi,</small> <b>{user.username}</b></span>
					<button className="btn small" onClick={logout}>Logout</button>
				</>
			)}
		</div>
	)
}
