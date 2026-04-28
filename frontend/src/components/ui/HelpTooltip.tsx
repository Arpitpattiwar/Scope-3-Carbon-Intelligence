import { HelpCircle } from 'lucide-react'

interface Props {
  title: string
  content: string
  example?: string
  link?: { label: string; href: string }
}

export default function HelpTooltip({ title, content, example, link }: Props) {
  return (
    <span className="relative inline-flex items-center ml-1.5 group">
      <span
        className="p-0.5 text-gray-400 hover:text-brand-600 transition-colors cursor-help"
        title={title}
      >
        <HelpCircle size={14} />
      </span>
      {/* Hover tooltip — pure CSS, no JS state, no click needed */}
      <span className="
        pointer-events-none absolute left-6 top-0 z-50 w-60
        bg-gray-900 text-white text-xs rounded-xl shadow-2xl p-3
        opacity-0 group-hover:opacity-100
        translate-y-1 group-hover:translate-y-0
        transition-all duration-150
        whitespace-normal
      ">
        <span className="block font-semibold mb-1 text-white">{title}</span>
        <span className="block text-gray-300 leading-relaxed">{content}</span>
        {example && (
          <span className="block mt-2 p-1.5 bg-gray-800 rounded-lg">
            <span className="block text-gray-400 text-[10px] uppercase tracking-wide mb-0.5">Example</span>
            <span className="font-mono text-gray-200">{example}</span>
          </span>
        )}
        {link && (
          <a href={link.href}
            className="pointer-events-auto mt-2 inline-flex text-brand-400 hover:text-brand-300 hover:underline">
            {link.label} →
          </a>
        )}
      </span>
    </span>
  )
}
