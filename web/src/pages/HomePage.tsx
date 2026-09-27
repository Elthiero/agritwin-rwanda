import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import '../styles/shared.css'

export default function HomePage() {
  const { t } = useTranslation()

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-title">
          <h1>{t('app.title')}</h1>
          <p className="hero-tagline">{t('home.hero')}</p>
        </div>
        <LanguageSwitcher />
      </header>
      <SiteNav />

      <div className="page-content narrow home-content">
        <section className="hero-section">
          <h2>{t('home.problemTitle')}</h2>
          <p>{t('home.problemBody')}</p>
        </section>

        <section className="features-section">
          <h2>{t('home.solutionTitle')}</h2>
          <div className="features-grid">
            <div className="feature-card">
              <h3>{t('home.feature1Title')}</h3>
              <p>{t('home.feature1Body')}</p>
            </div>
            <div className="feature-card">
              <h3>{t('home.feature2Title')}</h3>
              <p>{t('home.feature2Body')}</p>
            </div>
            <div className="feature-card">
              <h3>{t('home.feature3Title')}</h3>
              <p>{t('home.feature3Body')}</p>
            </div>
            <div className="feature-card">
              <h3>{t('home.feature4Title')}</h3>
              <p>{t('home.feature4Body')}</p>
            </div>
          </div>
        </section>

        <section className="cta-section">
          <h2>{t('home.ctaTitle')}</h2>
          <p>{t('home.ctaBody')}</p>
          <Link className="cta-button" to="/map">
            {t('home.ctaButton')} →
          </Link>
        </section>

        <section className="info-section">
          <div className="info-column">
            <h3>{t('home.whyTitle')}</h3>
            <ul>
              <li>{t('home.why1')}</li>
              <li>{t('home.why2')}</li>
              <li>{t('home.why3')}</li>
              <li>{t('home.why4')}</li>
            </ul>
          </div>
        </section>
      </div>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
