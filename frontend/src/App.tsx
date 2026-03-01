import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Chat from './pages/Chat';
import DeepResearch from './pages/DeepResearch';
import Library from './pages/Library';
import Memory from './pages/Memory';
import Logs from './pages/Logs';
import Status from './pages/Status';
import Settings from './pages/Settings';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Chat />} />
          <Route path="research" element={<DeepResearch />} />
          <Route path="library" element={<Library />} />
          <Route path="memory" element={<Memory />} />
          <Route path="logs" element={<Logs />} />
          <Route path="status" element={<Status />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
