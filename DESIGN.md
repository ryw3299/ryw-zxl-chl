---
name: 知微智课
description: AI驱动的智能课程平台 - 温暖、亲和、活力的教育工具
colors:
  primary: "#3370ff"
  primary-strong: "#245bdb"
  neutral-bg: "#f5f6f8"
  surface: "#ffffff"
  surface-soft: "#f7f8fa"
  border: "#dfe1e6"
  border-soft: "#ebedf0"
  text: "#1d2129"
  muted: "#6b7785"
  subtle: "#a0a8b4"
  success: "#34c759"
  warning: "#ff9500"
  danger: "#ff3b30"
  sidebar-bg: "#1c2128"
  sidebar-text: "#cdd5e0"
typography:
  display:
    fontFamily: "PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  body:
    fontFamily: "PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "0"
  caption:
    fontFamily: "PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "0"
rounded:
  sm: "3px"
  md: "6px"
  lg: "10px"
  xl: "18px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.primary-strong}"
  button-secondary:
    backgroundColor: "#ffffff"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "0 12px"
    height: "36px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "16px"
  sidebar:
    backgroundColor: "{colors.sidebar-bg}"
    textColor: "{colors.sidebar-text}"
    width: "252px"
---

## Overview

知微智课是一个面向教师和学生的AI智能课程平台。PC端使用 Vue 3 + Element Plus，移动端使用 Vant 4。设计语言应该传递温暖、亲和、活力的教育产品氛围，同时保持专业工具的效率。

## Colors

主色调为蓝色（#3370ff），用于主要操作按钮和状态指示。中性色系以冷灰为基底（#f5f6f8 背景，#1d2129 文字）。语义色遵循标准：绿色成功、橙色警告、红色危险。

当前问题：侧边栏使用深色（#1c2128）配合浅色内容区，形成强烈的明暗对比，偏企业管理后台风格。部分组件仍残留青色系（#0ea5e9）硬编码值。

## Typography

系统字体栈：PingFang SC > Hiragino Sans GB > Microsoft YaHei > sans-serif。使用三级字重系统：400（正文）、500（标签/UI文字）、600（标题/按钮）。标题使用负字间距（-0.01em）增强紧凑感。

当前问题：部分组件仍有 font-weight: 700-800 的过度加粗。行高在部分场景不统一。

## Elevation

阴影使用克制的中性灰阴影（0 1px 3px rgba(0,0,0,0.06)）。卡片和面板使用细边框（1px solid #dfe1e6）而非重阴影来定义层级。当前存在部分不必要的 backdrop-filter 效果。

## Components

### 按钮
- 主要按钮：蓝色背景，白色文字，6px圆角
- 次要按钮：白色背景，边框，6px圆角
- 图标按钮：32px方形，边框，居中图标

### 卡片
- 白色背景，1px边框，6px圆角
- 内部 padding 14-24px
- hover态：边框颜色加深，无位移

### 侧边栏
- 当前：252px宽，深色背景，文字+图标导航
- 问题：过于像企业管理后台

### 课程卡片
- 当前：等大网格卡片，封面图+信息+操作
- 问题：千篇一律的AI卡片网格模式

## Do's and Don'ts

### Do's
- 使用CSS变量管理颜色，保持主题一致性
- hover态用边框变化代替位移（translateY）
- 字体限制在3级字重内（400/500/600）
- 圆角按元素大小分层使用
- 移动端保持足够的触控面积（44px+）

### Don'ts
- 不使用装饰性渐变背景（特别是hero区域的双色渐变）
- 不使用 font-weight 700 以上
- 不使用 backdrop-filter 做装饰（仅用于sticky/fixed元素）
- 不使用 emoji 作为功能图标
- 不使用等大的卡片网格铺满页面
- 不使用侧边彩色条（border-left accent）作为卡片装饰
- 不使用过度统一的动画时间（应有变化）
- 不在中文界面使用英文标签
