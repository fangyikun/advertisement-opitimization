import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Home } from 'lucide-react';

const STORE_ID = 'store_001';
const API_BASE = 'http://127.0.0.1:8000/api/v1';

interface CurrentContent {
  content: string;
}

function Player() {
  const [currentContent, setCurrentContent] = useState<string>('default');
  const [imageUrl, setImageUrl] = useState<string>('https://picsum.photos/seed/default/1920/1080');
  const [fadeIn, setFadeIn] = useState<boolean>(true);
  const prevContentRef = useRef<string>('default');

  // 根据 target_id 获取图片 URL（自动从后端搜索互联网图片）
  const fetchImageUrl = async (targetId: string): Promise<string> => {
    try {
      const res = await axios.get<{ url: string }>(
        `${API_BASE}/stores/${STORE_ID}/media/${encodeURIComponent(targetId)}`
      );
      return res.data?.url || '';
    } catch {
      return '';
    }
  };

  const fetchCurrentContent = async () => {
    try {
      const res = await axios.get<CurrentContent>(
        `${API_BASE}/stores/${STORE_ID}/current-content`
      );
      const newContent = res.data.content || 'default';
      
      if (newContent !== prevContentRef.current) {
        setFadeIn(false);
        
        setTimeout(async () => {
          const url = await fetchImageUrl(newContent);
          setImageUrl(url || 'https://picsum.photos/seed/default/1920/1080');
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
          (e.target as HTMLImageElement).src = 'https://picsum.photos/seed/default/1920/1080';
        }}
      />
    </div>
  );
}

export default Player;
