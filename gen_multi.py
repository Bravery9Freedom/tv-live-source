# -*- coding: utf-8 -*-
"""
央卫视纯 IPv4 多线路直播源生成器
=================================
每个频道配 2~3 条线路，播放器(TiviMate/TVBox/DIYP/OTT/Kodi/fred-tv)可手动或自动切换。

线路口径（按优先级排序）：
  CCTV : ①央视官方 wscdns  ②tvbus 中转  ③公开聚合（CCTV-9 用 xykt-fix）
  卫视 : ①央广官方 cnr.cn  ②运营商 IPTV CDN  ③tvbus 中转

IPv6：全部为 IPv4。生成后脚本自检，含 [xx:xx::x] 形式立即报错。

用法:
    python gen_multi.py                  # 生成到桌面 TV直播源
    python gen_multi.py --out <目录>      # 指定输出目录
    python gen_multi.py --verify         # 生成前并发实测，把通的线路排到前面
"""
import os, re, sys, subprocess, tempfile, concurrent.futures as cf

# ---------------- 数据源 ----------------
CNR = "http://satellitepull.cnr.cn/live/"
WSCDN = "https://cctvcnch5ca.v.wscdns.com/live/"
MYQCLOUD = "https://cctvtxyh5ca.liveplay.myqcloud.com/live/"
TVBUS = "http://bztv.tvbus.cc:8081/cdnlive/"
EPG = "http://epg.51zmt.top:8000/e.xml"

# 卫视：主源 = 央广官方拉流（已逐个实测 200，纯 IPv4）
SAT_MAIN = {
    "北京卫视": "wxbtv",       "天津卫视": "wxtjws",      "河北卫视": "wxhebws",
    "山西卫视": "wxssxws",     "内蒙古卫视": "wx32nmgws", "辽宁卫视": "wxlnws",
    "吉林卫视": "wxjlws",      "黑龙江卫视": "wx32hljws", "东方卫视": "wx32dfws",
    "江苏卫视": "wx32jsws",    "浙江卫视": "wxzjws",      "安徽卫视": "wxahws",
    "东南卫视": "wx32fjws",    "江西卫视": "wx32jiangxws","山东卫视": "wxsdws",
    "河南卫视": "wxhnws",      "湖北卫视": "wx32hubws",   "湖南卫视": "wx32hunws",
    "广东卫视": "wxgdws",      "广西卫视": "wx32gxws",    "海南卫视": "wxhainlyws",
    "重庆卫视": "wxcqws",      "四川卫视": "wxscws",      "贵州卫视": "wx32gzws",
    "云南卫视": "wxynws",      "西藏卫视": "wxxzws",      "陕西卫视": "wxsxxws",
    "甘肃卫视": "wxgsws",      "青海卫视": "wx32qhws",    "宁夏卫视": "wxnxws",
    "新疆卫视": "wxxjws",      "深圳卫视": "wxszws",      "延边卫视": "wxybws",
    "兵团卫视": "wxbtws",
}

# 卫视备源 ②：运营商 IPTV CDN（来源 iptv-org 维护清单；对口运营商网络更快）
SAT_IPTV = {
    "北京卫视": ["http://go.bkpcp.top/mg/bjws", "http://ivi.bupt.edu.cn/hls/btv1.m3u8"],
    "天津卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225698/index.m3u8"],
    "内蒙古卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225667/index.m3u8"],
    "辽宁卫视": ["http://39.134.39.37/PLTV/88888888/224/3221226209/index.m3u8"],
    "江苏卫视": ["http://39.134.24.166/dbiptv.sn.chinamobile.com/PLTV/88888890/224/3221226200/index.m3u8"],
    "浙江卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225703/index.m3u8"],
    "江西卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225705/index.m3u8"],
    "山东卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225697/index.m3u8"],
    "四川卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225733/index.m3u8"],
    "贵州卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225728/index.m3u8"],
    "云南卫视": ["https://hwapi.yunshicloud.com/8xughf/e0bx15.m3u8"],
    "西藏卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225723/index.m3u8"],
    "陕西卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225729/index.m3u8"],
    "青海卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225727/index.m3u8"],
    "宁夏卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225726/index.m3u8"],
    "新疆卫视": ["http://39.134.115.163:8080/PLTV/88888910/224/3221225725/index.m3u8"],
    "深圳卫视": ["http://39.134.24.166/dbiptv.sn.chinamobile.com/PLTV/88888890/224/3221226205/index.m3u8"],
    "延边卫视": ["http://223.110.245.139/PLTV/4/224/3221227002/index.m3u8"],
    "兵团卫视": ["http://112.25.48.68/live/program/live/btws/1300000/mnf.m3u8"],
}

# 卫视备源 ③：tvbus 中转码
SAT_TVBUS = {
    "北京卫视": "bjws",   "天津卫视": "tjws",   "河北卫视": "hews",   "山西卫视": "sxws",
    "内蒙古卫视": "nmgws","辽宁卫视": "lnws",   "吉林卫视": "jlws",   "黑龙江卫视": "hljws",
    "东方卫视": "dfws",   "江苏卫视": "jsws",   "浙江卫视": "zjws",   "安徽卫视": "ahws",
    "东南卫视": "dnws",   "江西卫视": "jxws",   "山东卫视": "sdws",   "河南卫视": "haws",
    "湖北卫视": "hbws",   "湖南卫视": "hnws",   "广东卫视": "gdws",   "广西卫视": "gxws",
    "重庆卫视": "cqws",   "四川卫视": "scws",   "贵州卫视": "gzws",   "云南卫视": "ynws",
    "陕西卫视": "snws",   "甘肃卫视": "gsws",   "青海卫视": "qhws",   "宁夏卫视": "nxws",
    "新疆卫视": "xjws",   "深圳卫视": "szws",   "兵团卫视": "btws",   "延边卫视": "ybws",
}

# CCTV 官方 CDN 三族（央视网 web 播放所用，域名来自多个公开列表交叉一致）
CCTV_WS = {i: "CHCCTV%d" % i for i in range(1, 18)}
CCTV_WS.update({55: "CHCCTV5P", 4: "CHCCTV4", 40: "CHCCTV4K", 80: "CHCCTV8K"})
CCTV_MYQCLOUD = {i: "cctv%d_2" % i for i in range(1, 18)}
CCTV_MYQCLOUD.update({55: "cctv5plus_2", 40: "cctv4k_2", 80: "cctv8k_2"})
CCTV_TVBUS = {
    1: "cctv1", 2: "cctv2", 3: "cctv3", 4: "cctv4", 5: "cctv5", 55: "cctv5p",
    6: "cctv6", 7: "cctv7", 8: "cctv8", 9: "cctv9", 10: "cctv10", 11: "cctv11",
    12: "cctv12", 13: "cctv13", 14: "cctv14", 15: "cctv15", 16: "cctv16", 17: "cctv17",
}
CCTV_SPECIAL = {9: ["https://xykt-fix.github.io/Y77.m3u8"]}   # CCTV-9 额外公开源

CCTV_ORDER = [1, 2, 3, 4, 5, 55, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 40, 80]
CCTV_NAME = {55: "CCTV-5+", 40: "CCTV-4K", 80: "CCTV-8K"}
# EPG 匹配名（对齐 51zmt：CCTV1~CCTV17 / CCTV5+ / CCTV4K）
CCTV_EPG = {55: "CCTV5+", 40: "CCTV4K", 80: "CCTV8K"}

# ---------------- 组装 ----------------
def cctv_channels():
    """返回 [(显示名, epg名, [线路...])]，已按优先级排好"""
    out = []
    for n in CCTV_ORDER:
        disp = CCTV_NAME.get(n, "CCTV-%d" % n)
        epg = CCTV_EPG.get(n, "CCTV%d" % n)
        urls = []
        # ① 央视官方 wscdns（国内最快）
        if n in CCTV_WS:
            urls.append(WSCDN + CCTV_WS[n] + "/playlist.m3u8")
        # ② 央视官方 腾讯云 CDN（国内）
        if n in CCTV_MYQCLOUD:
            urls.append(MYQCLOUD + CCTV_MYQCLOUD[n] + "/index.m3u8")
        # ③ tvbus 中转（境外，兜底）
        if n in CCTV_TVBUS:
            urls.append(TVBUS + CCTV_TVBUS[n] + ".m3u8")
        urls.extend(CCTV_SPECIAL.get(n, []))
        out.append((disp, epg, urls))
    return out

def sat_channels():
    out = []
    for name in SAT_MAIN:
        urls = [CNR + SAT_MAIN[name] + "/playlist.m3u8"]
        urls.extend(SAT_IPTV.get(name, []))
        if name in SAT_TVBUS:
            urls.append(TVBUS + SAT_TVBUS[name] + ".m3u8")
        out.append((name, name, urls))
    return out

# ---------------- 可选实测 ----------------
def verify(all_urls):
    """并发实测：返回 {url: (http_code, 是否可用)}。走 --noproxy 直连，避开本地代理误报 502。"""
    def one(u):
        fd, tmp = tempfile.mkstemp(suffix=".m3u8"); os.close(fd)
        try:
            r = subprocess.run(
                ["curl", "-sL", "--noproxy", "*", "-o", tmp, "-w", "%{http_code}|%{url_effective}",
                 "--max-time", "14", "-A", "Mozilla/5.0", u],
                capture_output=True, text=True, timeout=22)
            parts = r.stdout.strip().split("|")
            h = parts[0]; eff = parts[1] if len(parts) > 1 else ""
            body = open(tmp, "rb").read().decode("utf-8", "ignore")
            ok = (h == "200" and "#EXTM3U" in body)
            return u, h, ok, eff
        except Exception:
            return u, "TIMEOUT", False, ""
        finally:
            try: os.remove(tmp)
            except Exception: pass
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        return {r[0]: (r[1], r[2]) for r in ex.map(one, all_urls)}

# ---------------- 写出 ----------------
def build(outdir, do_verify=False):
    cctv = cctv_channels()
    sat = sat_channels()

    if do_verify:
        urls = []
        for _, _, us in cctv + sat:
            urls.extend(us)
        res = verify(urls)
        # 通的排前面，通的组内保持原优先级
        def sortkey(u):
            code, ok = res.get(u, ("?", False))
            return (0 if ok else 1,)
        def reorder(us):
            return sorted(us, key=sortkey)
        cctv = [(d, e, reorder(us)) for d, e, us in cctv]
        sat = [(d, e, reorder(us)) for d, e, us in sat]
        print("--- 实测 ---")
        for d, e, us in cctv + sat:
            for u in us:
                code, ok = res.get(u, ("?", False))
                print("  [%s] %-6s %s %s" % (code, "OK" if ok else "NO", d, u[:60]))
        sums = {}
        for d, e, us in cctv + sat:
            good = sum(1 for u in us if res.get(u, ("", False))[1])
            sums[d] = good
        print("无可用线路频道:", [k for k, v in sums.items() if v == 0] or "无")

    # M3U
    L = ['#EXTM3U x-tvg-url="%s"' % EPG]
    for disp, epg, urls in cctv:
        for u in urls:
            L.append('#EXTINF:-1 tvg-id="%s" tvg-name="%s" group-title="中央电视台",%s' % (epg, epg, disp))
            L.append(u)
    for disp, epg, urls in sat:
        for u in urls:
            L.append('#EXTINF:-1 tvg-id="%s" tvg-name="%s" group-title="卫视频道",%s' % (epg, epg, disp))
            L.append(u)
    m3u = "\n".join(L) + "\n"

    # TXT（TVBox/DIYP/YYKM genre 格式，同名多行 = 多线路）
    T = ["中央电视台,#genre#"]
    for disp, epg, urls in cctv:
        for u in urls:
            T.append("%s,%s" % (disp, u))
    T.append("卫视频道,#genre#")
    for disp, epg, urls in sat:
        for u in urls:
            T.append("%s,%s" % (disp, u))
    txt = "\n".join(T) + "\n"

    # 自检：IPv6
    v6 = re.findall(r"\[[0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{0,4}){2,}\]", m3u)
    if v6:
        raise SystemExit("发现 IPv6 地址，已中止: %s" % v6[:3])

    os.makedirs(outdir, exist_ok=True)
    m3u_path = os.path.join(outdir, "央卫视直播源.m3u")
    txt_path = os.path.join(outdir, "央卫视直播源.txt")
    with open(m3u_path, "wb") as f:
        f.write(b"\xef\xbb\xbf")
        f.write(m3u.encode("utf-8"))
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt)

    n_ext = len(re.findall(r"^#EXTINF", m3u, re.M))
    n_ch = len(cctv) + len(sat)
    multi = sum(1 for _, _, us in cctv + sat if len(us) >= 2)
    print("频道数: %d   线路总数: %d   含 IPv6: %d" % (n_ch, n_ext, len(v6)))
    print("有 ≥2 条线路的频道: %d / %d" % (multi, n_ch))
    print("M3U 字节: %d   TXT 行数: %d" % (len(m3u.encode("utf-8")), len(T)))
    print("已写出: %s / %s" % (m3u_path, txt_path))

if __name__ == "__main__":
    args = sys.argv[1:]
    outdir = "C:/Users/13125/Desktop/TV直播源"
    if "--out" in args:
        outdir = args[args.index("--out") + 1]
    build(outdir, do_verify=("--verify" in args))
