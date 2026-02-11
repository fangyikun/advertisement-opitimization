import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Store, MapPin, ArrowLeft, Cloud, RefreshCw, AlertCircle, Globe, Navigation } from 'lucide-react';
import { getRecommendations } from '../api/client';

interface RecommendedStore {
  name: string;
  address: string;
  latitude?: number;
  longitude?: number;
  type?: string;
  photos?: string[];
  google_maps_uri?: string;
}

interface RecommendationData {
  weather: string;
  target_id: string;
  category_label: string;
  stores: RecommendedStore[];
  message: string;
  push_message?: string | null;
  city?: string;
}

const WEATHER_LABELS: Record<string, string> = {
  sunny: '晴',
  cloudy: '云',
  rain: '雨',
  snow: '雪',
  storm: '雷',
  fog: '雾',
};

const POPULAR_CITIES = ['Adelaide', 'Sydney', 'Melbourne', 'London', 'New York', 'Paris', 'Tokyo', 'Singapore', 'Shanghai'];

type UserLocation = { lat: number; lon: number };

export default function StoresPage() {
  const [searchParams] = useSearchParams();
  const urlCity = searchParams.get('city') || '';
  const urlTargetId = searchParams.get('target_id') || '';

  const [city, setCity] = useState(urlCity || 'Adelaide');
  const [targetId, setTargetId] = useState(urlTargetId || '');
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [data, setData] = useState<RecommendationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 同步 URL 参数到 state（从 Dashboard 标签跳转时）
  useEffect(() => {
    if (urlCity) setCity(urlCity);
    if (urlTargetId) setTargetId(urlTargetId);
  }, [urlCity, urlTargetId]);

  const fetchRecommendations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = userLocation
        ? await getRecommendations(10, city, userLocation.lat, userLocation.lon, targetId || undefined)
        : await getRecommendations(10, city, undefined, undefined, targetId || undefined);
      setData(res.data);
    } catch (e: unknown) {
      console.error(e);
      setData(null);
      let msg = '请求失败，请检查后端服务是否启动';
      if (axios.isAxiosError(e)) {
        msg = e.response?.data?.detail ?? e.message;
      } else if (e instanceof Error) {
        msg = e.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [city, userLocation, targetId]);

  const handleUseMyLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('您的浏览器不支持定位功能');
      return;
    }
    setLocationError(null);
    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setLocationLoading(false);
      },
      (err) => {
        setLocationLoading(false);
        if (err.code === 1) setLocationError('您已拒绝定位权限，可改用上方城市选择');
        else if (err.code === 2) setLocationError('无法获取位置，请检查网络或定位设置');
        else setLocationError('定位失败：' + (err.message || '未知错误'));
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  }, []);

  useEffect(() => {
    fetchRecommendations();
  }, [fetchRecommendations]);

  const weatherLabel = data ? WEATHER_LABELS[data.weather] || data.weather : '—';

  return (
    <div className="min-h-screen p-6 sm:p-10 lg:p-16">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <header className="mb-12">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-stone-600 hover:text-ink-800 transition-colors text-sm font-medium tracking-wide mb-8"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="font-body">返回</span>
          </Link>
          <h1 className="font-elegant text-4xl sm:text-5xl font-semibold text-ink-800 tracking-tight leading-tight">
            精选门店
          </h1>
          <p className="mt-3 font-body text-stone-600 text-lg italic">
            随天气与心情，发现城市的温度
          </p>
        </header>

        {/* 城市选择 / 当前位置 */}
        <section className="mb-10">
          <label className="block font-elegant text-lg text-ink-700 mb-4">
            {userLocation ? '正在使用您的位置' : '选择城市'}
          </label>
          {userLocation ? (
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-body text-stone-600 text-sm">
                根据您附近位置推荐 · {data?.city || '定位中...'}
              </span>
              <button
                onClick={() => { setUserLocation(null); setLocationError(null); }}
                className="px-4 py-2.5 rounded-sm font-body text-sm bg-cream-200/60 text-ink-700 hover:bg-stone-400/20 transition-all"
              >
                切换回城市选择
              </button>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap gap-3">
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && fetchRecommendations()}
                  placeholder="Sydney, London, Tokyo..."
                  className="flex-1 min-w-[160px] px-4 py-3 bg-cream-50 border border-stone-300 rounded-sm text-ink-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-accent-500 focus:border-accent-500 transition-colors font-body"
                />
                <button
                  onClick={handleUseMyLocation}
                  disabled={locationLoading}
                  className="flex items-center gap-2 px-5 py-3 bg-accent-600 text-cream-100 rounded-sm hover:bg-accent-500 disabled:opacity-60 transition-all font-body text-sm"
                >
                  <Navigation className={`w-4 h-4 ${locationLoading ? 'animate-pulse' : ''}`} />
                  {locationLoading ? '定位中…' : '使用当前位置'}
                </button>
              </div>
              <div className="flex flex-wrap gap-3 mt-3">
                {POPULAR_CITIES.map((c) => (
                  <button
                    key={c}
                    onClick={() => setCity(c)}
                    className={`px-4 py-2.5 rounded-sm font-body text-sm transition-all duration-200 ${
                      city === c
                        ? 'bg-ink-800 text-cream-100'
                        : 'bg-cream-200/60 text-ink-700 hover:bg-stone-400/20'
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </>
          )}
          {locationError && (
            <p className="mt-3 font-body text-sm text-amber-700">{locationError}</p>
          )}
        </section>

        {/* 推送语 Hero - 品类主推送语（从标签进入时展示） */}
        {data?.push_message && (
          <section className="mb-8 p-6 bg-accent-50/60 border border-accent-200/60 rounded-sm shadow-soft">
            <p className="font-elegant text-xl sm:text-2xl text-ink-800 leading-relaxed text-center italic">
              「{data.push_message.split(/\s*\/\s*/).filter(Boolean).find((p) => /[\u4e00-\u9fff]/.test(p)) || data.push_message}」
            </p>
            <p className="font-body text-stone-500 text-sm text-center mt-2">
              {data.category_label} · 精选推送语
            </p>
          </section>
        )}

        {/* 天气与状态 */}
        <section className="mb-10 p-6 bg-cream-50/80 border border-stone-300/80 rounded-sm shadow-soft">
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="flex items-center gap-5">
              <div className="w-14 h-14 rounded-full bg-cream-200/80 flex items-center justify-center border border-stone-300/50">
                <Cloud className="w-7 h-7 text-stone-600" />
              </div>
              <div>
                <p className="font-elegant text-xl text-ink-800">{weatherLabel}</p>
                <p className="font-body text-stone-600 text-sm mt-0.5">
                  {data?.city || city} · 当前天气
                </p>
              </div>
            </div>
            <button
              onClick={fetchRecommendations}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-ink-800 text-cream-100 rounded-sm hover:bg-ink-700 disabled:opacity-50 transition-all font-body text-sm tracking-wide"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </button>
          </div>
          {data && (
            <p className="mt-5 pt-5 border-t border-stone-300/50 font-body text-ink-700 text-[15px] leading-relaxed">
              {data.message}
            </p>
          )}
        </section>

        {error && (
          <div className="mb-10 p-5 bg-red-50/80 border border-red-200/80 rounded-sm flex items-center gap-4">
            <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
            <p className="font-body text-red-800 text-sm flex-1">{error}</p>
            <button
              onClick={fetchRecommendations}
              className="px-4 py-2 bg-red-100 hover:bg-red-200 rounded-sm font-body text-sm text-red-800"
            >
              重试
            </button>
          </div>
        )}

        {/* 门店列表 */}
        <section>
          <h2 className="font-elegant text-2xl text-ink-800 mb-6">
            {data?.category_label ? `为您精选 · ${data.category_label}` : '为您精选'}
          </h2>

          {loading ? (
            <div className="py-20 text-center">
              <div className="inline-block w-8 h-8 border-2 border-accent-500/30 border-t-accent-600 rounded-full animate-spin mb-4" />
              <p className="font-body text-stone-500">正在获取 {city} 的灵感...</p>
            </div>
          ) : !data || data.stores.length === 0 ? (
            <div className="py-20 text-center">
              <Globe className="w-12 h-12 text-stone-300 mx-auto mb-4" />
              <p className="font-body text-stone-500">
                {error ? '请解决上方问题后重试' : '暂无推荐，试试其他城市'}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {data.stores.map((s, i) => {
                const mapUrl = s.google_maps_uri || (s.latitude != null && s.longitude != null
                  ? `https://www.google.com/maps?q=${s.latitude},${s.longitude}`
                  : null);
                return (
                  <article
                    key={`${s.name}-${i}`}
                    className="group bg-cream-50 border border-stone-300/70 rounded-sm overflow-hidden hover:border-stone-400/60 hover:shadow-elegant transition-all duration-300"
                  >
                    <div className="flex flex-col sm:flex-row">
                      <div className="sm:w-52 shrink-0 bg-cream-200/50">
                        {s.photos && s.photos.length > 0 ? (
                          <div className="p-3">
                            <img
                              src={s.photos[0]}
                              alt={s.name}
                              loading="lazy"
                              className="w-full aspect-[4/3] object-cover rounded-sm"
                            />
                            {s.photos.length > 1 && (
                              <div className="flex gap-1.5 mt-2 overflow-x-auto">
                                {s.photos.slice(1, 5).map((url, j) => (
                                  <img
                                    key={j}
                                    src={url}
                                    alt=""
                                    loading="lazy"
                                    className="w-12 h-12 object-cover rounded-sm shrink-0 opacity-90"
                                  />
                                ))}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="aspect-[4/3] flex items-center justify-center">
                            <Store className="w-14 h-14 text-stone-300" />
                          </div>
                        )}
                      </div>
                      <div className="flex-1 p-5 min-w-0 flex flex-col justify-center">
                        <div className="flex items-start gap-4">
                          <span className="font-elegant text-2xl text-stone-400 tabular-nums shrink-0">
                            {String(i + 1).padStart(2, '0')}
                          </span>
                          <div className="min-w-0 flex-1">
                            <h3 className="font-elegant text-xl text-ink-800 group-hover:text-ink-900 transition-colors">
                              {s.name}
                            </h3>
                            <p className="font-body text-stone-600 text-sm mt-1.5 flex items-start gap-2">
                              <MapPin className="w-3.5 h-3.5 mt-0.5 shrink-0 text-stone-500" />
                              <span>{s.address}</span>
                            </p>
                            {mapUrl && (
                              <a
                                href={mapUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 mt-3 font-body text-sm text-accent-600 hover:text-accent-500 transition-colors"
                              >
                                查看地图 →
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <footer className="mt-14 pt-8 border-t border-stone-300/50">
          <p className="font-body text-stone-500 text-sm">
            随天气与规则智能推荐 · 数据来自 Google Places 与 OpenStreetMap
          </p>
        </footer>
      </div>
    </div>
  );
}
