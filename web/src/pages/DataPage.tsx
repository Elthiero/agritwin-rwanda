import { useTranslation } from 'react-i18next'
import { useMeta } from '../api/hooks'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SiteNav from '../components/SiteNav'
import '../styles/shared.css'

const SATELLITE_SOURCES = [
  { name: 'MODIS NDVI (MOD13Q1)', use: 'ndvi' },
  { name: 'CHIRPS daily rainfall', use: 'rainfall' },
  { name: 'ESA WorldCover', use: 'cropland' },
  { name: 'iSDAsoil (pH, nitrogen, carbon, texture)', use: 'soil' },
  { name: 'SRTM elevation', use: 'terrain' },
] as const

export default function DataPage() {
  const { t } = useTranslation()
  const meta = useMeta()

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-title">
          <h1>{t('data.title')}</h1>
          <p>{t('data.tagline')}</p>
        </div>
        <LanguageSwitcher />
      </header>
      <SiteNav />

      <div className="page-grid">
        <section className="card">
          <h2>{t('data.surveyTitle')}</h2>
          <p className="card-caption">{t('data.surveyCaption')}</p>
          <p className="card-note">{t('data.surveyBody')}</p>
        </section>

        <section className="card">
          <h2>{t('data.satelliteTitle')}</h2>
          <p className="card-caption">{t('data.satelliteCaption')}</p>
          <ul>
            {SATELLITE_SOURCES.map((s) => (
              <li key={s.name}>
                {s.name} — {t(`data.satelliteUse.${s.use}`)}
              </li>
            ))}
          </ul>
        </section>

        <section className="card">
          <h2>{t('data.scopeTitle')}</h2>
          {meta.isLoading && <p className="card-empty">{t('data.loading')}</p>}
          {meta.data && (
            <dl>
              <dt>{t('data.dataVersion')}</dt>
              <dd>{meta.data.data_version}</dd>
              <dt>{t('data.crops')}</dt>
              <dd>{meta.data.crops.map((c) => t(`crop.${c}`)).join(', ')}</dd>
              <dt>{t('data.years')}</dt>
              <dd>
                {Math.min(...meta.data.years)}–{Math.max(...meta.data.years)}
              </dd>
              <dt>{t('data.districtCount')}</dt>
              <dd>{meta.data.districts.length}</dd>
            </dl>
          )}
        </section>

        <section className="card">
          <h2>{t('data.privacyTitle')}</h2>
          <p className="card-note">{t('data.privacyBody')}</p>
        </section>
      </div>

      <footer className="footer-strip">{t('app.footer')}</footer>
    </div>
  )
}
