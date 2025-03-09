import { defineConfig } from 'vite';

export default defineConfig({
  base: '/static/', // 配置资源的基础路径，Django 静态文件路径
  build: {
    manifest: true, // 确保生成 manifest.json
    outDir: 'static', // 输出到 static 目录下
    rollupOptions: {
      input: './index.html', // 指定入口文件
    },
  },
});
