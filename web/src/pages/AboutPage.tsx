import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import '../styles/shared.css'

export default function AboutPage() {
  const { t } = useTranslation()

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-title">
          <h1>{t('about.title')}</h1>
          <p>{t('about.tagline')}</p>
        </div>
        <LanguageSwitcher />
      </header>
      <SiteNav />

      <div className="page-content">
        <h2>{t('about.projectTitle')}</h2>
        <p>{t('about.projectBody1')}</p>
        <p>{t('about.projectBody2')}</p>

        <h2>{t('about.teamTitle')}</h2>
        <p>{t('about.teamBody')}</p>

        <h2>{t('about.aiTitle')}</h2>
        <p>{t('about.aiBody')}</p>

        <h2>{t('about.contactTitle')}</h2>
        <p>{t('about.contactBody')}</p>
      </div>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
