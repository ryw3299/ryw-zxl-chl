<template>
  <div class="app-root">
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
/* ── Design Tokens ─────────────────────────────────────────── */
:root {
  --brand-hue: 221;
  --brand-primary: #2563eb;
  --brand-primary-hover: #1d4ed8;
  --brand-primary-light: #dbeafe;
  --brand-primary-bg: #eff6ff;
  --brand-accent: #f59e0b;
  --brand-accent-green: #10b981;
  --brand-accent-red: #ef4444;
  --brand-accent-purple: #8b5cf6;

  --bg: #ffffff;
  --bg-page: #f1f5f9;
  --bg-card: #ffffff;
  --bg-sidebar: #ffffff;
  --bg-header: #ffffff;
  --bg-hover: #f8fafc;
  --bg-selected: #eff6ff;

  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --text-inverse: #ffffff;
  --text-brand: #2563eb;

  --border: #e2e8f0;
  --border-light: #f1f5f9;

  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.08);

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;

  --sidebar-width: 220px;
  --header-height: 60px;

  --font-sans: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif;
  --font-mono: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

/* ── Global Reset ──────────────────────────────────────────── */
*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-sans);
  color: var(--text-primary);
  background: var(--bg-page);
  line-height: 1.6;
}

a {
  color: var(--text-brand);
  text-decoration: none;
}
a:hover {
  color: var(--brand-primary-hover);
}

/* ── Common Layout ─────────────────────────────────────────── */
.page-layout {
  display: flex;
  min-height: 100vh;
}

.page-main {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
}

.page-body {
  padding: 24px;
  flex: 1;
}

/* ── Card ──────────────────────────────────────────────────── */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-light);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.card-body {
  padding: 20px;
}

/* ── Tag / Badge overrides ─────────────────────────────────── */
.el-tag--primary { --el-tag-bg-color: var(--brand-primary-light); --el-tag-border-color: transparent; --el-tag-text-color: var(--brand-primary); }
.el-tag--success { --el-tag-bg-color: #ecfdf5; --el-tag-border-color: transparent; --el-tag-text-color: #059669; }
.el-tag--warning { --el-tag-bg-color: #fffbeb; --el-tag-border-color: transparent; --el-tag-text-color: #d97706; }
.el-tag--danger  { --el-tag-bg-color: #fef2f2; --el-tag-border-color: transparent; --el-tag-text-color: #dc2626; }
.el-tag--info    { --el-tag-bg-color: #f1f5f9; --el-tag-border-color: transparent; --el-tag-text-color: #64748b; }

/* ── Button overrides ──────────────────────────────────────── */
.el-button--primary {
  --el-button-bg-color: var(--brand-primary);
  --el-button-border-color: var(--brand-primary);
  --el-button-hover-bg-color: var(--brand-primary-hover);
  --el-button-hover-border-color: var(--brand-primary-hover);
}

/* ── Menu overrides (sidebar) ──────────────────────────────── */
.sidebar-menu .el-menu-item {
  height: 44px;
  line-height: 44px;
  margin: 2px 12px;
  border-radius: var(--radius-sm);
  padding: 0 12px !important;
}
.sidebar-menu .el-menu-item.is-active {
  background: var(--bg-selected) !important;
  color: var(--brand-primary) !important;
}
.sidebar-menu .el-menu-item:hover {
  background: var(--bg-hover) !important;
}

/* ── Scrollbar ─────────────────────────────────────────────── */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* ── Utility ───────────────────────────────────────────────── */
.text-brand { color: var(--brand-primary); }
.text-muted { color: var(--text-muted); }
.fw-600 { font-weight: 600; }
</style>
