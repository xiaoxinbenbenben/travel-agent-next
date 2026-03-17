/// <reference types="vite/client" />

declare global {
  interface Window {
    __TRAVEL_AGENT_E2E__?: boolean
    _AMapSecurityConfig?: {
      securityJsCode: string
    }
  }
}

export {}
