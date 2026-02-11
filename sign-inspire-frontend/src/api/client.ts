import axios from 'axios';
import { config } from '../config';

const api = axios.create({
  baseURL: config.apiBaseUrl,
});

export const parseRule = async (storeId: string, text: string) => {
  return api.post(`/stores/${storeId}/rules:parse`, null, {
    params: { text } // 注意：后端是 Query Param 还是 Body，这里假设是 Query
  });
};

export const createRule = async (storeId: string, ruleData: any) => {
  return api.post(`/stores/${storeId}/rules`, ruleData);
};

export const updateRule = async (storeId: string, ruleId: string, data: { priority?: number; name?: string }) => {
  return api.patch(`/stores/${storeId}/rules/${ruleId}`, data);
};

export const deleteRule = async (storeId: string, ruleId: string) => {
  return api.delete(`/stores/${storeId}/rules/${ruleId}`);
};

/** 重置规则：清空当前门店规则并恢复为默认全球规则种子 */
export const resetRules = (storeId: string) =>
  api.post(`/stores/${storeId}/rules:reset`);

export const getRules = (storeId: string, city?: string) =>
  api.get(`/stores/${storeId}/rules`, { params: city ? { city } : {} });
export const getWeather = () =>
  api.get<{ weather: string; temp_c?: number; region?: string; updated_at: string | null }>('/weather');
export const checkRules = (storeId: string) =>
  api.post<{ current_playlist: string; current_weather: string }>(`/stores/${storeId}/check-rules`);

// 门店 API
export const listStores = async () => api.get('/stores');
export const listStoresByCity = async (city: string) => api.get(`/cities/${city}/stores`);
export const getStore = async (storeId: string) => api.get(`/stores/${storeId}`);
export const createStore = async (data: Record<string, unknown>) => api.post('/stores', data);
export const updateStore = async (storeId: string, data: Record<string, unknown>) =>
  api.patch(`/stores/${storeId}`, data);
export const deleteStore = async (storeId: string) => api.delete(`/stores/${storeId}`);

// 内容（支持 sign_id，App 用）
export const getCurrentContentByStore = (storeId: string) =>
  api.get<{ content: string }>(`/stores/${storeId}/current-content`);
export const getCurrentContentBySign = (signId: string) =>
  api.get<{ content: string; store_id?: string }>(`/signs/${signId}/current-content`);

// 推荐门店（基于当前天气+规则，支持城市名或用户定位 lat,lon；target_id 指定品类时按该品类推荐）
export const getRecommendations = (
  limit = 10,
  city = 'Adelaide',
  lat?: number,
  lon?: number,
  targetId?: string
) =>
  api.get<{
    weather: string;
    target_id: string;
    category_label: string;
    stores: Array<{
      name: string;
      address: string;
      latitude?: number;
      longitude?: number;
      type?: string;
      photos?: string[];
      google_maps_uri?: string;
    }>;
    message: string;
    city?: string;
  }>('/recommendations', {
    params: { limit, city, ...(lat != null && lon != null ? { lat, lon } : {}), ...(targetId ? { target_id: targetId } : {}) },
  });