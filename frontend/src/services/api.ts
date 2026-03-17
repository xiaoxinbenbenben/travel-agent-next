import axios from 'axios'
import type {
  HealthResponse,
  TripFormData,
  TripPlanResponse
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

function resolveErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    return (
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      fallback
    )
  }
  if (error instanceof Error) {
    return error.message
  }
  return fallback
}

export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error) {
    throw new Error(resolveErrorMessage(error, '生成旅行计划失败'))
  }
}

export async function healthCheck(): Promise<HealthResponse> {
  try {
    const response = await apiClient.get<HealthResponse>('/health')
    return response.data
  } catch (error) {
    throw new Error(resolveErrorMessage(error, '健康检查失败'))
  }
}

export default apiClient
