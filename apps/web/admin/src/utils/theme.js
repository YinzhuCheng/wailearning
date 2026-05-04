const legacyThemeAliases = {
  default: 'professional-blue',
  primary: 'professional-blue',
  blue: 'professional-blue',
  ocean: 'professional-blue',
  green: 'fresh-green',
  teal: 'fresh-green',
  emerald: 'fresh-green',
  warm: 'warm-amber',
  orange: 'warm-amber',
  amber: 'warm-amber',
  grayscale: 'minimal-gray',
  neutral: 'minimal-gray',
  gray: 'minimal-gray',
  grey: 'minimal-gray'
}

const colorScales = {
  blue: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a'
  },
  green: {
    50: '#ecfdf5',
    100: '#d1fae5',
    200: '#a7f3d0',
    300: '#6ee7b7',
    400: '#34d399',
    500: '#10b981',
    600: '#059669',
    700: '#047857',
    800: '#065f46',
    900: '#064e3b'
  },
  amber: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f'
  },
  gray: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a'
  },
  navy: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#2563eb',
    600: '#1d4ed8',
    700: '#1e40af',
    800: '#172554',
    900: '#0f172a'
  },
  slate: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#334155',
    700: '#1f2937',
    800: '#111827',
    900: '#020617'
  },
  cyan: {
    50: '#ecfeff',
    100: '#cffafe',
    200: '#a5f3fc',
    300: '#67e8f9',
    400: '#22d3ee',
    500: '#06b6d4',
    600: '#0891b2',
    700: '#0e7490',
    800: '#155e75',
    900: '#164e63'
  },
  teal: {
    50: '#f0fdfa',
    100: '#ccfbf1',
    200: '#99f6e4',
    300: '#5eead4',
    400: '#2dd4bf',
    500: '#14b8a6',
    600: '#0d9488',
    700: '#0f766e',
    800: '#115e59',
    900: '#134e4a'
  },
  violet: {
    50: '#f5f3ff',
    100: '#ede9fe',
    200: '#ddd6fe',
    300: '#c4b5fd',
    400: '#a78bfa',
    500: '#8b5cf6',
    600: '#7c3aed',
    700: '#6d28d9',
    800: '#5b21b6',
    900: '#4c1d95'
  },
  red: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d'
  }
}

export const appearancePresets = [
  {
    key: 'professional-blue',
    name: 'Professional Blue',
    description: 'Calm operational blue with cyan accents, soft shadows, and balanced radius.',
    config: {
      primary: 'blue',
      accent: 'cyan',
      texture: 'none',
      shadow: 'soft',
      transparency: 'balanced',
      radius: 'balanced',
      density: 'comfortable'
    }
  },
  {
    key: 'fresh-green',
    name: 'Fresh Green',
    description: 'Green primary actions with blue accents and a light paper texture.',
    config: {
      primary: 'green',
      accent: 'blue',
      texture: 'soft-paper',
      shadow: 'soft',
      transparency: 'balanced',
      radius: 'soft',
      density: 'comfortable'
    }
  },
  {
    key: 'warm-amber',
    name: 'Warm Amber',
    description: 'Amber action color, teal accents, subtle grid texture, and crisp surfaces.',
    config: {
      primary: 'amber',
      accent: 'teal',
      texture: 'subtle-grid',
      shadow: 'medium',
      transparency: 'solid',
      radius: 'balanced',
      density: 'comfortable'
    }
  },
  {
    key: 'minimal-gray',
    name: 'Minimal Gray',
    description: 'Neutral gray theme with violet accents, lower shadows, and compact controls.',
    config: {
      primary: 'gray',
      accent: 'violet',
      texture: 'none',
      shadow: 'flat',
      transparency: 'solid',
      radius: 'subtle',
      density: 'compact'
    }
  },
  {
    key: 'academic-navy',
    name: 'Academic Navy',
    description: 'Navy primary palette with amber accents and fine texture for a formal academic feel.',
    config: {
      primary: 'navy',
      accent: 'amber',
      texture: 'fine-noise',
      shadow: 'medium',
      transparency: 'balanced',
      radius: 'subtle',
      density: 'comfortable'
    }
  },
  {
    key: 'high-contrast',
    name: 'High Contrast',
    description: 'High contrast slate surfaces, red accents, solid backgrounds, and strong focus visibility.',
    config: {
      primary: 'slate',
      accent: 'red',
      texture: 'none',
      shadow: 'strong',
      transparency: 'solid',
      radius: 'subtle',
      density: 'comfortable'
    }
  }
]

export const adminThemeNames = ['blue', 'green', 'warm', 'grayscale']
export const appearancePresetKeys = appearancePresets.map(item => item.key)

const defaultConfig = appearancePresets[0].config

export function normalizeAdminTheme(value) {
  const preset = resolveAppearancePreset(value)
  if (preset?.key === 'fresh-green') return 'green'
  if (preset?.key === 'warm-amber') return 'warm'
  if (preset?.key === 'minimal-gray') return 'grayscale'
  return 'blue'
}

export function resolveAppearancePreset(value) {
  if (typeof value !== 'string') {
    return appearancePresets[0]
  }

  const normalized = value.trim().toLowerCase().replace(/[_\s]+/g, '-')
  const key = legacyThemeAliases[normalized] || normalized
  return appearancePresets.find(item => item.key === key) || appearancePresets[0]
}

export function normalizeAppearanceConfig(value = {}) {
  const config = value && typeof value === 'object' ? value : {}
  return {
    primary: colorScales[config.primary] ? config.primary : defaultConfig.primary,
    accent: colorScales[config.accent] ? config.accent : defaultConfig.accent,
    texture: ['none', 'subtle-grid', 'soft-paper', 'fine-noise'].includes(config.texture)
      ? config.texture
      : defaultConfig.texture,
    shadow: ['flat', 'soft', 'medium', 'strong'].includes(config.shadow) ? config.shadow : defaultConfig.shadow,
    transparency: ['solid', 'balanced', 'glass'].includes(config.transparency)
      ? config.transparency
      : defaultConfig.transparency,
    radius: ['square', 'subtle', 'balanced', 'soft'].includes(config.radius) ? config.radius : defaultConfig.radius,
    density: ['compact', 'comfortable', 'spacious'].includes(config.density) ? config.density : defaultConfig.density
  }
}

export function resolveAppearanceFromState(settings = {}, appearanceState = null) {
  if (appearanceState?.selected_style?.config) {
    return normalizeAppearanceConfig(appearanceState.selected_style.config)
  }

  const presetKey =
    appearanceState?.system_default_preset ||
    settings.appearance_default_preset ||
    settings.admin_theme ||
    settings.theme ||
    settings.theme_color ||
    settings.color_theme

  return normalizeAppearanceConfig(resolveAppearancePreset(presetKey).config)
}

export function resolveAdminTheme(settings = {}) {
  return normalizeAdminTheme(settings.admin_theme || settings.theme || settings.theme_color || settings.color_theme)
}

function applyScale(root, prefix, scale) {
  Object.entries(scale).forEach(([step, value]) => {
    root.style.setProperty(`--wa-color-${prefix}-${step}`, value)
  })
}

function applyRadius(root, mode) {
  const values = {
    square: ['2px', '3px', '4px', '6px', '8px', '10px'],
    subtle: ['3px', '4px', '6px', '8px', '10px', '12px'],
    balanced: ['4px', '6px', '8px', '12px', '16px', '20px'],
    soft: ['6px', '8px', '12px', '16px', '20px', '24px']
  }[mode]

  root.style.setProperty('--wa-radius-xs', values[0])
  root.style.setProperty('--wa-radius-sm', values[1])
  root.style.setProperty('--wa-radius-md', values[2])
  root.style.setProperty('--wa-radius-lg', values[3])
  root.style.setProperty('--wa-radius-xl', values[4])
  root.style.setProperty('--wa-radius-2xl', values[5])
}

function applyShadow(root, mode, primary) {
  const shadows = {
    flat: ['none', '0 1px 2px rgba(15, 23, 42, 0.06)'],
    soft: ['0 8px 24px rgba(15, 23, 42, 0.07)', '0 12px 30px rgba(15, 23, 42, 0.09)'],
    medium: ['0 12px 28px rgba(15, 23, 42, 0.1)', '0 18px 38px rgba(15, 23, 42, 0.13)'],
    strong: ['0 14px 34px rgba(15, 23, 42, 0.14)', '0 22px 48px rgba(15, 23, 42, 0.18)']
  }[mode]

  root.style.setProperty('--wa-shadow-surface', shadows[0])
  root.style.setProperty('--wa-shadow-object', shadows[1])
  root.style.setProperty('--wa-focus-ring', `0 0 0 3px ${primary[600]}2e`)
}

function applyTransparency(root, mode) {
  const surface = {
    solid: '1',
    balanced: '0.88',
    glass: '0.76'
  }[mode]

  root.style.setProperty('--wa-surface-alpha', surface)
  root.style.setProperty('--wa-header-alpha', mode === 'solid' ? '0.96' : surface)
}

function applySidebar(root, primary, config) {
  const bottom = config.primary === 'amber' ? '#3f2f20' : primary[900]
  root.style.setProperty('--wa-sidebar-bg', `linear-gradient(180deg, ${primary[900]} 0%, ${bottom} 100%)`)
  root.style.setProperty('--wa-sidebar-active-bg', `linear-gradient(90deg, ${primary[700]} 0%, ${primary[500]} 100%)`)
}

export function applyAppearanceStyle(configValue) {
  const config = normalizeAppearanceConfig(configValue)
  const root = document.documentElement
  const primary = colorScales[config.primary]
  const accent = colorScales[config.accent]

  root.dataset.waTheme = config.primary
  root.dataset.waTexture = config.texture
  root.dataset.waShadow = config.shadow
  root.dataset.waTransparency = config.transparency
  root.dataset.waRadius = config.radius
  root.dataset.waDensity = config.density

  applyScale(root, 'primary', primary)
  applyScale(root, 'accent', accent)
  applyRadius(root, config.radius)
  applyShadow(root, config.shadow, primary)
  applyTransparency(root, config.transparency)
  applySidebar(root, primary, config)

  return config
}

export function applyAdminTheme(theme) {
  const preset = resolveAppearancePreset(theme)
  return applyAppearanceStyle(preset.config).primary
}
