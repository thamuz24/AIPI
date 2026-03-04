import './App.css';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './features/auth/context';
import { AppRoutes } from './app/routes';
import { ToastProvider } from './shared/ui';

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
