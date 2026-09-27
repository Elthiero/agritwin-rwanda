import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import '../styles/shared.css'
import '../styles/about.css'

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

      <div className="about-layout">
        <div className="about-main">
          <h2>{t('about.projectTitle')}</h2>
          <p>{t('about.projectBody1')}</p>
          <p>{t('about.projectBody2')}</p>
        </div>

        <aside className="about-rail">
          <div className="about-rail-block">
            <h3>{t('about.teamTitle')}</h3>
            <p>{t('about.teamBody')}</p>
          </div>

          <blockquote className="about-quote">
            <p>{t('about.aiBody')}</p>
            <cite>{t('about.aiTitle')}</cite>
          </blockquote>

          <div className="about-rail-block">
            <h3>{t('about.contactTitle')}</h3>
            <p>{t('about.contactBody')}</p>
          </div>
        </aside>
      </div>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
