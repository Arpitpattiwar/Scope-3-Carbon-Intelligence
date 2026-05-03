/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_PINCODE_API_BASE_URL?: string
  readonly VITE_GOOGLE_APP_PASSWORDS_URL?: string
  readonly VITE_GHG_PROTOCOL_SCOPE3_URL?: string
  readonly VITE_GRI_STANDARDS_URL?: string
  readonly VITE_DEFRA_CONVERSION_FACTORS_URL?: string
  readonly VITE_IPCC_AR6_URL?: string
  readonly VITE_SEBI_BRSR_URL?: string
  readonly VITE_CPCB_URL?: string
  readonly VITE_NIC_CODE_PDF_URL?: string
  readonly VITE_GOOGLE_FONTS_API_URL?: string
  readonly VITE_GOOGLE_FONTS_STATIC_URL?: string
  readonly VITE_GOOGLE_FONTS_CSS_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
