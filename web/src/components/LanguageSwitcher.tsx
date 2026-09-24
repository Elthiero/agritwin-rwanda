import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { SUPPORTED_LANGUAGES, type Language } from '../i18n'

const LANGUAGE_LABELS: Record<Language, string> = {
  en: 'EN',
  fr: 'FR',
  rw: 'RW',
}

/** Language choice persists in the URL's ?lang= param, per web/CLAUDE.md rule 2 (the
 * global filter bar, including language, is shareable via the URL), in addition to
 * i18n/index.ts remembering it in localStorage for the next visit. */
export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()

  function selectLanguage(lang: Language) {
    void i18n.changeLanguage(lang)
    const next = new URLSearchParams(searchParams)
    next.set('lang', lang)
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="tab-set language-switcher" role="group" aria-label={t('app.language')}>
      {SUPPORTED_LANGUAGES.map((lang) => (
        <button
          key={lang}
          type="button"
          aria-pressed={i18n.resolvedLanguage === lang}
          onClick={() => selectLanguage(lang)}
        >
          {LANGUAGE_LABELS[lang]}
        </button>
      ))}
    </div>
  )
}
