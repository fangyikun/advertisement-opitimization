import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Sparkles, Save, Clock, CloudRain, Calendar, PlaySquare, List, Sun, Cloud, Monitor, RefreshCw, Trash2 } from 'lucide-react';

// --- 类型定义 (对应后端的 Schema) ---
interface Condition {
  type: 'weather' | 'time' | 'holiday';
  operator: string;
  value: string;
}

interface Action {
  type: 'switch_playlist';
  target_id: string;
}

interface Rule {
  id?: string;
  store_id?: string;
  name: string;
  priority: number;
  conditions: Condition[];
  action: Action;
}

interface WeatherContext {
  weather: string;
  updated_at: string | null;
}

export default function Dashboard() {
  const STORE_ID = 'store_001'; // 门店ID
  
  // 状态管理
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [generatedRule, setGeneratedRule] = useState<Rule | null>(null);
  const [activeRules, setActiveRules] = useState<Rule[]>([]);
  const [isLoadingRules, setIsLoadingRules] = useState(false);
  const [weatherContext, setWeatherContext] = useState<WeatherContext>({
    weather: 'unknown',
    updated_at: null
  });
  const [currentPlaylist, setCurrentPlaylist] = useState<string>('');
  const [editingPriorities, setEditingPriorities] = useState<Record<string, number>>({});

  // 获取当前生效的规则列表
  const fetchRules = async () => {
    setIsLoadingRules(true);
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/rules`);
      console.log("获取规则列表:", res.data);
      setActiveRules(res.data);
    } catch (error) {
      console.error("获取规则列表失败:", error);
      // 失败时不显示错误，避免影响用户体验
    } finally {
      setIsLoadingRules(false);
    }
  };

  // 获取当前播放内容（规则检查结果）
  const fetchCurrentContent = async () => {
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/current-content`);
      setCurrentPlaylist(res.data.content || 'default');
    } catch {
      setCurrentPlaylist('');
    }
  };

  // 获取天气状态
  const fetchWeather = async () => {
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/v1/weather`);
      console.log("获取天气状态:", res.data);
      setWeatherContext(res.data);
    } catch (error) {
      console.error("获取天气状态失败:", error);
      // 失败时不显示错误，避免影响用户体验
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
  }, []);

  // 1. 调用 AI 生成规则
  const handleGenerate = async () => {
    if (!inputText) return;
    setIsLoading(true);
    setGeneratedRule(null); // 清空旧结果
    
    try {
      // ✅ 真实调用：发送请求给 FastAPI
      // 注意：这里用了 query param (params: {text}) 对应后端的 text: str
      const res = await axios.post(`http://127.0.0.1:8000/api/v1/stores/store_001/rules:parse`, null, {
        params: { text: inputText }
      });
      
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
      // 调用真实的后端接口保存规则
      await axios.post(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/rules`, generatedRule);
      
      // 保存成功后立即触发规则检查并刷新当前播放
      await axios.post(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/check-rules`).catch(() => {});
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
      await axios.patch(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/rules/${rule.id}`, { priority: clamped });
      await fetchRules();
      await axios.post(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/check-rules`).catch(() => {});
      await fetchCurrentContent();
    } catch (error) {
      console.error("更新优先级失败:", error);
      alert("更新优先级失败");
    }
  };

  // 删除规则
  const handleDeleteRule = async (rule: Rule) => {
    if (!rule.id) return;
    if (!confirm(`确定要删除规则「${rule.name}」吗？`)) return;
    try {
      await axios.delete(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/rules/${rule.id}`);
      await fetchRules();
      await axios.post(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/check-rules`).catch(() => {});
      await fetchCurrentContent();
    } catch (error) {
      console.error("删除规则失败:", error);
      alert("删除规则失败");
    }
  };

  // 手动触发规则检查
  const handleCheckRules = async () => {
    try {
      const res = await axios.post(`http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/check-rules`);
      setCurrentPlaylist(res.data.current_playlist || 'default');
      alert(`规则检查完成！\n当前播放: ${res.data.current_playlist}\n当前天气: ${res.data.current_weather}`);
    } catch (error) {
      console.error("触发规则检查失败:", error);
      alert("触发规则检查失败，请检查后端服务是否正常运行");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800 font-sans p-8">
      <div className="max-w-3xl mx-auto">
        
        {/* Header */}
        <header className="mb-6 text-center">
          <div className="flex justify-between items-center mb-4">
            <div></div>
            <h1 className="text-4xl font-bold text-blue-600 flex justify-center items-center gap-3">
              <Sparkles className="w-8 h-8" />
              Sign Inspire 智能排期
            </h1>
            <Link
              to="/player"
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Monitor className="w-5 h-5" />
              播放页面
            </Link>
          </div>
          <p className="text-gray-500">让 AI 帮你配置数字标牌的播放策略</p>
        </header>

        {/* --- 实时环境状态栏 --- */}
        <div className={`mb-8 rounded-xl shadow-md p-4 flex items-center justify-between transition-all ${
          weatherContext.weather === 'rain' 
            ? 'bg-blue-100 border-2 border-blue-300' 
            : weatherContext.weather === 'sunny'
            ? 'bg-orange-100 border-2 border-orange-300'
            : weatherContext.weather === 'cloudy'
            ? 'bg-gray-100 border-2 border-gray-300'
            : weatherContext.weather === 'snow'
            ? 'bg-blue-50 border-2 border-blue-200'
            : weatherContext.weather === 'storm'
            ? 'bg-purple-100 border-2 border-purple-300'
            : 'bg-gray-50 border-2 border-gray-200'
        }`}>
          <div className="flex items-center gap-3">
            {weatherContext.weather === 'rain' && (
              <>
                <CloudRain className="w-6 h-6 text-blue-600" />
                <span className="text-lg font-semibold text-blue-800">雨天</span>
              </>
            )}
            {weatherContext.weather === 'sunny' && (
              <>
                <Sun className="w-6 h-6 text-orange-600" />
                <span className="text-lg font-semibold text-orange-800">晴天</span>
              </>
            )}
            {weatherContext.weather === 'cloudy' && (
              <>
                <Cloud className="w-6 h-6 text-gray-600" />
                <span className="text-lg font-semibold text-gray-800">多云</span>
              </>
            )}
            {weatherContext.weather === 'snow' && (
              <>
                <CloudRain className="w-6 h-6 text-blue-500" />
                <span className="text-lg font-semibold text-blue-700">雪天</span>
              </>
            )}
            {weatherContext.weather === 'storm' && (
              <>
                <CloudRain className="w-6 h-6 text-purple-600" />
                <span className="text-lg font-semibold text-purple-800">雷暴</span>
              </>
            )}
            {!['rain', 'sunny', 'cloudy', 'snow', 'storm'].includes(weatherContext.weather) && (
              <>
                <Cloud className="w-6 h-6 text-gray-500" />
                <span className="text-lg font-semibold text-gray-600">未知</span>
              </>
            )}
            <span className="text-sm text-gray-600 ml-2">
              (Adelaide)
            </span>
            {currentPlaylist && (
              <span className="text-sm font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded">
                当前播放: {currentPlaylist}
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-3">
            {weatherContext.updated_at && (
              <div className="text-sm text-gray-600">
                最后更新: {new Date(weatherContext.updated_at).toLocaleTimeString('zh-CN', { 
                  hour: '2-digit', 
                  minute: '2-digit',
                  second: '2-digit'
                })}
              </div>
            )}
            <button
              onClick={handleCheckRules}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
              title="立即检查规则并更新播放列表"
            >
              <RefreshCw className="w-4 h-4" />
              检查规则
            </button>
          </div>
        </div>

        {/* --- 输入区域 (Magic Input) --- */}
        <div className="bg-white p-6 rounded-xl shadow-lg mb-8 transition-all hover:shadow-xl">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            你想怎么安排播放内容？(自然语言)
          </label>
          <div className="flex gap-3">
            <input
              type="text"
              className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-lg"
              placeholder="例如：如果现在下雨，就把屏幕换成热饮广告..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
            />
            <button
              onClick={handleGenerate}
              disabled={isLoading}
              className={`px-8 py-3 rounded-lg font-bold text-white flex items-center gap-2 transition-colors ${
                isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {isLoading ? (
                '思考中...'
              ) : (
                <>
                  <Sparkles className="w-5 h-5" /> 生成
                </>
              )}
            </button>
          </div>
        </div>

        {/* --- 结果确认区域 (IFTTT Card) --- */}
        {generatedRule && (
          <div className="bg-white border-2 border-blue-100 rounded-xl overflow-hidden animate-fade-in-up">
            <div className="bg-blue-50 px-6 py-4 border-b border-blue-100 flex justify-between items-center flex-wrap gap-3">
              <h3 className="font-bold text-blue-800 flex items-center gap-2">
                <Sparkles className="w-4 h-4" /> AI 解析结果确认
              </h3>
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-700 font-medium">优先级:</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={generatedRule.priority}
                  onChange={(e) => setGeneratedRule({
                    ...generatedRule,
                    priority: Math.max(1, Math.min(10, parseInt(e.target.value, 10) || 1))
                  })}
                  className="w-14 border border-gray-300 rounded px-2 py-1 text-center font-medium"
                  title="数字越大优先级越高，晴天时高优先级规则会优先播放"
                />
                <span className="text-xs text-gray-500">(数字越大越优先)</span>
              </div>
            </div>

            <div className="p-6 grid gap-6">
              {/* IF 部分 */}
              <div className="flex items-start gap-4">
                <div className="bg-orange-100 text-orange-600 p-2 rounded-lg mt-1">
                  <span className="font-black text-sm">IF</span>
                </div>
                <div className="flex-1 space-y-2">
                  {generatedRule.conditions.map((cond, idx) => (
                    <div key={idx} className="flex items-center gap-3 bg-gray-50 p-3 rounded border border-gray-100">
                      {cond.type === 'weather' && <CloudRain className="w-4 h-4 text-gray-400"/>}
                      {cond.type === 'time' && <Clock className="w-4 h-4 text-gray-400"/>}
                      {cond.type === 'holiday' && <Calendar className="w-4 h-4 text-gray-400"/>}
                      
                      <span className="font-medium text-gray-700">{cond.type}</span>
                      <span className="text-gray-400 text-sm font-mono">{cond.operator}</span>
                      <span className="font-bold text-gray-900 bg-white px-2 py-0.5 rounded shadow-sm border">
                        {cond.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* ARROW */}
              <div className="flex justify-center text-gray-300">↓</div>

              {/* THEN 部分 */}
              <div className="flex items-start gap-4">
                <div className="bg-green-100 text-green-600 p-2 rounded-lg mt-1">
                  <span className="font-black text-sm">THEN</span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 bg-green-50 p-4 rounded border border-green-100">
                    <PlaySquare className="w-5 h-5 text-green-600"/>
                    <span className="text-gray-600">Switch Playlist To:</span>
                    <span className="font-bold text-green-800 text-lg">
                      {generatedRule.action.target_id}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3 border-t border-gray-100">
              <button 
                onClick={() => setGeneratedRule(null)}
                className="px-4 py-2 text-gray-500 hover:text-gray-700"
              >
                取消
              </button>
              <button 
                onClick={handleSave}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 shadow-sm"
              >
                <Save className="w-4 h-4" /> 确认并生效
              </button>
            </div>
          </div>
        )}

        {/* --- 当前生效规则列表 --- */}
        <div className="mt-12">
          <div className="flex items-center gap-2 mb-6">
            <List className="w-6 h-6 text-blue-600" />
            <h2 className="text-2xl font-bold text-gray-800">当前生效规则</h2>
            <span className="text-sm text-gray-500">（同天气下，优先级高的规则优先触发）</span>
            {isLoadingRules && (
              <span className="text-sm text-gray-500">加载中...</span>
            )}
          </div>

          {activeRules.length === 0 ? (
            <div className="bg-white p-8 rounded-xl shadow-lg text-center text-gray-500">
              <p>暂无生效规则</p>
              <p className="text-sm mt-2">创建规则后，它们将显示在这里</p>
            </div>
          ) : (
            <div className="space-y-4">
              {activeRules.map((rule) => (
                <div
                  key={rule.id || rule.name}
                  className="bg-white border border-gray-200 rounded-xl shadow-md hover:shadow-lg transition-shadow overflow-hidden"
                >
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center flex-wrap gap-3">
                    <h3 className="font-bold text-gray-800 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-blue-600" />
                      {rule.name}
                    </h3>
                    <div className="flex items-center gap-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-gray-600">优先级:</label>
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
                          className="w-12 border border-gray-300 rounded px-1.5 py-0.5 text-center text-sm font-medium"
                        />
                      </div>
                      {rule.id && (
                        <span className="text-xs text-gray-500 font-mono">
                          ID: {rule.id.substring(0, 8)}...
                        </span>
                      )}
                      <button
                        onClick={() => handleDeleteRule(rule)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="删除规则"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="p-6 grid gap-4">
                    {/* IF 部分 */}
                    <div className="flex items-start gap-4">
                      <div className="bg-orange-100 text-orange-600 p-2 rounded-lg mt-1">
                        <span className="font-black text-sm">IF</span>
                      </div>
                      <div className="flex-1 space-y-2">
                        {rule.conditions.map((cond, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-3 bg-gray-50 p-3 rounded border border-gray-100"
                          >
                            {cond.type === 'weather' && (
                              <CloudRain className="w-4 h-4 text-gray-400" />
                            )}
                            {cond.type === 'time' && (
                              <Clock className="w-4 h-4 text-gray-400" />
                            )}
                            {cond.type === 'holiday' && (
                              <Calendar className="w-4 h-4 text-gray-400" />
                            )}

                            <span className="font-medium text-gray-700">{cond.type}</span>
                            <span className="text-gray-400 text-sm font-mono">
                              {cond.operator}
                            </span>
                            <span className="font-bold text-gray-900 bg-white px-2 py-0.5 rounded shadow-sm border">
                              {cond.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* ARROW */}
                    <div className="flex justify-center text-gray-300">↓</div>

                    {/* THEN 部分 */}
                    <div className="flex items-start gap-4">
                      <div className="bg-green-100 text-green-600 p-2 rounded-lg mt-1">
                        <span className="font-black text-sm">THEN</span>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-3 bg-green-50 p-4 rounded border border-green-100">
                          <PlaySquare className="w-5 h-5 text-green-600" />
                          <span className="text-gray-600">Switch Playlist To:</span>
                          <span className="font-bold text-green-800 text-lg">
                            {rule.action.target_id}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
