import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Home } from 'lucide-react';
import { config } from '../config';
import { getRecommendations } from '../api/client';

const API_BASE = config.apiBaseUrl;

const PLACEHOLDER =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'%3E%3Crect fill='%231e293b' width='1920' height='1080'/%3E%3Ctext x='50%25' y='50%25' fill='%2394a3b8' font-size='24' text-anchor='middle' dy='.3em' font-family='sans-serif'%3E灵犀 · 智能推送%3C/text%3E%3C/svg%3E";

const SLIDE_INTERVAL_MS = 8000;
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

function Player() {
  const [searchParams] = useSearchParams();
  const cityParam = searchParams.get('city') || '';
  const targetIdParam = searchParams.get('target_id') || '';
  const storeId = searchParams.get('store') || config.defaultStoreId;
  const signId = searchParams.get('sign') || '';
  const useGeo = searchParams.get('geo') === '1';

  const [mode, setMode] = useState<'city' | 'store'>('city');
  const [city, setCity] = useState(cityParam || config.defaultCity);
  const [userLocation, setUserLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [slides, setSlides] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 获取 target_id 对应的品类图片（商家无图时兜底）
  const fetchCategoryImage = useCallback(async (targetId: string): Promise<string> => {
    try {
      const res = await axios.get<{ url: string }>(
        `${API_BASE}/stores/${storeId}/media/${encodeURIComponent(targetId)}`
      );
      return res.data?.url || '';
    } catch {
      return '';
    }
  }, [storeId]);

  // 城市模式：根据天气规则获取推荐门店，收集所有商家照片轮播
  const fetchCitySlides = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = userLocation
        ? await getRecommendations(15, city, userLocation.lat, userLocation.lon, targetIdParam || undefined)
        : await getRecommendations(15, city, undefined, undefined, targetIdParam || undefined);
      const data = res.data;

      let urls: string[] = [];
      for (const store of data.stores || []) {
        const photos = store.photos || [];
        if (photos.length > 0) {
          urls = urls.concat(photos);
        }
      }

      if (urls.length === 0 && data.target_id) {
        const catUrl = await fetchCategoryImage(data.target_id);
        if (catUrl) urls = [catUrl];
      }
      if (urls.length === 0) {
        urls = [await fetchCategoryImage('coffee_ad')].filter(Boolean);
      }
      if (urls.length === 0) urls = [PLACEHOLDER];

      setSlides(urls);
      setCurrentIndex(0);
    } catch (e) {
      console.error('获取推荐失败:', e);
      setError('获取推荐失败');
      setSlides([PLACEHOLDER]);
    } finally {
      setLoading(false);
    }
  }, [city, userLocation, targetIdParam, fetchCategoryImage]);

  // 门店/屏幕模式：沿用原有逻辑
  const [storeContent, setStoreContent] = useState<string>('default');
  const [storeImageUrl, setStoreImageUrl] = useState<string>(PLACEHOLDER);
  const storeContentRef = useRef<string>('default');

  const fetchStoreContent = useCallback(async () => {
    try {
      const url = signId
        ? `${API_BASE}/signs/${signId}/current-content`
        : `${API_BASE}/stores/${storeId}/current-content`;
      const res = await axios.get<{ content: string }>(url);
      const content = res.data?.content || 'default';
      if (content !== storeContentRef.current) {
        storeContentRef.current = content;
        const mediaRes = await axios.get<{ url: string }>(
          `${API_BASE}/stores/${storeId}/media/${encodeURIComponent(content)}`
        );
        setStoreImageUrl(mediaRes.data?.url || PLACEHOLDER);
        setStoreContent(content);
      }
    } catch (e) {
      console.error('获取门店内容失败:', e);
    }
  }, [storeId, signId]);

  useEffect(() => {
    if (cityParam) setCity(cityParam);
  }, [cityParam]);

  // 可选：?geo=1 时使用浏览器定位
  useEffect(() => {
    if (!useGeo || !navigator.geolocation || mode !== 'city') return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => {},
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 300000 }
    );
  }, [useGeo, mode]);

  useEffect(() => {
    if (signId || searchParams.has('store')) {
      setMode('store');
    } else {
      setMode('city');
    }
  }, [signId, searchParams]);

  useEffect(() => {
    if (mode === 'store') {
      fetchStoreContent();
      const t = setInterval(fetchStoreContent, 2000);
      return () => clearInterval(t);
    }
  }, [mode, fetchStoreContent]);

  useEffect(() => {
    if (mode === 'city') {
      fetchCitySlides();
      const refreshT = setInterval(fetchCitySlides, REFRESH_INTERVAL_MS);
      return () => clearInterval(refreshT);
    }
  }, [mode, city, userLocation, targetIdParam, fetchCitySlides]);

  // 城市模式：轮播
  useEffect(() => {
    if (mode !== 'city' || slides.length <= 1) return;
    intervalRef.current = setInterval(() => {
      setCurrentIndex((i) => (i + 1) % slides.length);
    }, SLIDE_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [mode, slides.length]);

  const imageUrl = mode === 'city' ? (slides[currentIndex] || PLACEHOLDER) : storeImageUrl;

  return (
    <div className="fixed inset-0 bg-black flex items-center justify-center overflow-hidden">
      <Link
        to="/"
        className="absolute top-4 left-4 z-10 flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg backdrop-blur-sm transition-colors"
      >
        <Home className="w-5 h-5" />
        返回管理
      </Link>

      {loading && mode === 'city' && slides.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60 z-20">
          <div className="w-10 h-10 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        </div>
      )}

      {error && mode === 'city' && (
        <div className="absolute top-16 left-4 right-4 bg-red-900/80 text-white px-4 py-2 rounded z-20 text-sm">
          {error} · 将使用默认内容
        </div>
      )}

      <img
        key={mode === 'city' ? currentIndex : storeContent}
        src={imageUrl}
        alt={mode === 'city' ? `推荐 ${currentIndex + 1}` : storeContent}
        className="w-full h-full object-contain transition-opacity duration-500"
        onError={(e) => {
          (e.target as HTMLImageElement).src = PLACEHOLDER;
        }}
      />
    </div>
  );
}

export default Player;
