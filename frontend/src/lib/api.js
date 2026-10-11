import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 65_000,
});

let bannerShown = false;
let bannerListeners = new Set();
export const subscribeWakeUp = (fn) => {
  bannerListeners.add(fn);
  return () => bannerListeners.delete(fn);
};
const emitBanner = (visible) => {
  bannerShown = visible;
  bannerListeners.forEach((fn) => fn(visible));
};
export const isWakingUp = () => bannerShown;

api.interceptors.response.use(
  (resp) => {
    if (bannerShown) emitBanner(false);
    return resp;
  },
  async (error) => {
    const config = error.config || {};
    config.__retryCount = config.__retryCount || 0;
    const shouldRetry =
      config.__retryCount < 2 &&
      (error.code === "ECONNABORTED" ||
        error.code === "ERR_NETWORK" ||
        (error.response && error.response.status >= 500));
    if (shouldRetry) {
      config.__retryCount += 1;
      if (!bannerShown) emitBanner(true);
      await new Promise((r) => setTimeout(r, 1500 * config.__retryCount));
      return api.request(config);
    }
    const msg = error?.response?.data?.detail || error.message || "Request failed";
    toast.error(msg);
    return Promise.reject(error);
  }
);

export const endpoints = {
  health: () => api.get("/"),
  catalog: () => api.get("/catalog"),
  eda: () => api.get("/eda"),
  models: () => api.get("/models"),
  experiments: () => api.get("/experiments"),
  forecast: (store, item, horizon = 28) =>
    api.get("/forecast", { params: { store, item, horizon } }),
  explain: (store, item) => api.get("/explain", { params: { store, item } }),
  inventory: (store, item, leadTime, serviceLevel, onHand = 0) =>
    api.get("/inventory", {
      params: {
        store,
        item,
        lead_time: leadTime,
        service_level: serviceLevel,
        on_hand: onHand,
      },
    }),
  inventoryAlerts: (leadTime = 7, serviceLevel = 0.95) =>
    api.get("/inventory/alerts", {
      params: { lead_time: leadTime, service_level: serviceLevel },
    }),
  drift: () => api.get("/drift"),
  modelCard: () => api.get("/model-card"),
};
