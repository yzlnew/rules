# ACL_mini 的 Kelee AI 补充规则

`ACL_mini.ini` 新增一个自包含的 `data:text/plain;base64,...` ruleset，包含 **240 条兼容规则**。
原有 8 个 MetaCubeX AI 源、`💬 人工智能` 策略组、其他规则和模板均保留。
新增规则无需远程转换器读取本机文件，无需新增未发布的 GitHub 文件、provider 或替换 converter base。
发布本仓库的更新不会自动加载客户端配置或更改系统设置；使用此 INI 的远程订阅须刷新后才能生效。

## 覆盖和明确排除的规则

来源：https://kelee.one/Tool/Loon/Lsr/AI.lsr 。源文件标注更新时间为 2026-10-07 22:40:50。
245 条输入：194 DOMAIN、46 DOMAIN-SUFFIX、3 AND、1 IPv4、1 IPv6。
`api.githubcopilot.com` 出现三次，去重后完整规则共 243 条。

默认 INI 补充的是 192 条唯一 DOMAIN、46 条 DOMAIN-SUFFIX、1 条 IPv4 CIDR、1 条 IPv6 CIDR，共 240 条。
DOMAIN 保持精确匹配，DOMAIN-SUFFIX 保持原后缀；IP-CIDR/IP-CIDR6 和 no-resolve 原样保留。
来源涵盖 Antigravity、NotebookLM、JetBrains AI、Mistral、Trae、Groq、OpenRouter 以及源中列出的其他 AI 服务/API；
不代表每个服务的全部依赖域名或可用性保证。

**以下 3 条 AND 不受默认 subconverter Clash 规则导出支持，没有接入默认 INI：**

```text
AND,((DOMAIN-KEYWORD,chatgpt-async-webps-prod-),(DOMAIN-SUFFIX,webpubsub.azure.com))
AND,((DOMAIN-KEYWORD,openaicom-api-),(DOMAIN-SUFFIX,azurefd.net))
AND,((DOMAIN-KEYWORD,antigravity-auto-updater-),(DOMAIN-SUFFIX,run.app))
```

因此这是 Kelee 的部分补充，不能称为完整覆盖。这些连接仍按原有 8 个 AI 源和后续规则处理，可能走其他出口。
没有将 AND 拆成 OR、添加无约束关键字，或将 Azure/Cloud Run 的共享后缀整体归入 AI。
上游 subconverter ClashRuleTypes 不包含 AND，通用拼接还会按逗号拆分；不能靠 inline AND 绕过。

## 为什么内嵌 data URI

Kelee 源用普通 curl、subconverter User-Agent 下载均返回 403，专用 Loon User-Agent 才可下载。
本地生成后只放在仓库的新 ruleset 文件，在不发布时远程 converter 也无法读取。
逐条使用 240 个 `[]DOMAIN` inline 项又会超过上游默认 64 个 ruleset 的限制，实际生成测试已确认会拒绝外部配置。
因此将兼容的 Surge 风格文本作为**一个** base64 data URI 内嵌到 INI。

subconverter 原生 `webGet` 支持 data URI，官方 v0.9.0 ARM macOS 二进制实测可解码并输出全部 240 条规则。
`ruleset` 行末的 `,86400` 必须保留，确保 INI ruleset 参数解析保留 data URI 内的逗号。
该行是规则快照，不会自动获取 Kelee 更新；需运行同步脚本后重新发布 INI。
不要手改 base64 内容，也不要换成原始 Loon URL、domain-only YAML 或只存在本机的路径。

## 优先级

补充源位于原有广告规则之后、原有 AI 源之前。前置 LAN、自定义直连、v6、Steam 等规则继续优先。
特别是 `ruleset/direct.list` 中的 `DOMAIN-KEYWORD,aliyun` 仍让以下源内 API 直连：
`dashscope-intl.aliyuncs.com`、`coding-intl.dashscope.aliyuncs.com`、`token-plan.ap-southeast-1.maas.aliyuncs.com`。
这是保留的用户显式覆盖。AI 规则之后仍是 Apple、通用代理、中国域名/IP、GEOIP 和 FINAL。
`💬 人工智能` 组的实际选择决定最终出口。

## 同步和静态验证

同步脚本仅使用 Python 3 标准库，不执行上游代码。下载有 30 秒超时、2 MB 上限和专用 Loon User-Agent，
也支持离线源。未知类型、格式变化、错误页、空规则报错，不静默跳过；仅将验证通过的 AND 显式排除于兼容快照。
完整 native payload 保留 AND，文件头记录源 URL 与 SHA256。成功验证后原子替换各输出文件。

```sh
# 同步完整原生 payload，并更新默认 INI 中的兼容快照
python3 scripts/sync_kelee_ai.py --update-ini
# 或使用已下载源
python3 scripts/sync_kelee_ai.py --source /tmp/kelee-ai.lsr --update-ini
python3 scripts/sync_kelee_ai.py --source /tmp/kelee-ai.lsr --update-ini --check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

不加 `--update-ini` 时只生成完整原生 payload，不改默认 INI。
没有后台同步或 CI。更新后审查差异，再由用户自行发布并刷新现有远程转换订阅。

## 实际生成验证与边界

用官方 subconverter v0.9.0 macOS ARM 发行版的 `-g` 离线生成模式验证：
使用修改后 INI 的全部新增 data URI 和原有策略组；原有远程规则内容替换为合成夹具，以避免真实订阅和外部依赖，
自定义 direct.list 保留用于优先级检查；合成节点为 192.0.2.1，不进行连接。
检查生成 YAML 的新增规则与 240 条预期规则逐条一致、策略组目标正确、IP/no-resolve 保留、没有 AND 或悬空 provider。
再使用本机已安装的 Mihomo `-t`、独立 /tmp 数据目录和应用自带的公开 country.mmdb 进行配置检查，通过。
只进行配置检查，没有启动代理或加载进实际客户端。

尚未调用用户实际远程 converter，也未测试真实服务连通性；实际远程部署须支持 data URI，其他版本/分支不能以此测试保证。
原有远程规则的可用性和内容未在这次合成验证中复测。
初次探测 converter 时 `-h` 未被识别而进入服务模式，该临时进程已停止；后续全部使用 `-g`，不保留服务。

## 未启用：完整原生 Mihomo 方案

`ACL_mini.kelee-mihomo.ini.example`、`ruleset/kelee-ai.yaml` 和 `ruleset/kelee-ai-provider.yaml`
保留为实验参考，不由默认 INI 引用。完整 payload 为 243 条，含三条 AND。
此方案须将 payload 复制到 Mihomo HomeDir 的 ruleset/，并将 provider 片段合并进最终 `rule-providers`，保留其他 provider。
仅使用该示例 INI 会因缺少 provider 而不可用，不能直接替换默认订阅模板；尚未对该完整方案执行 converter/客户端联合验证。

参考：
- [subconverter ruleconvert.cpp](https://github.com/tindy2013/subconverter/blob/master/src/generator/config/ruleconvert.cpp)、[webget.cpp](https://github.com/tindy2013/subconverter/blob/master/src/handler/webget.cpp)。
- [官方 v0.9.0 发行版](https://github.com/tindy2013/subconverter/releases/tag/v0.9.0)。
- [Mihomo 规则集合](https://wiki.metacubex.one/config/rule-providers/)、[classical 内容](https://wiki.metacubex.one/config/rule-providers/content/)、[路由优先级](https://wiki.metacubex.one/config/rules/)。
