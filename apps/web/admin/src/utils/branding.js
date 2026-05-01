const LEGACY_BRAND_REGEX = /dd-class/gi

export function normalizeBrandingText(value) {
  if (typeof value !== 'string') {
    return value
  }

  return value.replace(LEGACY_BRAND_REGEX, 'BIMSA-CLASS')
}

export function normalizeSystemSettings(settings) {
  if (!settings || typeof settings !== 'object') {
    return settings
  }

  return {
    ...settings,
    system_name: normalizeBrandingText(settings.system_name),
    copyright: normalizeBrandingText(settings.copyright)
  }
}
