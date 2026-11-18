# Kelee mini 补充筛选（2026-11-18）

在保留 AI 补充及现有 8 个 AI 源的基础上，仅新增以下三条已审查的 DOMAIN-SUFFIX 规则，使用 `🚀 节点选择`：

| 域名 | 用途 |
| --- | --- |
| dependabot.com | GitHub 依赖更新服务 |
| ghcr.io | GitHub Container Registry，Docker/OCI 镜像 |
| repo.new | GitHub 新建仓库入口 |

来源：[Kelee GitHub.lsr](https://rule.kelee.one/Loon/GitHub.lsr)，上游标注 2026-10-29 03:15:57、31 条。
本次下载快照 SHA256：`0da4ee0773602538d3647c9a81e3b390909a7fcb314604428cce6e54b99a5e4c`。
这些是按功能挑选的域名事实，不是将 Kelee 整包规则或配置模板直接导入。
[GitHub 官方文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)说明了 ghcr.io 的容器仓库用途。

三条规则在 INI 中以普通 `[]DOMAIN-SUFFIX` 内联，不依赖额外本机文件、Kelee User-Agent 或尚未发布的远程 URL。
位置在 AI、Apple 和现有 Telegram 之后、ProxyMedia/ProxyGFWlist 之前；前置 LAN、自定义直连、v6、Steam、广告优先级均不改变。
域名后缀不匹配 `notghcr.io`、`ghcr.io.example.com` 等无关域名；没有添加 `github`/`nicegram` 关键字。
若这些域名被更早的用户自定义直连命中，仍以该直连为准。

## 对照后未加入的候选

| 候选 | 结论 |
| --- | --- |
| Telegram | 下载的 Kelee 40 条均已被现有 blackmatrix7 Telegram 源覆盖，包括域名、IP、IPv6、ASN 和 nicegram；没有增益。ASN 本身也不适合默认 subconverter Clash 导出。 |
| Direct / Steam CDN | 12 个 cmp1/2/3 的 hkg1/tyo3/sgp1/lax1 地址已经被本地 `steamserver.net` 后缀覆盖；另有 GEOIP+域名 AND，不能拆开。 |
| Proxy | 只有 4 条，含 IBM、Plex 与 Steam 更新 AND；没有本机使用需求证据，不整体强制代理，也不展开 AND。 |
| GitHub 其余项 | 多数被 ProxyGFWlist 的 GitHub 域名/关键字覆盖；未引入上游宽泛 `github` 关键字。npm 注册表、社区及其他附属站点保持现有策略，避免改变包下载出口。 |
| Apple | 保留专用 Apple 组及原源；没有足够明确的缺口，不用更大的 Kelee 整包改变 Apple/CDN 策略。 |
| SpeedtestInternational | 约 18,500 条，显著增加 mini 体量，且出现 `DOMAIN,http` 异常条目；未采用。测速出口也应由用户明确选择。 |
| Game / TikTok / Netflix 等 | 现有 Steam、ProxyMedia/ProxyGFWlist 已有覆盖；没有新增独立地区/媒体组的需求，不复制 Kelee 全模板。 |

比较是本次公开源快照的规则语义比较，不是实际服务连通性测试。已有源未来更新可能减少差异；没有承诺所有候选逐项或所有动态 IP 都覆盖。
[官方 Kelee Clash 模板](https://raw.githubusercontent.com/luestr/ProxyResource/main/Tool/Clash/Config/Clash_Sample_Config_By_iKeLee.yaml)仅用于查找候选，不采用其中的端口、DNS、TUN、控制器或服务设置。

## 更新与验证

三条开发域名是刻意固定的审查子集；未来手工对照上游、检查语义和优先级再更新，不自动扩大到整包。
AI 仍用 `scripts/sync_kelee_ai.py --update-ini` 更新快照，3 条 AND 限制见 [KELEE_AI.md](KELEE_AI.md)。
不增加后台任务、第三方执行脚本或 CI。发布仓库更新后，使用 mini 的订阅需要刷新；没有自动加载客户端。

单元测试：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`。
可重复的端到端检查脚本为 `tests/verify_mini_conversion.py`：使用官方 subconverter 的 `-g` 生成模式、合成节点、公开本地自定义规则和远程规则夹具，
然后调用已安装 Mihomo 的 `-t`。数据、生成配置和日志均放在独立临时目录；不启动代理，不连接合成节点，不读取真实订阅或节点凭据。

```sh
python3 tests/verify_mini_conversion.py \
  --converter /path/to/official/subconverter \
  --mihomo '/Applications/Clash Party.app/Contents/Resources/sidecar/mihomo' \
  --country-mmdb '/Applications/Clash Party.app/Contents/Resources/files/country.mmdb'
```

实际验证版本为官方 subconverter v0.9.0 macOS ARM 和本机已安装 Mihomo。
验证全部 240 条 AI 补充、3 条开发补充、8 个 AI 源位置、策略组、IPv6/no-resolve、前置 aliyun 直连与 FINAL。
用户实际远程 converter 版本及真实服务连通性尚未验证，远程仍须支持 data URI；其他原有公开规则内容在端到端测试中用夹具替代。
