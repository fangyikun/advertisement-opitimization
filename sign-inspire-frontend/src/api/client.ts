import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1', // 指向你的 FastAPI
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