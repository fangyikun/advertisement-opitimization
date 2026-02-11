import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Home } from 'lucide-react';

const STORE_ID = 'store_001'; // 门店ID

// 图片映射
const IMAGE_MAP: Record<string, string> = {
  hot_drink_ad: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1920&h=1080&fit=crop',
  coffee_ads_playlist: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1920&h=1080&fit=crop', // 咖啡广告
  coffee_ads_playlist_id: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1920&h=1080&fit=crop', // 咖啡广告（LLM生成的ID）
  coffee_ads: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1920&h=1080&fit=crop', // 咖啡广告（简化版）
  coffee_ad: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1920&h=1080&fit=crop', // 咖啡广告（单数形式）
  default: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1920&h=1080&fit=crop'
};

interface CurrentContent {
  content: string;
}

function Player() {
  const [currentContent, setCurrentContent] = useState<string>('default');
  const [imageUrl, setImageUrl] = useState<string>(IMAGE_MAP.default);
  const [fadeIn, setFadeIn] = useState<boolean>(true);
  const prevContentRef = useRef<string>('default');

  // 获取当前播放内容
  const fetchCurrentContent = async () => {
    try {
      const res = await axios.get<CurrentContent>(
        `http://127.0.0.1:8000/api/v1/stores/${STORE_ID}/current-content`
      );
      console.log("获取当前内容:", res.data);
      
      const newContent = res.data.content;
      console.log(`📺 当前内容: "${newContent}", 映射的图片: ${IMAGE_MAP[newContent] ? '✅ 存在' : '❌ 不存在，将使用默认图片'}`);
      
      // 如果内容发生变化，触发淡入淡出动画
      if (newContent !== prevContentRef.current) {
        // 淡出当前图片
        setFadeIn(false);
        
        // 等待淡出动画完成后再切换图片（500ms 淡出时间）
        setTimeout(() => {
          const newImageUrl = IMAGE_MAP[newContent] || IMAGE_MAP.default;
          setImageUrl(newImageUrl);
          setCurrentContent(newContent);
          prevContentRef.current = newContent;
          
          // 短暂延迟后开始淡入新图片
          setTimeout(() => {
            setFadeIn(true);
          }, 100);
        }, 500);
      }
    } catch (error) {
      console.error("获取当前内容失败:", error);
      // 失败时保持当前状态
    }
  };

  // 组件加载时立即获取一次
  useEffect(() => {
    fetchCurrentContent();
    
    // 设置定时器，每5秒获取一次
    const contentInterval = setInterval(() => {
      fetchCurrentContent();
    }, 5000); // 5秒

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
        alt={currentContent === 'hot_drink_ad' || currentContent === 'coffee_ads_playlist' || currentContent === 'coffee_ads_playlist_id' || currentContent === 'coffee_ads' || currentContent === 'coffee_ad' ? '咖啡广告' : '默认风景'}
        className={`w-full h-full object-contain transition-opacity duration-500 ${
          fadeIn ? 'opacity-100' : 'opacity-0'
        }`}
        onError={(e) => {
          // 如果图片加载失败，使用默认图片
          const target = e.target as HTMLImageElement;
          target.src = IMAGE_MAP.default;
        }}
      />
    </div>
  );
}

export default Player;
