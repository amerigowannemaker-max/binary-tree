# 2027 天津专升本数据结构：Tauri 2 + SQLite

保留上传工程的 210 道题、九章内容与原有页面样式。题库和 index.html 的 SHA-256 校验见 `verification/original-integrity.json`。

## GitHub 云端构建

工程位于 `amerigowannemaker-max/binary-tree` 仓库的 `codex/tianjin-ds-android-arm64-20261114` 独立分支，目录为 `tianjin-ds-android`；仓库根目录的 `.github/workflows/tianjin-ds-android.yml` 自动运行构建。原有 main 分支与二叉树页面保持原样。

构建流程固定 Node.js 22、JDK 17、NDK 27.2.12479018、Tauri 2.12、SQL 插件 2.6.0，并使用 npm 与 Cargo 锁文件。输出 ARM64 已签名调试 APK，适合直接安装测试；原生库与 APK 内部存放偏移均检查 16KB 内存页兼容。禁用 Rust 调试符号，减小安装包体积。

Actions 同时执行内容完整性检查、全部 210 题的自动判题检查，以及 Android 模拟器上的真实 SQLite 插件测试。测试覆盖草稿保存、快速输入后的最新记录、强制关闭后恢复、错题集、收藏、清空记录和中文输入法确认键。模拟器使用 x86_64 验证相同应用代码，手机交付物为 ARM64。

在 Actions 运行页下载 `tianjin-ds-2027-android-arm64-apk`；编译日志、签名信息、依赖版本及测试结果位于 `tianjin-ds-verification-*`。

## 本地构建

安装 JDK 17、Android SDK/NDK、Rust 和 Node.js；配置 `JAVA_HOME`、`ANDROID_HOME`、`NDK_HOME`，并安装 `aarch64-linux-android` Rust 目标。在工程目录执行：

```bash
npm ci
npm run tauri -- icon ./app-icon.png
npm run tauri -- android init --ci --skip-targets-install
RUSTFLAGS="-C link-arg=-Wl,-z,max-page-size=16384" npm run tauri -- android build --apk --debug --ci --target aarch64
```

APK 位于 `src-tauri/gen/android/app/build/outputs/apk/`。首次云端构建生成的调试签名会通过 Actions 缓存保留；正式分发应使用自己的长期签名。

## 数据与修复

SQL 插件在应用沙箱中的 `study.db` 保存完整学习状态，读写权限由 `src-tauri/capabilities/default.json` 限定。每次输入按顺序写入参数化 SQL，错误答案自动加入错题集，改正后移出。此工程不做跨设备同步，也不自动导入旧 HTML 的浏览器记录。

修复首次运行时默认状态对象被修改导致清空不彻底的问题；中文输入法处于组词状态时，回车不触发判题。

`index.html` 为完整原始页面；`src/main.js` 保留原题库与练习逻辑。浏览器测试仅替换原生 IPC 传输层并使用真实 SQLite；Android 测试直接调用打包后的 Tauri SQL 插件，不替换插件。
