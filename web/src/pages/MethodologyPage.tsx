import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import '../styles/shared.css'
import '../styles/methodology.css'

const SECTIONS = [
  { id: 'yield', titleKey: 'methodology.yieldTitle' },
  { id: 'attainable', titleKey: 'methodology.attainableTitle' },
  { id: 'drivers', titleKey: 'methodology.driversTitle' },
  { id: 'nowcast', titleKey: 'methodology.nowcastTitle' },
  { id: 'scenario', titleKey: 'methodology.scenarioTitle' },
  { id: 'reliability', titleKey: 'methodology.reliabilityTitle' },
  { id: 'validation', titleKey: 'methodology.validationTitle' },
]

export default function MethodologyPage() {
  const { t } = useTranslation()

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-title">
          <h1>{t('methodology.title')}</h1>
          <p>{t('methodology.tagline')}</p>
        </div>
        <LanguageSwitcher />
      </header>
      <SiteNav />

      <div className="methodology-stats">
        <div>
          <strong>{t('methodology.statGapValue')}</strong>
          <span>{t('methodology.statGapLabel')}</span>
        </div>
        <div>
          <strong>{t('methodology.statDriverValue')}</strong>
          <span>{t('methodology.statDriverLabel')}</span>
        </div>
        <div>
          <strong>{t('methodology.statNowcastValue')}</strong>
          <span>{t('methodology.statNowcastLabel')}</span>
        </div>
      </div>

      <div className="methodology-layout">
        <nav className="methodology-index" aria-label={t('methodology.indexLabel')}>
          <ul>
            {SECTIONS.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`}>{t(s.titleKey)}</a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="page-content methodology-content">
          <section id="yield">
            <h2>{t('methodology.yieldTitle')}</h2>
            <p>{t('methodology.yieldBody')}</p>
          </section>

          <section id="attainable">
            <h2>{t('methodology.attainableTitle')}</h2>
            <p>{t('methodology.attainableBody1')}</p>
            <p>{t('methodology.attainableBody2')}</p>
          </section>

          <section id="drivers">
            <h2>{t('methodology.driversTitle')}</h2>
            <p>{t('methodology.driversBody1')}</p>
            <p>{t('methodology.driversBody2')}</p>
          </section>

          <section id="nowcast">
            <h2>{t('methodology.nowcastTitle')}</h2>
            <p>{t('methodology.nowcastBody1')}</p>
            <p>{t('methodology.nowcastBody2')}</p>
          </section>

          <section id="scenario">
            <h2>{t('methodology.scenarioTitle')}</h2>
            <p>{t('methodology.scenarioBody')}</p>
          </section>

          <section id="reliability">
            <h2>{t('methodology.reliabilityTitle')}</h2>
            <p>{t('methodology.reliabilityBody1')}</p>
            <ul>
              <li>{t('methodology.reliabilityOk')}</li>
              <li>{t('methodology.reliabilityCaution')}</li>
              <li>{t('methodology.reliabilitySuppressed')}</li>
            </ul>
          </section>

          <section id="validation">
            <h2>{t('methodology.validationTitle')}</h2>
            <p>{t('methodology.validationBody')}</p>
          </section>
        </div>
      </div>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
