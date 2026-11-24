import type { NextConfig } from "next";

/**
 * 桌面封装走静态导出：`next build` 产出 out/，由 Python（pywebview 壳）同源托管，
 * 前端不再依赖 Node 服务端，所有数据在浏览器里通过 /api 取。
 *
 * - output: "export"  —— 生成纯静态站点
 * - trailingSlash: true —— 目录形式 URL（/overview/ → out/overview/index.html），
 *   静态文件服务器与 pywebview 内的相对路径都能正确解析
 * - images.unoptimized —— 静态导出没有图片优化服务
 *
 * 受限环境（DSH 沙箱 / 部分 CI）禁止 child_process.fork，而 next build 的 worker 需要 fork，
 * 会报 spawn EPERM。此时用 scripts/build-sandbox.ps1（设 RATGP_BUILD_SANDBOX=1）：
 * 构建 worker 改用 worker_threads，并注入只在该沙箱里需要的序列化补丁。
 * 正常环境不需要它，行为与 Next 默认一致。
 */
const sandboxBuild = process.env.RATGP_BUILD_SANDBOX === "1";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  ...(sandboxBuild
    ? {
        experimental: {
          // 不用 fork 出来的子进程做 webpack 编译
          webpackBuildWorker: false,
          // 预渲染 worker 用线程，不依赖管道
          workerThreads: true,
        },
      }
    : {}),
};

export default nextConfig;
