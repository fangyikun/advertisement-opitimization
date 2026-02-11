import { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Home } from 'lucide-react';
import { config } from '../config';

const API_BASE = config.apiBaseUrl;

function Player() {
  const [searchParams] = useSearchParams();
  const signId = searchParams.get('sign') || config.defaultSignId;
  const storeId = searchParams.get('store') || config.defaultStoreId;

  const [currentContent, setCurrentContent] = useState<string>('default');
  const PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'%3E%3Crect fill='%231e293b' width='1920' height='1080'/%3E%3Ctext x='50%25' y='50%25' fill='%2394a3b8' font-size='24' text-anchor='middle' dy='.3em' font-family='sans-serif'%3E灵犀 · 智能推送%3C/text%3E%3C/svg%3E";
  const [imageUrl, setImageUrl] = useState<string>(PLACEHOLDER);
  const [fadeIn, setFadeIn] = useState<boolean>(true);
  const prevContentRef = useRef<string>('default');

  const fetchImageUrl = async (targetId: string): Promise<string> => {
    try {
      const res = await axios.get<{ url: string }>(
        `${API_BASE}/stores/${storeId}/media/${encodeURIComponent(targetId)}`
      );
      return res.data?.url || '';
    } catch {
      return '';
    }
  };

  const fetchCurrentContent = async () => {
    try {
      const url = signId
        ? `${API_BASE}/signs/${signId}/current-content`
        : `${API_BASE}/stores/${storeId}/current-content`;
      const res = await axios.get<{ content: string }>(url);
      const newContent = res.data.content || 'default';
      
      if (newContent !== prevContentRef.current) {
        setFadeIn(false);
        
        setTimeout(async () => {
          const url = await fetchImageUrl(newContent);
          setImageUrl(url || PLACEHOLDER);
          setCurrentContent(newContent);
          prevContentRef.current = newContent;
          
          setTimeout(() => setFadeIn(true), 100);
        }, 500);
      }
    } catch (error) {
      console.error("获取当前内容失败:", error);
    }
  };

  // 组件加载时立即获取一次
  useEffect(() => {
    fetchCurrentContent();
    
    // 设置定时器，每2秒获取一次（加速内容更新）
    const contentInterval = setInterval(() => {
      fetchCurrentContent();
    }, 2000); // 2秒

    // 清理定时器
    return () => {
      clearInterval(contentInterval);
    };
  }, []); // 只在组件挂载时执行一次

  return (
    <div className="fixed inset-0 bg-black flex items-center justify-center overflow-hidden">
      {/* 返回管理页面的按钮 */}
      <Link
        to="/"
        className="absolute top-4 left-4 z-10 flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-lg backdrop-blur-sm transition-colors"
      >
        <Home className="w-5 h-5" />
        返回管理
      </Link>
      
      <img
        src={imageUrl}
        alt={currentContent}
        className={`w-full h-full object-contain transition-opacity duration-500 ${
          fadeIn ? 'opacity-100' : 'opacity-0'
        }`}
        onError={(e) => {
          (e.target as HTMLImageElement).src = PLACEHOLDER;
        }}
      />
    </div>
  );
}

export default Player;
