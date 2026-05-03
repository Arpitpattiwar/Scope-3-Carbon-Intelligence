const envUrl = (value: string | undefined): string => value?.trim() || ''
const envBaseUrl = (value: string | undefined): string => envUrl(value).replace(/\/+$/, '')

export const URLS = {
  api: envBaseUrl(import.meta.env.VITE_API_URL),
  pincodeApiBase: envBaseUrl(import.meta.env.VITE_PINCODE_API_BASE_URL),
  googleAppPasswords: envUrl(import.meta.env.VITE_GOOGLE_APP_PASSWORDS_URL),
  ghgProtocolScope3: envUrl(import.meta.env.VITE_GHG_PROTOCOL_SCOPE3_URL),
  griStandards: envUrl(import.meta.env.VITE_GRI_STANDARDS_URL),
  defraConversionFactors: envUrl(import.meta.env.VITE_DEFRA_CONVERSION_FACTORS_URL),
  ipccAr6: envUrl(import.meta.env.VITE_IPCC_AR6_URL),
  sebiBrsr: envUrl(import.meta.env.VITE_SEBI_BRSR_URL),
  cpcb: envUrl(import.meta.env.VITE_CPCB_URL),
  nicCodePdf: envUrl(import.meta.env.VITE_NIC_CODE_PDF_URL),
} as const
