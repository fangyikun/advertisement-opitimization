/**
 * 统一配置（Web / 未来 App 可覆盖）
 */
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1',
  defaultStoreId: import.meta.env.VITE_STORE_ID || 'store_001',
  defaultSignId: import.meta.env.VITE_SIGN_ID || 'sign_001',
  defaultCity: import.meta.env.VITE_DEFAULT_CITY || 'Adelaide',
};
