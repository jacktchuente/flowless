export const environment = {
  baseUrl: `https://api.${(window as any).env?.BASE_DOMAIN}/api/`,
  wsBaseUrl: `wss://ws.${(window as any).env?.BASE_DOMAIN}/ws/notification/`,
  authApiUrl: `https://api.${(window as any).env?.BASE_DOMAIN}/api`,
  resetUrl: `https://${(window as any).env?.BASE_DOMAIN}/reset-password`,
  confirmationUrl: `https://${(window as any).env?.BASE_DOMAIN}/confirmation`,
  appName: 'Flowless',
  logo: 'assets/logo.png',
  contactEmail: (window as any).env?.CONTACT_EMAIL,
  mode: (window as any).env?.MODE,
  web3FormApiKey: (window as any).env?.WEB3_FORM_API_KEY ,
};
