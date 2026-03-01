import { useState } from "react"
import { NavLink, Outlet, useLocation } from "react-router-dom"
import {
    MessageSquare,
    Search,
    Library,
    Brain,
    Terminal,
    Activity,
    Settings,
    X,
    Sparkles,
    Menu,
} from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
    { label: "Chat", href: "/", icon: MessageSquare },
    { label: "Deep Research", href: "/research", icon: Search },
    { label: "Biblioteca", href: "/library", icon: Library },
    { label: "Memória", href: "/memory", icon: Brain },
    { label: "Logs", href: "/logs", icon: Terminal },
    { label: "Status", href: "/status", icon: Activity },
    { label: "Configurações", href: "/settings", icon: Settings },
]

export default function Layout() {
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const location = useLocation()

    return (
        <div className="flex h-[100dvh] w-full overflow-hidden bg-[#0f172a] overscroll-none text-slate-200">
            {/* Overlay mobile */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
                    onClick={() => setSidebarOpen(false)}
                    aria-hidden="true"
                />
            )}

            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed top-0 left-0 z-50 flex h-[100dvh] w-64 flex-col bg-[#1e293b] text-slate-200 transition-transform duration-300 ease-in-out md:relative md:translate-x-0 border-r border-slate-800",
                    sidebarOpen ? "translate-x-0" : "-translate-x-full"
                )}
                style={{ paddingTop: "env(safe-area-inset-top)" }}
            >
                {/* Header sidebar */}
                <div className="flex items-center justify-between px-4 py-4">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-[#38bdf8]" />
                        <span className="text-lg font-semibold text-white tracking-wider">IARA</span>
                    </div>
                    <button
                        onClick={() => setSidebarOpen(false)}
                        className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-white md:hidden"
                        aria-label="Fechar menu"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Navegação */}
                <nav className="flex-1 space-y-1 px-3 py-2">
                    {navItems.map((item) => {
                        const isActive = location.pathname === item.href
                        return (
                            <NavLink
                                key={item.href}
                                to={item.href}
                                onClick={() => setSidebarOpen(false)}
                                className={cn(
                                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                                    isActive
                                        ? "bg-[#38bdf8] text-[#0f172a]"
                                        : "text-slate-400 hover:bg-slate-800 hover:text-white"
                                )}
                            >
                                <item.icon className={cn("h-5 w-5", isActive && "text-[#0f172a]")} />
                                {item.label}
                            </NavLink>
                        )
                    })}
                </nav>

                {/* Footer sidebar */}
                <div className="border-t border-slate-800 px-4 py-4">
                    <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#38bdf8] text-sm font-bold text-[#0f172a]">
                            M
                        </div>
                        <div className="flex flex-col">
                            <span className="text-sm font-medium text-white">Marcello</span>
                            <span className="text-xs text-slate-400">marcello@email.com</span>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content Wrapper */}
            <div className="flex flex-1 flex-col overflow-hidden min-w-0">
                {/* Header mobile */}
                <header
                    className="flex items-center justify-between border-b border-slate-800 bg-[#1e293b] px-4 py-3 md:hidden"
                    style={{ paddingTop: "calc(env(safe-area-inset-top) + 0.75rem)" }}
                >
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
                        aria-label="Abrir menu"
                    >
                        <Menu className="h-6 w-6" />
                    </button>
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-[#38bdf8]" />
                        <span className="text-lg font-semibold text-white tracking-wider">IARA</span>
                    </div>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#38bdf8] text-sm font-bold text-[#0f172a]">
                        M
                    </div>
                </header>

                {/* Page Content with isolated scroll */}
                <main className="flex-1 overflow-hidden relative">
                    <Outlet />
                </main>
            </div>
        </div>
    )
}
