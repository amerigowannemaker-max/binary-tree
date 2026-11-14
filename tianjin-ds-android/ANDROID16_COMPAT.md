# Android 16 安装兼容验证分支

本分支保留原 210 题和 index.html，应用版本升为 0.1.1。Android 生成工程固定 compileSdk/targetSdk 36，release 关闭 debuggable、JNI debugging、testOnly 和代码缩减，保留 16KB 内存页支持。最终安装包使用独立的长期发布证书和 v1/v2/v3 签名。

标准 Android 16 模拟器使用普通 adb install 安装非调试 release，验证页面、SQLite 草稿保存、强制关闭后恢复、自动判错、错题集和手动纠正。此结果不代表已在 ColorOS 实体机验证；本版本用于排查旧调试包的安装兼容性，不能单独确定 ColorOS 报错原因。

签名私钥只在签名任务的临时私有目录中生成。导出前通过 AES-256-GCM 加密，随机密钥再以开发者持有的 RSA 公钥封装。公开工作流与产物中不包含明文 keystore、密码或解密私钥。开发者持有的私密备份用于恢复长期发布签名，未来更新须复用同一证书。当前工作流拒绝覆盖已存在的同名发布，以避免意外更换签名。

`ci/signing-backup-public.pem` 仅是备份加密公钥。请勿提交对应的私钥、release.jks 或签名密码。
