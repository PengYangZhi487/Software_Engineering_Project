import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RATGP · 需求工程工作台",
  description: "需求解析 · 测试用例 · 追踪矩阵 · 变更影响",
};

/**
 * 首屏之前把已保存的主题打到 <html data-theme>，避免出现"先白后紫"的闪烁。
 * 默认浅色；优先级：URL ?theme= > localStorage > 浅色。
 */
const themeScript = `(function(){try{
  var p=new URLSearchParams(location.search).get('theme');
  var t=p||localStorage.getItem('ratgp-theme');
  if(t==='light'||t==='glass'||t==='dark'){document.documentElement.dataset.theme=t;}
}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
