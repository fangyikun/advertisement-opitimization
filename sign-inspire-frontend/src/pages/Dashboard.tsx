import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  parseRule,
  createRule,
  updateRule,
  deleteRule,
  getRules,
  resetRules,
  getCurrentContentByStore,
  getWeather,
  checkRules,
} from '../api/client';
import { config } from '../config';
import { Sparkles, Save, Clock, CloudRain, Calendar, PlaySquare, List, Monitor, RefreshCw, Trash2, Store, Thermometer, Globe } from 'lucide-react';

// --- 类型定义 (对应后端的 Schema) ---
interface Condition {
  type: 'weather' | 'time' | 'holiday' | 'temp' | 'region' | 'city' | 'day' | 'china_region' | 'solar_term';
  operator: string;
  value: string;
}

interface Action {
  type: 'switch_playlist';
  target_id: string;
  message?: string;
}

interface Rule {
  id?: string;
  store_id?: string;
  name: string;
  priority: number;
  conditions: Condition[];
  action: Action;
  matches_current?: boolean;
}

interface WeatherContext {
  weather: string;
  temp_c?: number | null;
  region?: string | null;
  china_subregion?: string | null;
  solar_terms?: string[] | null;
  season?: string | null;
  hour?: number | null;
  weekday?: number | null;
  updated_at: string | null;
}

interface RecommendedStore {
  name: string;
  address: string;
  latitude?: number;
  longitude?: number;
  type?: string;
  photos?: string[];
  google_maps_uri?: string;
}

const DASHBOARD_CITIES = ['Adelaide', 'Shanghai', 'Beijing', 'Guangzhou', 'Shenzhen', 'Hangzhou', 'Tokyo', 'London', 'Singapore', 'New York'];

const TARGET_LABEL: Record<string, string> = {
  coffee_ad: '咖啡店', coffee_ads: '咖啡店', hot_drink_ad: '热饮/咖啡馆', sunscreen_ad: '药妆/防晒',
  xigua_ad: '果蔬/冷饮', bingxigua_ad: '冰品店', sushi_ad: '寿司/日料', shousi_ad: '寿司/日料',
  bbq_ad: 'BBQ/烧烤', fish_chips_ad: '炸鱼薯条', pizza_ad: '披萨', asian_soup_ad: '叻沙/拉面/河粉',
  green_bean_soup_ad: '绿豆沙/糖水', herbal_tea_ad: '凉茶', congee_ad: '砂锅粥', crayfish_ad: '小龙虾',
  dumplings_ad: '饺子', tangyuan_ad: '汤圆', bubble_tea_ad: '奶茶', cold_noodles_ad: '冷面',
  lamb_hotpot_ad: '铜锅涮肉/羊汤', iron_pot_stew_ad: '铁锅炖', hairy_crab_ad: '大闸蟹',
  vietnamese_ad: '越南米纸卷/檬粉', burger_ad: '炸鸡排/汉堡/塔可', default: '咖啡馆',
};

export default function Dashboard() {
  const STORE_ID = config.defaultStoreId;
  const [dashboardCity, setDashboardCity] = useState(config.defaultCity);
  
  // 状态管理
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [generatedRule, setGeneratedRule] = useState<Rule | null>(null);
  const [activeRules, setActiveRules] = useState<Rule[]>([]);
  const [isLoadingRules, setIsLoadingRules] = useState(false);
  const [weatherContext, setWeatherContext] = useState<WeatherContext>({
    weather: 'unknown',
    temp_c: null,
    region: null,
    updated_at: null
  });
  const [currentPlaylist, setCurrentPlaylist] = useState<string>('');
  const [editingPriorities, setEditingPriorities] = useState<Record<string, number>>({});

  // 获取规则列表（按当前城市计算适用性）
  const fetchRules = async () => {
    setIsLoadingRules(true);
    try {
      const res = await getRules(STORE_ID, dashboardCity);
      const data = res.data;
      const rules = Array.isArray(data) ? data : (data?.rules || []);
      const ctx = data?.context;
      if (ctx) {
        setWeatherContext((prev) => ({
          ...prev,
          weather: ctx.weather,
          temp_c: ctx.temp_c,
          region: ctx.region,
          china_subregion: ctx.china_subregion ?? null,
          solar_terms: ctx.solar_terms ?? null,
          season: ctx.season ?? null,
          hour: ctx.hour ?? null,
          weekday: ctx.weekday ?? null,
        }));
      }
      setActiveRules(rules);
    } catch (error) {
      console.error("获取规则列表失败:", error);
    } finally {
      setIsLoadingRules(false);
    }
  };

  // 获取当前播放内容（规则检查结果）
  const fetchCurrentContent = async () => {
    try {
      const res = await getCurrentContentByStore(STORE_ID);
      setCurrentPlaylist(res.data.content || 'default');
    } catch {
      setCurrentPlaylist('');
    }
  };

  // 获取天气状态（门店位置 Adelaide；切换城市时由 fetchRules 的 context 更新）
  const fetchWeather = async () => {
    try {
      const res = await getWeather();
      setWeatherContext((prev) => {
        if (dashboardCity === config.defaultCity) return { ...prev, ...res.data };
        return prev;
      });
    } catch (error) {
      console.error("获取天气状态失败:", error);
    }
  };

  // 组件加载时获取规则列表、天气和当前播放
  useEffect(() => {
    fetchRules();
    fetchWeather();
    fetchCurrentContent();

    const interval = setInterval(() => {
      fetchWeather();
      fetchCurrentContent();
    }, 30000);

    return () => clearInterval(interval);
  }, [dashboardCity]);

  // 1. 调用 AI 生成规则
  const handleGenerate = async () => {
    if (!inputText) return;
    setIsLoading(true);
    setGeneratedRule(null); // 清空旧结果
    
    try {
      const res = await parseRule(STORE_ID, inputText);
      
      console.log("AI 返回结果:", res.data);
      setGeneratedRule(res.data); // 将真实数据渲染到界面

    } catch (error) {
      alert("请求失败！请检查：\n1. 后端是否启动？\n2. API Key 是否配置？");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  // 2. 保存规则
  const handleSave = async () => {
    if (!generatedRule) return;
    
    try {
      await createRule(STORE_ID, generatedRule);
      await checkRules(STORE_ID).catch(() => {});
      await fetchCurrentContent();
      
      // 刷新规则列表
      await fetchRules();
      
      // 清空表单
      setGeneratedRule(null);
      setInputText("");
      
      // 显示成功提示
      alert(`规则 "${generatedRule.name}" 已保存并生效！`);
    } catch (error) {
      console.error("保存规则失败:", error);
      alert("保存规则失败，请检查后端服务是否正常运行");
    }
  };

  // 更新规则优先级
  const handleUpdatePriority = async (rule: Rule, newPriority: number) => {
    if (!rule.id) return;
    const clamped = Math.max(1, Math.min(10, newPriority));
    try {
      await updateRule(STORE_ID, rule.id, { priority: clamped });
      await fetchRules();
      await checkRules(STORE_ID).catch(() => {});
      await fetchCurrentContent();
    } catch (error) {
      console.error("更新优先级失败:", error);
      alert("更新优先级失败");
    }
  };

  // 恢复默认规则（清空并重新写入全球规则种子）
  const [resettingRules, setResettingRules] = useState(false);
  const handleResetRules = async () => {
    if (!confirm('确定要恢复默认规则吗？将清空当前所有规则并写入澳洲+中国城市规则。')) return;
    setResettingRules(true);
    try {
      await resetRules(STORE_ID);
      await fetchRules();
      await checkRules(STORE_ID).catch(() => {});
      await fetchCurrentContent();
      alert('已恢复默认规则');
    } catch (e: unknown) {
      console.error('恢复默认规则失败:', e);
      const msg = typeof e === 'object' && e != null && 'response' in e
        ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      alert(msg ? `恢复失败：${typeof msg === 'string' ? msg : JSON.stringify(msg)}` : '恢复默认规则失败');
    } finally {
      setResettingRules(false);
    }
  };

  // 删除规则
  const handleDeleteRule = async (rule: Rule) => {
    if (!rule.id) return;
    if (!confirm(`确定要删除规则「${rule.name}」吗？`)) return;
    try {
      await deleteRule(STORE_ID, rule.id);
      await fetchRules();
      await checkRules(STORE_ID).catch(() => {});
      await fetchCurrentContent();
    } catch (error: unknown) {
      console.error("删除规则失败:", error);
      const msg = typeof error === 'object' && error != null && 'response' in error
        ? (error as { response?: { data?: { detail?: string }; status?: number } }).response?.data?.detail
        : null;
      alert(msg ? `删除失败：${typeof msg === 'string' ? msg : JSON.stringify(msg)}` : "删除规则失败");
    }
  };

  // 点击规则标签：跳转到门店页面，展示该品类前十家店
  const navigate = useNavigate();
  const handleTagClick = (targetId: string) => {
    navigate(`/stores?city=${encodeURIComponent(dashboardCity)}&target_id=${encodeURIComponent(targetId)}`);
  };

  // 根据当前城市只显示该地域且匹配当前天气/温度/日期的规则
  const displayedRules = (() => {
    const conds = (r: Rule) => r.conditions || [];
    const hasWestern = (r: Rule) => conds(r).some((c) => c.type === 'region' && c.value === 'western');
    const hasEastAsia = (r: Rule) => conds(r).some((c) => c.type === 'region' && c.value === 'east_asia');
    const hasChinaRegion = (r: Rule) => conds(r).some((c) => c.type === 'china_region');
    const getChinaRegionValue = (r: Rule) => conds(r).find((c) => c.type === 'china_region')?.value;
    const hasSolarTerm = (r: Rule) => conds(r).some((c) => c.type === 'solar_term');

    const sub = weatherContext.china_subregion;
    const isAustralia = weatherContext.region === 'western' && !sub;

    let byRegion: Rule[] = [];
    if (isAustralia) byRegion = activeRules.filter((r) => hasWestern(r) && !hasChinaRegion(r) && !hasSolarTerm(r));
    else if (sub === 'east_china' || sub === 'south_china' || sub === 'north_china') {
      byRegion = activeRules.filter((r) => {
        const cr = getChinaRegionValue(r);
        if (cr) return cr === sub;
        if (hasSolarTerm(r)) return true;
        if (hasEastAsia(r)) return true;
        return false;
      });
    } else if (weatherContext.region === 'east_asia') {
      byRegion = activeRules.filter((r) => hasEastAsia(r) || hasChinaRegion(r) || hasSolarTerm(r));
    } else byRegion = activeRules;

    // 仅展示匹配当前天气/温度/日期的规则
    return byRegion.filter((r) => r.matches_current === true);
  })();

  // 前五个最优先级的适用规则（按 priority 降序，同 target_id 去重取首条）
  const top5Tags = (() => {
    const matched = displayedRules
      .filter((r) => r.matches_current === true && r.action?.target_id)
      .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0));
    const seen = new Set<string>();
    const out: { target_id: string; name: string; label: string; message?: string }[] = [];
    for (const r of matched) {
      const tid = r.action.target_id;
      if (!seen.has(tid) && out.length < 5) {
        seen.add(tid);
        out.push({
          target_id: tid,
          name: r.name,
          label: TARGET_LABEL[tid] ?? tid,
          message: r.action?.message,
        });
      }
    }
    return out;
  })();

  // 主推送语：当前最高优先级规则的 message（取中文部分）
  const heroPushMessage = (() => {
    const top = displayedRules
      .filter((r) => r.matches_current === true && r.action?.message)
      .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0))[0];
    if (!top?.action?.message) return null;
    const parts = top.action.message.split(/\s*\/\s*/).filter(Boolean);
    return parts.find((p) => /[\u4e00-\u9fff]/.test(p)) || parts[0] || null;
  })();

  // 手动触发规则检查
  const handleCheckRules = async () => {
    try {
      const res = await checkRules(STORE_ID);
      setCurrentPlaylist(res.data.current_playlist || 'default');
      alert(`规则检查完成！\n当前播放: ${res.data.current_playlist}\n当前天气: ${res.data.current_weather}`);
    } catch (error) {
      console.error("触发规则检查失败:", error);
      alert("触发规则检查失败，请检查后端服务是否正常运行");
    }
  };

  const weatherLabel = ['rain','sunny','cloudy','snow','storm','fog'].includes(weatherContext.weather)
    ? { rain: '雨', sunny: '晴', cloudy: '云', snow: '雪', storm: '雷', fog: '雾' }[weatherContext.weather]
    : '—';
  const seasonLabel: Record<string, string> = { spring: '春', summer: '夏', autumn: '秋', winter: '冬' };
  const regionLabel: Record<string, string> = { western: '欧美澳', east_asia: '东亚', tropical: '热带', uk: '英伦', south_china: '华南', east_china: '华东', north_china: '华北' };
  const dayLabel: Record<string, string> = { '0': '周一', '1': '周二', '2': '周三', '3': '周四', '4': '周五', '5': '周六', '6': '周日', 'fri,sat,sun': '五六日', fri: '周五', sun: '周日', wed: '周三' };

  return (
    <div className="min-h-screen p-6 sm:p-10 lg:p-16">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <header className="mb-12">
          <div className="flex justify-between items-start flex-wrap gap-4 mb-8">
            <h1 className="font-elegant text-4xl sm:text-5xl font-semibold text-ink-800 tracking-tight">
              灵犀
            </h1>
            <div className="flex gap-3">
              <Link
                to="/stores"
                className="flex items-center gap-2 px-4 py-2.5 bg-ink-800 text-cream-100 rounded-sm hover:bg-ink-700 transition-colors font-body text-sm"
              >
                <Store className="w-4 h-4" />
                门店推荐
              </Link>
              <Link
                to="/player"
                className="flex items-center gap-2 px-4 py-2.5 bg-cream-200/80 text-ink-800 rounded-sm hover:bg-stone-400/20 transition-colors font-body text-sm border border-stone-300/60"
              >
                <Monitor className="w-4 h-4" />
                播放
              </Link>
            </div>
          </div>
          <p className="font-body text-stone-600 italic text-lg">用自然语言，让智能随天气与时间流转</p>
        </header>

        {/* 主推送语 Hero - 当前最高优先级规则的推送语 */}
        {heroPushMessage && (
          <section className="mb-8 p-6 bg-accent-50/60 border border-accent-200/60 rounded-sm shadow-soft">
            <p className="font-elegant text-xl sm:text-2xl text-ink-800 leading-relaxed text-center italic">
              「{heroPushMessage}」
            </p>
            <p className="font-body text-stone-500 text-sm text-center mt-2">当前匹配规则 · 今日主推送语</p>
          </section>
        )}

        {/* 天气状态栏 + 城市选择 */}
        <section className="mb-10 p-5 bg-cream-50/80 border border-stone-300/80 rounded-sm shadow-soft">
          <div className="flex items-center justify-between flex-wrap gap-4 mb-3">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-cream-200/80 flex items-center justify-center border border-stone-300/50">
                <CloudRain className="w-6 h-6 text-stone-600" />
              </div>
              <div>
                <p className="font-elegant text-xl text-ink-800">
                  {weatherLabel}
                  {weatherContext.temp_c != null && <span className="font-body ml-1"> {Math.round(weatherContext.temp_c)}°C</span>}
                  {weatherContext.season && <span className="font-body text-ink-700 ml-1"> · {seasonLabel[weatherContext.season] || weatherContext.season}</span>}
                </p>
                <p className="font-body text-stone-600 text-sm mt-1">
                  {dashboardCity}
                  {weatherContext.china_subregion ? ` · ${regionLabel[weatherContext.china_subregion] || weatherContext.china_subregion}` : weatherContext.region ? ` · ${regionLabel[weatherContext.region] || weatherContext.region}` : ''}
                  {weatherContext.solar_terms?.length ? ` · ${weatherContext.solar_terms.join('、')}` : ''}
                  {' · 当前天气与季节'}
                </p>
              </div>
            {currentPlaylist && (
              <span className="px-3 py-1.5 bg-ink-800/5 text-ink-700 rounded-sm font-body text-sm border border-stone-300/50">
                播放: {currentPlaylist}
              </span>
            )}
            </div>
            <div className="flex items-center gap-3">
            {weatherContext.updated_at && (
              <span className="font-body text-stone-500 text-sm">
                {new Date(weatherContext.updated_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <button
              onClick={handleCheckRules}
              className="px-4 py-2 bg-ink-800 text-cream-100 rounded-sm hover:bg-ink-700 text-sm font-body flex items-center gap-2 transition-colors"
              title="立即检查规则"
            >
              <RefreshCw className="w-4 h-4" />
              检查规则
            </button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 pt-3 border-t border-stone-300/50 mt-3">
            <span className="font-body text-stone-500 text-sm">查看规则适用城市：</span>
            {DASHBOARD_CITIES.map((c) => (
              <button
                key={c}
                onClick={() => setDashboardCity(c)}
                className={`px-3 py-1.5 rounded-sm font-body text-sm transition-all ${
                  dashboardCity === c ? 'bg-ink-800 text-cream-100' : 'bg-cream-200/60 text-ink-700 hover:bg-stone-400/20'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
          {top5Tags.length > 0 && (
            <div className="pt-4 mt-3 border-t border-stone-300/50">
              <span className="font-body text-stone-500 text-sm">今日推荐 · 点击查看门店：</span>
              <div className="flex flex-wrap gap-3 mt-2">
                {top5Tags.map((t) => {
                  const msgParts = t.message ? t.message.split(/\s*\/\s*/).filter(Boolean) : [];
                  const msgCn = msgParts.find((p) => /[\u4e00-\u9fff]/.test(p)) || msgParts[0];
                  return (
                    <div key={t.target_id} className="flex flex-col gap-1">
                      <button
                        onClick={() => handleTagClick(t.target_id)}
                        className="px-4 py-2 rounded-sm font-body text-sm bg-accent-500/15 text-accent-700 border border-accent-400/40 hover:bg-accent-500/25 hover:border-accent-500/60 transition-all disabled:opacity-60 text-left"
                        title={msgCn || undefined}
                      >
                        {t.label}
                      </button>
                      {msgCn && (
                        <span className="font-body text-xs text-stone-500 max-w-[180px] line-clamp-2 pl-1">
                          {msgCn}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        {/* 输入区域 */}
        <section className="mb-10 p-6 bg-cream-50 border border-stone-300/80 rounded-sm shadow-soft">
          <label className="block font-elegant text-lg text-ink-700 mb-4">描述你的播放策略</label>
          <div className="flex gap-3">
            <input
              type="text"
              className="flex-1 bg-cream-100 border border-stone-300 rounded-sm px-4 py-3 focus:outline-none focus:ring-1 focus:ring-accent-500 focus:border-accent-500 font-body text-ink-800 placeholder-stone-400"
              placeholder="若下雨，则切换到热饮广告..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
            />
            <button
              onClick={handleGenerate}
              disabled={isLoading}
              className={`px-6 py-3 rounded-sm font-body font-medium flex items-center gap-2 transition-all ${
                isLoading ? 'bg-stone-400 text-cream-100 cursor-not-allowed' : 'bg-ink-800 text-cream-100 hover:bg-ink-700'
              }`}
            >
              {isLoading ? (
                <>
                  <span className="w-4 h-4 border-2 border-cream-100/30 border-t-cream-100 rounded-full animate-spin" />
                  解析中
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" /> 生成
                </>
              )}
            </button>
          </div>
        </section>

        {/* AI 解析结果 */}
        {generatedRule && (
          <div className="mb-12 bg-cream-50 border border-stone-300/80 rounded-sm overflow-hidden shadow-elegant">
            <div className="px-6 py-4 border-b border-stone-300/60 flex justify-between items-center flex-wrap gap-3 bg-cream-200/30">
              <h3 className="font-elegant text-xl text-ink-800 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-accent-600" /> 解析结果
              </h3>
              <div className="flex items-center gap-2">
                <label className="font-body text-sm text-stone-600">优先级</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={generatedRule.priority}
                  onChange={(e) => setGeneratedRule({
                    ...generatedRule,
                    priority: Math.max(1, Math.min(10, parseInt(e.target.value, 10) || 1))
                  })}
                  className="w-12 border border-stone-300 rounded-sm px-2 py-1 text-center font-body text-ink-800 bg-cream-50"
                  title="数字越大越优先"
                />
              </div>
            </div>

            <div className="p-6 grid gap-6">
              <div className="flex items-start gap-4">
                <span className="font-elegant text-lg text-accent-600 bg-accent-400/10 px-3 py-1.5 rounded-sm">若</span>
                <div className="flex-1 space-y-2">
                  {generatedRule.conditions.map((cond, idx) => (
                    <div key={idx} className="flex items-center gap-3 bg-cream-100/80 p-3 rounded-sm border border-stone-300/50">
                      {cond.type === 'weather' && <CloudRain className="w-4 h-4 text-stone-500"/>}
                      {cond.type === 'time' && <Clock className="w-4 h-4 text-stone-500"/>}
                      {cond.type === 'holiday' && <Calendar className="w-4 h-4 text-stone-500"/>}
                      {cond.type === 'temp' && <Thermometer className="w-4 h-4 text-stone-500"/>}
                      {cond.type === 'region' && <Globe className="w-4 h-4 text-stone-500"/>}
                      {cond.type === 'time' && <Clock className="w-4 h-4 text-stone-500"/>}
                      {cond.type === 'day' && <Calendar className="w-4 h-4 text-stone-500"/>}
                      <span className="font-body text-stone-600">{cond.type === 'temp' ? '温度' : cond.type === 'region' ? '文化圈' : cond.type === 'china_region' ? '地域' : cond.type === 'solar_term' ? '节气' : cond.type === 'time' ? '时段' : cond.type === 'day' ? '星期' : cond.type}</span>
                      <span className="text-stone-400 text-sm font-mono">{cond.operator}</span>
                      <span className="font-body font-medium text-ink-800 bg-cream-50 px-2 py-0.5 rounded-sm border border-stone-300/50">
                        {cond.type === 'region' || cond.type === 'china_region' ? (regionLabel[cond.value] || cond.value) : cond.type === 'day' ? (dayLabel[cond.value] || cond.value) : cond.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex justify-center text-stone-400 font-elegant">↓</div>
              <div className="flex items-start gap-4">
                <span className="font-elegant text-lg text-ink-700 bg-ink-800/5 px-3 py-1.5 rounded-sm">则</span>
                <div className="flex-1">
                  <div className="flex items-center gap-3 bg-cream-100/80 p-4 rounded-sm border border-stone-300/50">
                    <PlaySquare className="w-5 h-5 text-accent-600"/>
                    <span className="font-body text-stone-600">播放</span>
                    <span className="font-elegant text-lg text-ink-800">{generatedRule.action.target_id}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="px-6 py-4 flex justify-end gap-3 border-t border-stone-300/50 bg-cream-100/30">
              <button onClick={() => setGeneratedRule(null)} className="px-4 py-2 font-body text-stone-600 hover:text-ink-800 transition-colors">
                取消
              </button>
              <button 
                onClick={handleSave}
                className="px-6 py-2 bg-ink-800 text-cream-100 rounded-sm hover:bg-ink-700 font-body flex items-center gap-2 transition-colors"
              >
                <Save className="w-4 h-4" /> 确认并生效
              </button>
            </div>
          </div>
        )}

        {/* 当前生效规则 */}
        <section className="mt-12">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="font-elegant text-2xl text-ink-800 mb-2">当前规则</h2>
              <p className="font-body text-stone-600 text-sm">仅展示匹配当前天气、温度、日期的规则 · 同条件下标高优先</p>
            </div>
            <button
              onClick={handleResetRules}
              disabled={resettingRules}
              className="px-4 py-2 font-body text-sm bg-cream-200/80 text-ink-700 border border-stone-300/60 rounded-sm hover:bg-stone-300/30 disabled:opacity-60 transition-colors"
            >
              {resettingRules ? '恢复中…' : '恢复默认规则'}
            </button>
          </div>

          {displayedRules.length === 0 ? (
            <div className="p-12 bg-cream-50/60 border border-stone-300/60 rounded-sm text-center">
              <List className="w-10 h-10 text-stone-300 mx-auto mb-3" />
              <p className="font-body text-stone-500">当前天气下暂无匹配规则</p>
              <p className="font-body text-stone-400 text-sm mt-1">可切换城市、或点击「恢复默认规则」获取完整规则库</p>
            </div>
          ) : (
            <>
            <div className="space-y-4">
              {[...displayedRules]
                .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0))
                .map((rule) => (
                <article
                  key={rule.id || rule.name}
                  className="bg-cream-50 border border-stone-300/80 rounded-sm overflow-hidden hover:shadow-elegant transition-all duration-300"
                >
                  <div className={`px-6 py-4 border-b border-stone-300/60 flex justify-between items-center flex-wrap gap-3 ${rule.matches_current ? 'bg-accent-50/50 border-l-4 border-l-accent-500' : 'bg-cream-200/20'}`}>
                    <h3 className="font-elegant text-xl text-ink-800 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-accent-600" />
                      {rule.name}
                      {rule.matches_current && (
                        <span className="px-2 py-0.5 bg-accent-500/20 text-accent-700 rounded text-xs font-body">适用当前</span>
                      )}
                    </h3>
                    <div className="flex items-center gap-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <label className="font-body text-xs text-stone-500">优先级</label>
                        <input
                          type="number"
                          min={1}
                          max={10}
                          value={editingPriorities[rule.id!] ?? rule.priority}
                          onChange={(e) => {
                            const v = parseInt(e.target.value, 10);
                            if (!isNaN(v) && rule.id) {
                              setEditingPriorities((p) => ({ ...p, [rule.id!]: Math.max(1, Math.min(10, v)) }));
                            }
                          }}
                          onBlur={() => {
                            const v = editingPriorities[rule.id!] ?? rule.priority;
                            if (rule.id && v !== rule.priority) {
                              handleUpdatePriority(rule, v);
                              setEditingPriorities((p) => {
                                const next = { ...p };
                                delete next[rule.id!];
                                return next;
                              });
                            }
                          }}
                          onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
                          className="w-11 border border-stone-300 rounded-sm px-1.5 py-0.5 text-center font-body text-sm bg-cream-50"
                        />
                      </div>
                      <button
                        onClick={() => handleDeleteRule(rule)}
                        className="p-1.5 text-stone-500 hover:text-red-600 hover:bg-red-50/50 rounded-sm transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="p-6 grid gap-4">
                    <div className="flex items-start gap-4">
                      <span className="font-elegant text-base text-accent-600 bg-accent-400/10 px-2.5 py-1 rounded-sm shrink-0">若</span>
                      <div className="flex-1 space-y-2">
                        {rule.conditions.map((cond, idx) => (
                          <div key={idx} className="flex items-center gap-3 bg-cream-100/60 p-3 rounded-sm border border-stone-300/40">
                            {cond.type === 'weather' && <CloudRain className="w-4 h-4 text-stone-500" />}
                            {cond.type === 'time' && <Clock className="w-4 h-4 text-stone-500" />}
                            {cond.type === 'holiday' && <Calendar className="w-4 h-4 text-stone-500" />}
                            {cond.type === 'temp' && <Thermometer className="w-4 h-4 text-stone-500" />}
                            {cond.type === 'region' && <Globe className="w-4 h-4 text-stone-500" />}
                            <span className="font-body text-stone-600">{cond.type === 'temp' ? '温度' : cond.type === 'region' ? '文化圈' : cond.type === 'china_region' ? '地域' : cond.type === 'solar_term' ? '节气' : cond.type}</span>
                            <span className="text-stone-400 text-sm font-mono">{cond.operator}</span>
                            <span className="font-body font-medium text-ink-800 bg-cream-50 px-2 py-0.5 rounded-sm border border-stone-300/50">
                              {cond.type === 'region' || cond.type === 'china_region' ? (regionLabel[cond.value] || cond.value) : cond.type === 'solar_term' ? cond.value : cond.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="flex justify-center text-stone-400 font-elegant">↓</div>
                    <div className="flex items-start gap-4">
                      <span className="font-elegant text-base text-ink-700 bg-ink-800/5 px-2.5 py-1 rounded-sm shrink-0">则</span>
                      <div className="flex-1">
                        <div className="flex flex-col gap-2 bg-cream-100/60 p-4 rounded-sm border border-stone-300/40">
                          <div className="flex items-center gap-3">
                            <PlaySquare className="w-5 h-5 text-accent-600 shrink-0" />
                            <span className="font-body text-stone-600">播放</span>
                            <span className="font-elegant text-lg text-ink-800">{rule.action.target_id}</span>
                          </div>
                          {rule.action?.message && (
                            <div className="font-body text-sm text-stone-600 italic border-l-2 border-accent-400/50 pl-3 space-y-1">
                              {rule.action.message.split(/\s*\/\s*/).filter(Boolean).map((line, i) => (
                                <p key={i}>{line}</p>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
            {displayedRules.length <= 2 && (
              <div className="mt-6 p-4 bg-amber-50/80 border border-amber-200/80 rounded-sm">
                <p className="font-body text-amber-800 text-sm">💡 规则较少？点击「恢复默认规则」可加载澳洲多云专项、中国节气等完整规则库</p>
              </div>
            )}
            </>
          )}
        </section>

      </div>
    </div>
  );
}
