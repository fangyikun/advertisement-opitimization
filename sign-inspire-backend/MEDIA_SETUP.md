# 自动图片搜索配置

新增的广告图片会根据提示词**自动从互联网搜索**，无需再手动维护 IMAGE_MAP。

## 工作流程

1. 用户创建规则（如「晴天 西瓜」）→ `target_id = xigua_ad`
2. 播放器请求 `/stores/{store_id}/media/xigua_ad`
3. 后端：若缓存无则用关键词「西瓜」搜索 Unsplash → 缓存 URL → 返回
4. 前端展示对应图片

## 配置 Unsplash（可选）

未配置时使用 [Picsum](https://picsum.photos) 占位图（按 target_id 固定样式）。

若需真实产品图片，在 `.env` 添加：

```
UNSPLASH_ACCESS_KEY=你的Access_Key
```

**获取步骤：**
1. 打开 https://unsplash.com/developers
2. 注册并创建应用
3. 复制 Access Key

Demo 模式约 50 次/小时。

## 词汇与搜索

- 系统从「词汇表」反向查找：`target_id` → 关键词（如 `xigua_ad` → `西瓜`）
- 常见词会映射为英文以提升 Unsplash 效果（如 西瓜→watermelon）
- 新词会使用中文关键词或 target_id 派生词进行搜索
