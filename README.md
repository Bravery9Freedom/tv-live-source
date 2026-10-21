# 央卫视直播源（纯 IPv4 · 多线路）

中央电视台 + 省级卫视频道直播源，每个频道配 **2~3 条线路**，播放器可手动/自动切换。

- 频道数：**54**（CCTV 1~17 + 5+ / 4K / 8K，共 20 路；省级卫视 34 路）
- 线路总数：**145**
- **全部 IPv4**，文件内 IPv6 地址数为 0（生成脚本强制自检）

线路数分布：4 条的 2 路、3 条的 34 路、2 条的 17 路、**1 条的 1 路**。
唯一单线路的频道是 **海南卫视**——tvbus 中转与运营商 CDN 均无该台的可用地址
（实测 tvbus 各候选码均返回「频道没有配置任何服务器」），它只有央广官方一条源。
央广这条已实测 200 + 有效 m3u8，能正常播放，只是没有第二条可切。

---

## 一、订阅地址（免维护自动更新）

仓库地址确定后，把下面地址里的 `OWNER/REPO` 换成实际的即可：

| 用途 | 地址 |
|---|---|
| **M3U 通用**（TiviMate / Televizo / OTT / Kodi / fred-tv / VLC / PotPlayer） | `https://raw.githubusercontent.com/OWNER/REPO/main/tv.m3u` |
| **TXT 盒端**（TVBox / DIYP / DIYBOX / YYKM / Box） | `https://raw.githubusercontent.com/OWNER/REPO/main/tv.txt` |
| jsDelivr 加速（国内访问更快的备选） | `https://cdn.jsdelivr.net/gh/OWNER/REPO@main/tv.m3u` |

> jsDelivr 有缓存（通常 12~24 小时），想要立刻拿到最新，用 raw 地址。

**节目单 EPG**：`http://epg.51zmt.top:8000/e.xml`
（已内嵌在 tv.m3u 的 `x-tvg-url` 里，支持该属性的播放器会自动加载）

---

## 二、各播放器怎么导入

### TiviMate / Televizo / OTT Navigator
设置 → 播放列表 → 添加播放列表 → 选「URL 或文件路径」→ 填上面的 M3U 地址 → 完成。
EPG：设置 → EPG → 添加 → 填 EPG 地址。

### Kodi
装插件 **IPTV Simple Client**（PVR 客户端）→ 配置 → 位置选「远程路径」→ 填 M3U 地址 → 频道启用。
EPG：同一配置页「EPG」→ XMLTV 路径填 EPG 地址。

### fred-tv（open-tv）
支持 M3U 文件与 M3U 网址 → 设置里添加播放列表 → 填 M3U 地址。

### VLC（Android）
打开 VLC → 「流」或本地网络导入，或用「打开网络串流」直接贴 M3U 地址。
⚠️ VLC 只播放，**不显示节目单**。

### TVBox 系（Box / DIYBOX / YYKM）
设置 → 直播源 / 订阅 → 填 TXT 地址。

### 多线路怎么切换
- **TiviMate**：播放时长按 OK/确认键 → 「选择线路/源」，或 播放列表设置里选。
- **TVBox/DIYP 系**：播放中按「确定」或方向键上 → 弹出线路列表。
- 播放器一般会在当前线路失败时**自动跳下一条**。

---

## 三、线路口径

| 分组 | ①主线路 | ②备用 | ③兜底 |
|---|---|---|---|
| **CCTV** | 央视官方 `cctvcnch5ca.v.wscdns.com` | 央视官方腾讯云 `cctvtxyh5ca.liveplay.myqcloud.com` | tvbus 中转 |
| **卫视** | 央广官方 `satellitepull.cnr.cn` | 运营商 IPTV CDN | tvbus 中转 |

- 卫视主线路为**央广官方拉流**，生成时 34 路全部实测返回 200 + 有效 m3u8。
- CCTV 官方 CDN 域名来自多个公开列表交叉佐证，属官方 CDN；本机网络无法直连该 CDN，故**需在盒子上实际点开确认**。
- tvbus 为境外中转，落地全部为 IPv4，但跨境会受带宽影响，仅作兜底。

---

## 四、自动更新

仓库内 `.github/workflows/update.yml` **每天自动重跑两次**（北京时间 12:00 与 24:00），
重新生成并推送最新源：

- 改了 `gen_multi.py` 会立即触发重建
- 也可以在 GitHub 仓库 → Actions → 选「每日更新直播源」→ Run workflow 手动立即执行
- 生成前会做 IPv6 自检，发现 IPv6 直接拒绝提交

---

## 五、本地自己生成

```bash
python gen_multi.py                  # 输出到 ./（中文文件名）
python gen_multi.py --out D:\iptv    # 指定目录
python gen_multi.py --verify         # 生成前并发实测，把通的线路排前面
```

`--verify` 会逐个 curl 实测（HTTP 200 且内容为合法 m3u8 才算通过），
并把可用线路排到前面。注意：国内 CDN 在境外网络下测不通是正常现象，
所以默认不使用 --verify 排序，避免把国内更快的线路排到后面。

---

*免维护的关键：把本仓库的 raw 地址填进播放器的「订阅/远程播放列表」，之后源文件的更新由 Actions 自动推送，播放器定期自取，你不用再手动拷贝文件。*
