import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import HeroTerraces from '../components/illustrations/HeroTerraces'
import ToolIcon from '../components/illustrations/ToolIcon'
import '../styles/shared.css'
import '../styles/home.css'

const TOOLS = [
  { key: 'feature1', kind: 'map' as const },
  { key: 'feature2', kind: 'drivers' as const },
  { key: 'feature3', kind: 'nowcast' as const },
  { key: 'feature4', kind: 'scenario' as const },
]

export default function HomePage() {
  const { t } = useTranslation()

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-title">
          <h1>{t('app.title')}</h1>
        </div>
        <LanguageSwitcher />
      </header>
      <SiteNav />

      <main>
        <section className="home-hero">
          <div className="home-hero-text">
            <h2>{t('home.hero')}</h2>
            <Link className="home-hero-cta" to="/map">
              {t('home.ctaButton')}
            </Link>
          </div>
          <div className="home-hero-art" aria-hidden="true">
            <HeroTerraces />
            <p className="home-hero-art-caption">
              {t('map.attainableYield')} <span className="dot dot-gold" /> · {t('map.actualYield')}{' '}
              <span className="dot dot-forest" />
            </p>
          </div>
        </section>

        <section className="home-proof-strip">
          <div>
            <strong>30</strong>
            <span>{t('data.districtCount')}</span>
          </div>
          <div>
            <strong>4</strong>
            <span>{t('data.crops')}</span>
          </div>
          <div>
            <strong>2019 to 2025</strong>
            <span>{t('data.years')}</span>
          </div>
        </section>

        <section className="home-tools">
          <h3>{t('home.solutionTitle')}</h3>
          <ul className="home-tools-list">
            {TOOLS.map(({ key, kind }) => (
              <li key={key}>
                <ToolIcon kind={kind} />
                <div>
                  <h4>{t(`home.${key}Title`)}</h4>
                  <p>{t(`home.${key}Body`)}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="home-challenge">
          <h3>{t('home.problemTitle')}</h3>
          <p>{t('home.problemBody')}</p>
        </section>

        <section className="home-cta">
          <h3>{t('home.ctaTitle')}</h3>
          <p>{t('home.ctaBody')}</p>
          <Link className="home-cta-button" to="/map">
            {t('home.ctaButton')}
          </Link>
        </section>

        <section className="home-why">
          <h3>{t('home.whyTitle')}</h3>
          <ul>
            <li>{t('home.why1')}</li>
            <li>{t('home.why2')}</li>
            <li>{t('home.why3')}</li>
            <li>{t('home.why4')}</li>
          </ul>
        </section>
      </main>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
