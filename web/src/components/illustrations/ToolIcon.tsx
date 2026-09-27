type ToolKind = 'map' | 'drivers' | 'nowcast' | 'scenario'

const PATHS: Record<ToolKind, JSX.Element> = {
  map: (
    <>
      <path d="M3 20 C7 15 10 21 14 17 C18 13 21 19 25 15" />
      <path d="M3 24 C7 20 10 25 14 22 C18 19 21 24 25 21" />
      <circle cx="19" cy="9" r="4" />
      <path d="M19 13 L19 17" />
    </>
  ),
  drivers: (
    <>
      <path d="M14 25 L14 13" />
      <path d="M14 13 C14 8 10 7 8 4" />
      <path d="M14 16 C14 12 18 11 20 8" />
      <path d="M14 20 C14 17 11 16 9 14" />
      <circle cx="14" cy="25" r="1.6" fill="currentColor" stroke="none" />
    </>
  ),
  nowcast: (
    <>
      <path d="M5 19 C5 11 11 5 19 5" strokeDasharray="2.5 3" />
      <circle cx="19" cy="5" r="2.4" />
      <path d="M9 23 C9 16 15 12 21 14" />
      <circle cx="8" cy="24" r="1.6" fill="currentColor" stroke="none" />
    </>
  ),
  scenario: (
    <>
      <path d="M4 10 L24 10" />
      <path d="M4 18 L24 18" />
      <circle cx="10" cy="10" r="2.6" fill="var(--paper-raised)" />
      <circle cx="18" cy="18" r="2.6" fill="var(--paper-raised)" />
    </>
  ),
}

export default function ToolIcon({ kind }: { kind: ToolKind }) {
  return (
    <svg className="tool-icon" viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {PATHS[kind]}
    </svg>
  )
}
