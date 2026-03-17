import dayjs from 'dayjs'

export function calculateTravelDays(startDate?: string, endDate?: string): number | null {
  if (!startDate || !endDate) {
    return null
  }

  const diff = dayjs(endDate).diff(dayjs(startDate), 'day') + 1
  return Number.isFinite(diff) ? diff : null
}

export function isValidDateRange(days: number): boolean {
  return days > 0 && days <= 30
}
