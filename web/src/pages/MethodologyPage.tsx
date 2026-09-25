import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import '../styles/shared.css'

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

      <div className="page-content">
        <h2>{t('methodology.yieldTitle')}</h2>
        <p>{t('methodology.yieldBody')}</p>

        <h2>{t('methodology.attainableTitle')}</h2>
        <p>{t('methodology.attainableBody1')}</p>
        <p>{t('methodology.attainableBody2')}</p>

        <h2>{t('methodology.driversTitle')}</h2>
        <p>{t('methodology.driversBody1')}</p>
        <p>{t('methodology.driversBody2')}</p>

        <h2>{t('methodology.nowcastTitle')}</h2>
        <p>{t('methodology.nowcastBody1')}</p>
        <p>{t('methodology.nowcastBody2')}</p>

        <h2>{t('methodology.scenarioTitle')}</h2>
        <p>{t('methodology.scenarioBody')}</p>

        <h2>{t('methodology.reliabilityTitle')}</h2>
        <p>{t('methodology.reliabilityBody1')}</p>
        <ul>
          <li>{t('methodology.reliabilityOk')}</li>
          <li>{t('methodology.reliabilityCaution')}</li>
          <li>{t('methodology.reliabilitySuppressed')}</li>
        </ul>

        <h2>{t('methodology.validationTitle')}</h2>
        <p>{t('methodology.validationBody')}</p>
      </div>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
