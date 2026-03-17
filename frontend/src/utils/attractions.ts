export function isTrustedAttractionImageUrl(url?: string): url is string {
  if (!url) {
    return false
  }

  try {
    const parsedUrl = new URL(url)
    return parsedUrl.hostname === 'images.unsplash.com'
  } catch {
    return false
  }
}

export function getMealLabel(type: string): string {
  const labels: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    snack: '小吃'
  }
  return labels[type] || type
}

export function normalizeTemperature(value: number | string): string {
  if (typeof value === 'number') {
    return `${value}°C`
  }
  if (!value) {
    return '0°C'
  }
  return `${String(value).replace(/°C|℃|°/g, '').trim()}°C`
}
