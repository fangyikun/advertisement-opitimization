import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Player from './components/Player';
import Stores from './pages/Stores';

function AppRoutes() {
  const location = useLocation();
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/stores" element={<Stores key={location.pathname + location.search} />} />
      <Route path="/player" element={<Player />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
