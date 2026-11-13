# 数据结构基础填空：Tauri 2 + SQLite 版

本项目基于原来的 210 题 HTML 改造，保留九章、自动判题、错题集、收藏、上次题目位置等功能。

## 本项目实际实现了什么？

- 用 Tauri 2 包装原来的网页；Android / Windows 共用界面。
- 不再调用浏览器 localStorage：答题状态写入 Tauri SQL 插件管理的 SQLite `study.db`。
- 数据库 `app_state` 表的 `json_state` 字段保存一份完整的学习状态 JSON；这是简单可靠的“SQLite 状态快照”方案，适用于 210 题。如果以后有几万题或多个用户，再拆分为标准化数据表。
- 所有写入按顺序排队，避免快速输入后乱序覆盖。页面隐藏时再触发一次保存。
- 数据库路径由 Tauri SQL 插件在应用沙箱中管理（通常是应用配置目录），无需开放手机存储读写权限。

**注意**：这不是云同步版；手机和电脑的本地 SQLite 文件互不共享。当前旧版下载 HTML 的 localStorage 也**不能自动迁移**到安装后的 Android APP：两者属于不同存储空间。请先保留旧 HTML，不要卸载或清空旧记录。

## 1. Windows 11 首次准备

安装：
1. Node.js LTS（https://nodejs.org/）
2. Rust / rustup（https://rustup.rs/）
3. Android Studio（https://developer.android.com/studio）
4. Windows 开发 C++ 工具链：Visual Studio Build Tools 的 Desktop development with C++（如果要在 Windows 上构建/运行 Tauri 桌面版）

Android Studio > Settings > Android SDK：
- 安装 Android SDK Platform、Platform-Tools、Build-Tools、Command-line Tools (latest)；
- SDK Tools 中勾选 **NDK (Side by side)**，记下 NDK 具体版本。

打开 **PowerShell**（以下路径根据实际安装情况调整）：

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$ndkVersion = (Get-ChildItem "$env:ANDROID_HOME\ndk" -Directory | Sort-Object Name -Descending | Select-Object -First 1).Name
$env:NDK_HOME = "$env:ANDROID_HOME\ndk\$ndkVersion"

rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android i686-linux-android
```

环境变量用 `$env:` 设置只影响当前 PowerShell 窗口。下次重开终端需要重新设置，或在 Windows 系统环境变量中永久保存。NDK_HOME 必须指向存在的 NDK 目录。

## 2. 安装依赖、预览

在项目根目录 PowerShell 输入：

```powershell
npm install
npm run tauri icon ./app-icon.png
npm run tauri dev
```

`tauri icon` 生成 Tauri 所需的不同分辨率图标（初次执行一次）。

## 3. 编译 Android APK

```powershell
npm run tauri android init
npm run tauri android dev
```

`android dev` 用于已经连接手机或运行了安卓模拟器的场景。手机可开启开发者选项、USB 调试；仅想编译可以跳过 dev。

```powershell
npm run tauri android build -- --apk
```

生成路径通常位于 `src-tauri/gen/android/app/build/outputs/apk/` 下，具体以构建输出为准。

**重要：发布版 APK 通常需要你自己的签名密钥。** 未签名 `.apk` 不能直接在手机上安装。首次运行建议先用 `android dev` 在真机上验证；再按官方安卓签名文档配置：
https://v2.tauri.app/distribute/sign/android/

签名密钥（`.jks`）和密码必须保管好；后续安装更新要求一致的应用标识和签名。

## 4. 编译 Windows 桌面版

```powershell
npm run tauri build
```

Windows 版保留相同前端和 SQLite 存储逻辑，但数据是另一份本地 `study.db`。

## 5. 核心代码在哪？

- `index.html`：原版页面样式、布局。
- `src/main.js`：210 题、判题逻辑、SQLite 初始化、自动保存。
- `src-tauri/src/lib.rs`：注册 SQL 插件。
- `src-tauri/capabilities/default.json`：开启 SQL 读取和写入权限。
- `src-tauri/tauri.conf.json`：App 名称、标识符、打包配置。

## 6. 常见错误

- 直接双击 `index.html`：**不行**，因为 SQLite 插件需要 Tauri 原生运行时。请使用 `npm run tauri dev`。
- 提示 `cargo` / `rustup` 找不到：重开 PowerShell，确认 Rust 已安装。
- Android 构建失败：检查 SDK、NDK、JAVA_HOME、ANDROID_HOME、NDK_HOME 和 Rust 安卓目标。
- SQL 写入失败：检查 `capabilities/default.json` 的 `sql:allow-execute`，并查看应用日志。
- 手机与电脑记录不同：正常，目前未引入云端同步。

本项目是已编写的待编译工程，未在此环境中完成 Rust/Android 真机编译；请先在 Windows 11 按步骤安装依赖并构建。
