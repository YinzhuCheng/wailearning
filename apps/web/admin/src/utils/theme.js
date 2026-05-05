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

/** Radius: controls squarer than cards/dialogs for visual rhythm */
function radiusTokenValues(mode) {
  return {
    square: {
      xs: '1px',
      sm: '2px',
      md: '3px',
      lg: '4px',
      xl: '5px',
      '2xl': '6px',
      control: '3px',
      card: '5px',
      dialog: '6px',
      pill: '999px'
    },
    subtle: {
      xs: '3px',
      sm: '4px',
      md: '6px',
      lg: '8px',
      xl: '10px',
      '2xl': '12px',
      control: '5px',
      card: '9px',
      dialog: '11px',
      pill: '999px'
    },
    balanced: {
      xs: '4px',
      sm: '6px',
      md: '8px',
      lg: '12px',
      xl: '16px',
      '2xl': '20px',
      control: '7px',
      card: '13px',
      dialog: '17px',
      pill: '999px'
    },
    soft: {
      xs: '6px',
      sm: '8px',
      md: '12px',
      lg: '16px',
      xl: '20px',
      '2xl': '24px',
      control: '10px',
      card: '17px',
      dialog: '21px',
      pill: '999px'
    }
  }[mode]
}

function shadowPair(mode, primaryHex) {
  const tint = `${primaryHex}14`
  const shadows = {
    flat: ['none', '0 1px 2px rgba(15, 23, 42, 0.06)'],
    soft: ['0 8px 24px rgba(15, 23, 42, 0.07)', `0 12px 30px rgba(15, 23, 42, 0.09), 0 1px 0 ${tint}`],
    medium: ['0 12px 28px rgba(15, 23, 42, 0.1)', `0 18px 38px rgba(15, 23, 42, 0.13), 0 1px 0 ${tint}`],
    strong: ['0 14px 34px rgba(15, 23, 42, 0.14)', `0 22px 48px rgba(15, 23, 42, 0.18), 0 2px 0 ${tint}`]
  }[mode]
  return shadows
}

function transparencyTokens(mode) {
  const surface = { solid: '1', balanced: '0.88', glass: '0.72' }[mode]
  const bodyBgMix = { solid: '0%', balanced: '8%', glass: '16%' }[mode]
  const textureOpacity = { solid: '0.38', balanced: '0.58', glass: '0.78' }[mode]
  const header = mode === 'solid' ? '0.96' : surface
  return { surface, bodyBgMix, textureOpacity, header }
}

function densityTokens(mode) {
  if (mode === 'compact') {
    return {
      fontXs: '11px',
      fontSm: '12px',
      fontMd: '13px',
      fontLg: '16px',
      fontXl: '18px',
      font2xl: '22px',
      fontStat: '24px',
      spaceXs: '4px',
      spaceSm: '8px',
      spaceMd: '12px',
      spaceLg: '16px',
      spaceXl: '20px',
      controlV: '6px',
      controlH: '11px',
      tableCellV: '6px',
      tableCellH: '8px',
      menuItemV: '6px',
      menuItemH: '12px'
    }
  }
  if (mode === 'spacious') {
    return {
      fontXs: '12px',
      fontSm: '14px',
      fontMd: '15px',
      fontLg: '19px',
      fontXl: '22px',
      font2xl: '28px',
      fontStat: '30px',
      spaceXs: '8px',
      spaceSm: '12px',
      spaceMd: '16px',
      spaceLg: '22px',
      spaceXl: '28px',
      controlV: '10px',
      controlH: '16px',
      tableCellV: '12px',
      tableCellH: '12px',
      menuItemV: '10px',
      menuItemH: '16px'
    }
  }
  return {
    fontXs: '12px',
    fontSm: '13px',
    fontMd: '14px',
    fontLg: '18px',
    fontXl: '20px',
    font2xl: '26px',
    fontStat: '28px',
    spaceXs: '6px',
    spaceSm: '10px',
    spaceMd: '14px',
    spaceLg: '18px',
    spaceXl: '24px',
    controlV: '8px',
    controlH: '14px',
    tableCellV: '8px',
    tableCellH: '10px',
    menuItemV: '8px',
    menuItemH: '14px'
  }
}

function buildAppearanceCssVars(config) {
  const primary = colorScales[config.primary]
  const accent = colorScales[config.accent]
  const vars = {}

  Object.entries(primary).forEach(([step, value]) => {
    vars[`--wa-color-primary-${step}`] = value
  })
  Object.entries(accent).forEach(([step, value]) => {
    vars[`--wa-color-accent-${step}`] = value
  })

  const rt = radiusTokenValues(config.radius)
  vars['--wa-radius-xs'] = rt.xs
  vars['--wa-radius-sm'] = rt.sm
  vars['--wa-radius-md'] = rt.md
  vars['--wa-radius-lg'] = rt.lg
  vars['--wa-radius-xl'] = rt.xl
  vars['--wa-radius-2xl'] = rt['2xl']
  vars['--wa-radius-control'] = rt.control
  vars['--wa-radius-card'] = rt.card
  vars['--wa-radius-dialog'] = rt.dialog
  vars['--wa-radius-pill'] = rt.pill

  vars['--el-border-radius-base'] = rt.control
  vars['--el-border-radius-small'] = rt.xs
  vars['--el-border-radius-round'] = rt.xl

  const [s0, s1] = shadowPair(config.shadow, primary[600])
  vars['--wa-shadow-surface'] = s0
  vars['--wa-shadow-object'] = s1
  vars['--wa-focus-ring'] = `0 0 0 3px ${primary[600]}2e`

  const tr = transparencyTokens(config.transparency)
  vars['--wa-surface-alpha'] = tr.surface
  vars['--wa-body-bg-mix'] = tr.bodyBgMix
  vars['--wa-texture-opacity'] = tr.textureOpacity
  vars['--wa-header-alpha'] = tr.header
  vars['--wa-surface-blend-pct'] = `${Math.round(parseFloat(tr.surface) * 100)}%`

  const dn = densityTokens(config.density)
  vars['--wa-font-size-xs'] = dn.fontXs
  vars['--wa-font-size-sm'] = dn.fontSm
  vars['--wa-font-size-md'] = dn.fontMd
  vars['--wa-font-size-lg'] = dn.fontLg
  vars['--wa-font-size-xl'] = dn.fontXl
  vars['--wa-font-size-2xl'] = dn.font2xl
  vars['--wa-font-size-stat'] = dn.fontStat
  vars['--wa-space-xs'] = dn.spaceXs
  vars['--wa-space-sm'] = dn.spaceSm
  vars['--wa-space-md'] = dn.spaceMd
  vars['--wa-space-lg'] = dn.spaceLg
  vars['--wa-space-xl'] = dn.spaceXl
  vars['--wa-control-padding-v'] = dn.controlV
  vars['--wa-control-padding-h'] = dn.controlH
  vars['--wa-table-cell-padding-v'] = dn.tableCellV
  vars['--wa-table-cell-padding-h'] = dn.tableCellH
  vars['--wa-menu-item-padding-v'] = dn.menuItemV
  vars['--wa-menu-item-padding-h'] = dn.menuItemH

  if (config.primary === 'amber') {
    const acc = colorScales[config.accent] || colorScales.teal
    vars['--wa-sidebar-bg'] = `linear-gradient(180deg, #111827 0%, ${acc[900]} 100%)`
    vars['--wa-sidebar-active-bg'] = `linear-gradient(90deg, ${primary[600]} 0%, ${acc[600]} 100%)`
  } else {
    vars['--wa-sidebar-bg'] = `linear-gradient(180deg, ${primary[900]} 0%, ${primary[900]} 100%)`
    vars['--wa-sidebar-active-bg'] = `linear-gradient(90deg, ${primary[700]} 0%, ${primary[500]} 100%)`
  }

  return vars
}

function applyCssVarsToElement(el, vars) {
  Object.entries(vars).forEach(([key, value]) => {
    el.style.setProperty(key, value)
  })
}

/**
 * CSS variables for appearance (same map as :root; use on preview hosts).
 */
export function appearancePreviewStyleVars(configValue) {
  return buildAppearanceCssVars(normalizeAppearanceConfig(configValue))
}

export function applyAppearanceStyle(configValue) {
  const config = normalizeAppearanceConfig(configValue)
  const root = document.documentElement

  root.dataset.waTheme = config.primary
  root.dataset.waTexture = config.texture
  root.dataset.waShadow = config.shadow
  root.dataset.waTransparency = config.transparency
  root.dataset.waRadius = config.radius
  root.dataset.waDensity = config.density

  applyCssVarsToElement(root, buildAppearanceCssVars(config))

  return config
}

export function applyAdminTheme(theme) {
  const preset = resolveAppearancePreset(theme)
  return applyAppearanceStyle(preset.config).primary
}
