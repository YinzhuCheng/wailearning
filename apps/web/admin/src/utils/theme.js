const themeAliases = {
  default: 'blue',
  primary: 'blue',
  ocean: 'blue',
  teal: 'green',
  emerald: 'green',
  orange: 'warm',
  amber: 'warm',
  neutral: 'grayscale',
  gray: 'grayscale',
  grey: 'grayscale'
}

export const adminThemeNames = ['blue', 'green', 'warm', 'grayscale']

export function normalizeAdminTheme(value) {
  if (typeof value !== 'string') {
    return 'blue'
  }

  const normalized = value.trim().toLowerCase().replace(/[_\s]+/g, '-')
  const aliased = themeAliases[normalized] || normalized

  return adminThemeNames.includes(aliased) ? aliased : 'blue'
}

export function resolveAdminTheme(settings = {}) {
  const localTheme = window.localStorage.getItem('wailearning-admin-theme')
  const configuredTheme = settings.admin_theme || settings.theme || settings.theme_color || settings.color_theme

  return normalizeAdminTheme(localTheme || configuredTheme)
}

export function applyAdminTheme(theme) {
  const normalizedTheme = normalizeAdminTheme(theme)
  document.documentElement.dataset.waTheme = normalizedTheme
  return normalizedTheme
}
