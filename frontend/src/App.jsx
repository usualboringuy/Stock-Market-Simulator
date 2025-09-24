import { Navigate, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import { useAuth } from './context/AuthContext'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import Stock from './pages/Stock'

export default function App()
{
	const { user } = useAuth()
	return (
		<>
			<Navbar />
			<div className="container">
				<Routes>
					<Route path="/" element={<Dashboard />} />
					<Route path="/stock/:symbol" element={<Stock />} />
					<Route path="/portfolio" element={user ? <Portfolio /> : <Navigate to="/login" replace />} />
					<Route path="/login" element={!user ? <Auth mode="login" /> : <Navigate to="/" replace />} />
					<Route path="/signup" element={!user ? <Auth mode="signup" /> : <Navigate to="/" replace />} />
					<Route path="*" element={<Navigate to="/" replace />} />
				</Routes>
			</div>
		</>
	)
}
