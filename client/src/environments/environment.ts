const isHttps = window.location.protocol === 'https:';
const wsProtocol = isHttps ? 'wss' : 'ws';
const origin = window.location.origin;

export const environment = {
  baseUrl: `${origin}/api/`,
  wsBaseUrl: `${wsProtocol}://${window.location.host}/ws/notification/`,
  authApiUrl: ``,
  resetUrl: ``,
  confirmationUrl: ``,
  appName: 'Flowless',
  logo: 'assets/logo.png',
  contactEmail: (window as any).env?.CONTACT_EMAIL,
  mode: (window as any).env?.MODE,
  web3FormApiKey: (window as any).env?.WEB3_FORM_API_KEY
};
