// 受限构建环境（DSH 沙箱 / 无 fork 权限的 CI）的 preload 补丁。
//
// next build 在静态导出阶段把 renderOpts / nextConfig 发给 worker；Next 的默认配置里
// generateBuildId（()=>null）和 exportPathMap 是函数，worker_threads 的 structuredClone
// 不接受函数，于是报 "DataCloneError: ()=>null could not be cloned"。
// 这里在 postMessage 前把这些函数字段换成 undefined —— 导出阶段用不到它们
// （buildId 与 exportPaths 已经作为参数传入）。
//
// 只被 scripts/build-sandbox.ps1 通过 NODE_OPTIONS=--require 加载；正常 next build 不需要。
const wt = require("worker_threads");

function stripFns(value, seen) {
  if (typeof value === "function") return undefined;
  if (value === null || typeof value !== "object") return value;
  if (seen.has(value)) return value;
  seen.add(value);
  if (
    value instanceof Map ||
    value instanceof Set ||
    value instanceof RegExp ||
    value instanceof Date
  ) {
    return value;
  }
  for (const key of Object.keys(value)) {
    const next = value[key];
    if (typeof next === "function") {
      try {
        value[key] = undefined;
      } catch {
        /* 只读属性忽略 */
      }
    } else if (next && typeof next === "object") {
      stripFns(next, seen);
    }
  }
  return value;
}

const orig = wt.Worker.prototype.postMessage;
wt.Worker.prototype.postMessage = function patched(value, ...rest) {
  try {
    structuredClone(value);
    return orig.call(this, value, ...rest);
  } catch {
    return orig.call(this, stripFns(value, new Set()), ...rest);
  }
};
