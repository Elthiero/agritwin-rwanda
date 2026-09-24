import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import fr from './locales/fr.json'
import rw from './locales/rw.json'

export const SUPPORTED_LANGUAGES = ['en', 'fr', 'rw'] as const
export type Language = (typeof SUPPORTED_LANGUAGES)[number]

function isLanguage(value: string | null): value is Language {
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(value ?? '')
}

// URL ?lang= wins (per web/CLAUDE.md rule 2: the filter bar, including language,
// persists in the URL so every view is shareable), then a remembered choice, then
// English. No i18next-browser-languagedetector dependency: this is a 2-line lookup.
function initialLanguage(): Language {
  const fromUrl = new URLSearchParams(window.location.search).get('lang')
  if (isLanguage(fromUrl)) return fromUrl
  const fromStorage = window.localStorage.getItem('agritwin-lang')
  if (isLanguage(fromStorage)) return fromStorage
  return 'en'
}

void i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      fr: { translation: fr },
      rw: { translation: rw },
    },
    lng: initialLanguage(),
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  })

i18n.on('languageChanged', (lng) => {
  try {
    window.localStorage.setItem('agritwin-lang', lng)
  } catch {
    // Private browsing or blocked storage: language still works for this session,
    // just isn't remembered for the next visit.
  }
})

export default i18n
