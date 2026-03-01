import type { LucideIcon } from "lucide-react"

interface PageHeaderProps {
    title: string
    description: string
    icon: LucideIcon
}

export default function PageHeader({ title, description, icon: Icon }: PageHeaderProps) {
    return (
        <div className="flex flex-col gap-4 mb-8 md:mb-10">
            <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#1e293b] border border-slate-800 shadow-sm">
                    <Icon className="h-7 w-7 text-[#38bdf8]" />
                </div>
                <div>
                    <h1 className="text-2xl font-semibold text-white tracking-tight">{title}</h1>
                    <p className="text-sm text-slate-400 mt-1 max-w-lg">{description}</p>
                </div>
            </div>
        </div>
    )
}
