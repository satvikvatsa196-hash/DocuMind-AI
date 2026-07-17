import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { BookOpen, FolderOpen, UploadCloud, MessageSquare, LogOut } from 'lucide-react';
import { clsx } from 'clsx';

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/', icon: BookOpen },
    { name: 'Collections', path: '/collections', icon: FolderOpen },
    { name: 'Upload', path: '/upload', icon: UploadCloud },
    { name: 'Chat AI', path: '/chat', icon: MessageSquare },
  ];

  return (
    <div className="flex h-screen bg-brand-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-brand-100 flex flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-600 to-brand-400 bg-clip-text text-transparent flex items-center gap-2">
            <BookOpen className="text-brand-600" />
            DocuMind AI
          </h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.name}
                to={item.path}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium',
                  isActive 
                    ? 'bg-brand-500 text-white shadow-md shadow-brand-500/20' 
                    : 'text-brand-700 hover:bg-brand-50 hover:text-brand-900'
                )}
              >
                <item.icon size={20} />
                {item.name}
              </Link>
            )
          })}
        </nav>

        <div className="p-4 border-t border-brand-100">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 w-full text-left text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors font-medium"
          >
            <LogOut size={20} />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-brand-50/50">
        <div className="h-full p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
