import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const LINKS: { to: string; key: string }[] = [
  { to: '/', key: 'nav.map' },
  { to: '/early-estimate', key: 'nav.earlyEstimate' },
  { to: '/scenario', key: 'nav.scenario' },
  { to: '/methodology', key: 'nav.methodology' },
  { to: '/data', key: 'nav.data' },
  { to: '/about', key: 'nav.about' },
]

export default function SiteNav() {
  const { t } = useTranslation()
  const { pathname } = useLocation()

  return (
    <nav className="site-nav" aria-label={t('nav.label')}>
      {LINKS.map(({ to, key }) => (
        <Link key={to} to={to} aria-current={pathname === to ? 'page' : undefined}>
          {t(key)}
        </Link>
      ))}
    </nav>
  )
}
