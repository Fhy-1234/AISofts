# -*- coding: utf-8 -*-
"""Fhy健康助手Lite V1.0 by AI. deps: pip install PySide6 pynput requests"""
from __future__ import annotations
import copy,ctypes,datetime as dt,json,os,random,sys,threading,time
from pathlib import Path
from typing import Any,Dict,List,Optional,Tuple
import requests
from pynput import keyboard,mouse
from PySide6.QtCore import QEasingCurve,QDate,QObject,QPoint,QPropertyAnimation,QThread,QRect,QTime,QTimer,Qt,Signal,Slot
from PySide6.QtGui import QColor,QFont,QIcon,QLinearGradient,QPainter,QPainterPath,QPalette,QPixmap,QBrush,QPen
from PySide6.QtWidgets import QApplication,QCheckBox,QComboBox,QDateEdit,QDialog,QFrame,QGraphicsDropShadowEffect,QGridLayout,QHBoxLayout,QLabel,QLineEdit,QMainWindow,QMenu,QMessageBox,QPushButton,QScrollArea,QSpinBox,QSystemTrayIcon,QTabWidget,QTimeEdit,QVBoxLayout,QWidget

APP_NAME="Fhy健康助手Lite";APP_VERSION="V1.0"
CONFIG_DIR=Path.home()/".FhyHealthLite";CONFIG_FILE=CONFIG_DIR/"config.json";BING=CONFIG_DIR/"bing_wallpaper.jpg"
DP=["久坐伤腰，定时起身。","远眺一分钟，护眼更轻松！","劳逸结合，事半功倍。","欢迎回来，今天也好好照顾自己呀~","你的健康，是我们最在意的事^_^","每一次小休息，都是给身体的充电！","科学用机，让健康和效率同行~"]

def _mk_welcome():
    return {"id":"welcome","type":"welcome","morning_start":5,"morning_end":12,"morning_content":"早上好，新的一天开始啦，今天要做些什么呢？","afternoon_start":12,"afternoon_end":17,"afternoon_content":"下午好，忙碌了这么久，记得歇一歇~","evening_start":17,"evening_end":22,"evening_content":"晚上好，忙碌了一天，享受自己的时光吧！","night_content":"夜深了，请注意休息，明天精神百倍！","position":"top_right","icon":"👋","enabled":True}

def _mk_timed(id_,c,t,ic):
    return {"id":id_,"type":"timed","content":c,"time":t,"date":"","repeat":"daily","position":"top_right","icon":ic,"enabled":True,"weekdays":[],"auto_delete":False}

def _mk_lo(id_,t,wd):
    return {"id":id_,"type":"lights_out","content":"马上就要熄灯了，请准备休息吧！","time":t,"date":"","repeat":"custom","position":"top_right","icon":"💡","enabled":True,"weekdays":wd,"auto_delete":False}

DEFAULT_REMINDERS=[
    _mk_welcome(),
    _mk_timed("p00","新的一天开始啦！","00:00","⭐"),
    _mk_timed("p10","上午好！工作间隙，站起来伸个懒腰吧","10:00","☕"),
    _mk_timed("p12","中午好！午休时间，让眼睛和大脑都歇一歇吧~","12:00","🍱"),
    _mk_timed("p15","下午好！困了吗？起身走走，喝杯茶提提神~","15:00","🍵"),
    _mk_timed("p20","晚上好！别熬夜太久，早点结束工作休息吧~","20:00","🌙"),
    _mk_lo("lo1","23:00",[0,1,2,3,6]),
    _mk_lo("lo2","23:30",[4,5]),
    {"id":"work","type":"work","interval_minutes":60,"content":"","content_mode":"smart","position":"top_right","icon":"⏳","enabled":True}
]

DEFAULT_CONFIG={"general":{"master_switch":True,"auto_start":False,"auto_shutdown_hours":3,"reminder_auto_close_seconds":5},"reminders":copy.deepcopy(DEFAULT_REMINDERS),"phrases":copy.deepcopy(DP)}

TCN={"welcome":"欢迎信息","timed":"普通提醒","lights_out":"熄灯提醒","work":"连续工作提醒","todo":"待办提醒","normal":"自定义"};TEN={v:k for k,v in TCN.items()}
RCN={"daily":"每天","date":"指定日期","workdays":"工作日","weekends":"休息日","custom":"自定义","once":"不重复","":""};REN={v:k for k,v in RCN.items()}
PCN={"fullscreen":"全屏","top_center":"顶部居中","bottom_center":"底部居中","top_left":"左上角","top_right":"右上角","bottom_left":"左下角","bottom_right":"右下角"};PEN={v:k for k,v in PCN.items()}
CMCN={"smart":"智能模式","always_remind":"始终提醒"};CMEN={v:k for k,v in CMCN.items()}
TABS=[("welcome","👋 欢迎"),("timed","⏰ 普通"),("lights_out","💡 熄灯"),("work","⏳ 工作"),("todo","📋 待办")]
DN=["一","二","三","四","五","六","日"]
WH="可用通配符：{Date}→日期 {Time}→时间 {WorkHours}→累计工作时间"

CS="QWidget#card{background:rgba(255,255,255,192);border-radius:18px;border:1px solid rgba(255,255,255,220);}QLabel{color:#263238;font-size:13px;}QLineEdit,QComboBox,QTimeEdit,QDateEdit,QSpinBox{background:rgba(255,255,255,235);border:1px solid rgba(0,0,0,18);border-radius:10px;padding:5px 8px;color:#1f2d3d;min-height:24px;}QComboBox::drop-down{border:none;width:24px;}QComboBox QAbstractItemView{background:white;color:#1f2d3d;selection-background-color:#dcd6f7;border:1px solid #ccc;padding:4px;}QCheckBox{color:#1f2d3d;font-size:13px;}QCheckBox::indicator{width:18px;height:18px;border-radius:5px;border:2px solid #aaa;}QCheckBox::indicator:checked{background:#6c5ce7;border-color:#6c5ce7;}QCalendarWidget QWidget{background-color:white;color:#263238;}QCalendarWidget QToolButton{color:#263238;background-color:#f0f4f8;border:1px solid #ddd;padding:4px;}QCalendarWidget QAbstractItemView{background-color:white;color:#263238;selection-background-color:#dcd6f7;selection-color:#263238;}QCalendarWidget QSpinBox{color:#263238;background:white;}"

def gcu():
    return os.environ.get("USERNAME") or os.environ.get("USER") or "用户"

def ecd():
    CONFIG_DIR.mkdir(parents=True,exist_ok=True)

def dm(b,e):
    o=copy.deepcopy(b)
    for k,v in e.items():
        if isinstance(v,dict) and isinstance(o.get(k),dict):
            o[k]=dm(o[k],v)
        else:
            o[k]=copy.deepcopy(v)
    return o

def cdc():
    ecd(); c=copy.deepcopy(DEFAULT_CONFIG); sc(c); return c

def lc():
    ecd()
    if not CONFIG_FILE.exists():
        return cdc()
    try:
        with open(CONFIG_FILE,"r",encoding="utf-8") as f:
            ld=json.load(f)
        return dm(DEFAULT_CONFIG,ld if isinstance(ld,dict) else {})
    except:
        return cdc()

def sc(c):
    ecd(); open(CONFIG_FILE,"w",encoding="utf-8").write(json.dumps(c,ensure_ascii=False,indent=2))

def gsw():
    try:
        b=ctypes.create_unicode_buffer(4096)
        if ctypes.windll.user32.SystemParametersInfoW(0x0073,len(b),b,0):
            p=b.value.strip()
            if p and os.path.isfile(p):
                return p
    except:
        pass
    return None

def gsac():
    try:
        import winreg; k=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"SOFTWARE\Microsoft\Windows\DWM"); v,_=winreg.QueryValueEx(k,"AccentColor"); winreg.CloseKey(k)
        return QColor((v>>8)&0xFF,(v>>16)&0xFF,(v>>24)&0xFF)
    except:
        return QColor(122,134,255)

def gbi():
    try:
        r=requests.get("https://cn.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN",timeout=6); r.raise_for_status()
        url="https://cn.bing.com"+r.json()["images"][0]["url"]; ir=requests.get(url,timeout=12); ir.raise_for_status()
        open(BING,"wb").write(ir.content); return str(BING)
    except:
        return None

def fwc(w):
    if not w: return ""
    sd=sorted(set(w)); gs=[]; s=e=sd[0]
    for d in sd[1:]:
        if d==e+1: e=d
        else: gs.append((s,e)); s=e=d
    gs.append((s,e)); ps=[]
    for s,e in gs:
        ps.append(DN[s] if s==e else f"{DN[s]}~{DN[e]}")
    return "周"+"、".join(ps)

def sm(r,n):
    rp=r.get("repeat","daily"); ds=r.get("date","")
    if rp=="once":
        if not ds: return True
        try: return dt.date.fromisoformat(ds)==n.date()
        except: return False
    if rp=="workdays": return n.weekday()<5
    if rp=="weekends": return n.weekday()>=5
    if rp=="custom": return n.weekday() in r.get("weekdays",[])
    if rp=="date" and ds:
        try: return dt.date.fromisoformat(ds)==n.date()
        except: pass
    return True

def gnmd(r):
    rp=r.get("repeat","daily"); td=dt.date.today()
    if rp=="daily": return td
    if rp=="workdays":
        d=td
        while d.weekday()>=5: d+=dt.timedelta(days=1)
        return d
    if rp=="weekends":
        d=td
        while d.weekday()<5: d+=dt.timedelta(days=1)
        return d
    if rp=="custom":
        wd=r.get("weekdays",[])
        if not wd: return td
        d=td
        for _ in range(7):
            if d.weekday() in wd: return d
            d+=dt.timedelta(days=1)
        return td
    if rp in("once","date") and r.get("date"):
        try: return dt.date.fromisoformat(r["date"])
        except: pass
    return td

def pw(t,wm=0):
    if not t: return t
    n=dt.datetime.now()
    t=t.replace("{Date}",f"{n.year}年{n.month}月{n.day}日").replace("{Time}",n.strftime("%H:%M"))
    h,m=divmod(wm,60); ws=f"{h}小时{m}分钟" if h>0 and m>0 else(f"{h}小时" if h>0 else f"{m}分钟")
    return t.replace("{WorkHours}",ws)

def gnrt(r,wm=0):
    rt=r.get("type","timed")
    if rt=="welcome": return "下次提醒：程序启动时"
    if rt=="work":
        iv=r.get("interval_minutes",60); hi,mi=divmod(iv,60)
        ivs=f"{hi}小时" if hi>0 and mi==0 else(f"{mi}分钟" if hi==0 else f"{hi}小时{mi}分钟")
        hu,mu=divmod(wm,60); us=f"{hu}小时{mu}分钟" if hu>0 and mu>0 else(f"{hu}小时" if hu>0 else f"{mu}分钟")
        cm=r.get("content_mode","smart"); ms=CMCN.get(cm,"智能模式")
        return f"每隔{ivs}提醒一次 | 当前已使用：{us} | 模式：{ms}"
    ts=r.get("time","")
    if not ts: return "未设置时间"
    try: hh,mm=map(int,ts.split(":"))
    except: return "时间格式错误"
    nw=dt.datetime.now(); td=nw.date(); rp=r.get("repeat","daily")
    if rp=="daily":
        tg=dt.datetime(td.year,td.month,td.day,hh,mm)
        return f"下次提醒：今天 {ts}" if tg>nw else f"下次提醒：明天 {ts}"
    if rp=="workdays":
        d=td; tg=dt.datetime(d.year,d.month,d.day,hh,mm)
        if tg>nw and d.weekday()<5: return f"下次提醒：今天 {ts}"
        d+=dt.timedelta(days=1)
        for _ in range(7):
            if d.weekday()<5: return f"下次提醒：{d.strftime('%m/%d')} {ts}"
            d+=dt.timedelta(days=1)
    if rp=="weekends":
        d=td; tg=dt.datetime(d.year,d.month,d.day,hh,mm)
        if tg>nw and d.weekday()>=5: return f"下次提醒：今天 {ts}"
        d+=dt.timedelta(days=1)
        for _ in range(7):
            if d.weekday()>=5: return f"下次提醒：{d.strftime('%m/%d')} {ts}"
            d+=dt.timedelta(days=1)
    if rp=="custom":
        wd=r.get("weekdays",[]); wt=fwc(wd) if wd else ""
        d=td; tg=dt.datetime(d.year,d.month,d.day,hh,mm)
        if tg>nw and d.weekday() in wd: return f"下次提醒：今天 {ts}（{wt}）"
        d+=dt.timedelta(days=1)
        for _ in range(7):
            if d.weekday() in wd: return f"下次提醒：{d.strftime('%m/%d')} {ts}（{wt}）"
            d+=dt.timedelta(days=1)
    if rp in("once","date"):
        ds=r.get("date","")
        if ds: return f"下次提醒：{ds} {ts}"
        return f"下次提醒：{ts}（仅一次）"
    return f"下次提醒：{ts}"

def arm(w,r):
    ww,hh=w.width(),w.height()
    if ww<=0 or hh<=0: return
    pm=QPixmap(ww,hh); pm.fill(Qt.transparent)
    p=QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setBrush(QColor(255,255,255)); p.setPen(Qt.NoPen)
    pa=QPainterPath(); pa.addRoundedRect(QRect(0,0,ww,hh),r,r); p.drawPath(pa); p.end(); w.setMask(pm.mask())

def sim(pr,t,x):
    m=QMessageBox(pr); m.setWindowTitle(t); m.setText(x); m.setIcon(QMessageBox.Information)
    m.setStyleSheet("QMessageBox{background:#f0f4f8;}QMessageBox QLabel{color:#263238;font-size:14px;}QMessageBox QPushButton{background:#6c5ce7;color:white;border:none;border-radius:10px;padding:8px 20px;font-weight:600;min-width:80px;}")
    m.exec()

class DD(QDialog):
    def __init__(s,p=None):
        super().__init__(p); s._dp=None
    def mousePressEvent(s,e):
        if e.button()==Qt.LeftButton:
            s._dp=e.globalPosition().toPoint()-s.window().frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(s,e):
        if s._dp is not None and e.buttons()&Qt.LeftButton:
            s.window().move(e.globalPosition().toPoint()-s._dp); e.accept()
    def mouseReleaseEvent(s,e):
        s._dp=None

class PQ(QObject):
    rp=Signal(dict)
    def __init__(s):
        super().__init__(); s._q=[]; s._s=False
    def eq(s,i):
        s._q.append(i); s._tn()
    def _tn(s):
        if s._s or not s._q: return
        s._s=True; s.rp.emit(s._q.pop(0))
    def oc(s):
        s._s=False; s._tn()

class IM(QObject):
    IDLE_THRESHOLD=300
    def __init__(s):
        super().__init__(); s._lk=threading.Lock(); s.la=time.time(); s._cs=time.time(); s._r=True; s.kl=s.ml=None; s._sl()
    def _rc(s):
        with s._lk:
            now=time.time()
            if now-s.la>s.IDLE_THRESHOLD:
                s._cs=now
            s.la=now
    def _sl(s):
        try:
            s.kl=keyboard.Listener(on_press=lambda _:s._rc())
            s.ml=mouse.Listener(on_move=lambda x,y:s._rc(),on_click=lambda x,y,b,p:s._rc(),on_scroll=lambda x,y,dx,dy:s._rc())
            s.kl.daemon=s.ml.daemon=True; s.kl.start(); s.ml.start()
        except:
            s.kl=s.ml=None
    def gcm(s):
        with s._lk:
            now=time.time()
            if now-s.la>s.IDLE_THRESHOLD: return 0
            return max(0,int((now-s._cs)/60))
    def gim(s):
        with s._lk:
            return int((time.time()-s.la)/60)
    def stop(s):
        s._r=False
        for l in(s.kl,s.ml):
            try:
                if l: l.stop()
            except: pass

class RP(QDialog):
    cl=Signal()
    def __init__(s,i,p=None):
        super().__init__(p); s.info=i; s.fa=s.sa=s.at=None
        s.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool); s.setAttribute(Qt.WA_TranslucentBackground,True); s.setModal(False); s._bu(); s._show()
    def _bu(s):
        s.sg=QApplication.primaryScreen().availableGeometry(); s.ps=s.info.get("position","top_right")
        s.ic=s.info.get("icon","🔔"); s.ct=s.info.get("content","提醒")
        s.ds_=s.info.get("datetime_str",dt.datetime.now().strftime("%Y/%m/%d %H:%M"))
        s.cn=QFrame(s); s.cn.setObjectName("pC")
        s.cn.setStyleSheet("#pC{background:rgba(18,18,18,205);border:1px solid rgba(255,255,255,48);border-radius:24px;}QLabel{color:white;}QPushButton{background:transparent;border:none;color:white;}QPushButton:hover{color:#ff9f9f;}")
        sh=QGraphicsDropShadowEffect(s.cn); sh.setBlurRadius(36); sh.setOffset(0,10); sh.setColor(QColor(0,0,0,130)); s.cn.setGraphicsEffect(sh)
        ol=QVBoxLayout(s); ol.setContentsMargins(0,0,0,0); ol.addWidget(s.cn)
        if s.ps in("top_left","top_right","bottom_left","bottom_right"):
            s.cn.setFixedSize(430,160); lo=QVBoxLayout(s.cn); lo.setContentsMargins(24,20,24,18); lo.setSpacing(10)
            t=QLabel(f"{s.ic} {s.ct}"); t.setWordWrap(True); t.setStyleSheet("font-size:18px;font-weight:700;"); lo.addWidget(t)
            b=QHBoxLayout(); tl=QLabel(s.ds_); tl.setStyleSheet("font-size:13px;color:rgba(255,255,255,180);")
            cb=QPushButton("✕"); cb.setFixedSize(26,26); cb.setStyleSheet("font-size:18px;font-weight:700;"); cb.clicked.connect(s.cp_)
            b.addWidget(tl); b.addStretch(1); b.addWidget(cb); lo.addLayout(b)
        elif s.ps in("top_center","bottom_center"):
            s.cn.setFixedSize(620,180); lo=QVBoxLayout(s.cn); lo.setContentsMargins(26,18,26,18); lo.setSpacing(10)
            t=QLabel(f"{s.ic} {s.ct}"); t.setWordWrap(True); t.setAlignment(Qt.AlignCenter); t.setStyleSheet("font-size:22px;font-weight:700;"); lo.addWidget(t)
            b=QHBoxLayout(); tl=QLabel(s.ds_); tl.setStyleSheet("font-size:13px;color:rgba(255,255,255,180);")
            cb=QPushButton("✕"); cb.setFixedSize(26,26); cb.setStyleSheet("font-size:18px;font-weight:700;"); cb.clicked.connect(s.cp_)
            b.addWidget(tl); b.addStretch(1); b.addWidget(cb); lo.addLayout(b)
        else:
            s.setFixedSize(s.sg.width(),s.sg.height()); s.cn.setFixedSize(s.sg.width(),s.sg.height())
            lo=QVBoxLayout(s.cn); lo.setContentsMargins(36,28,36,28); lo.setSpacing(24)
            tp=QHBoxLayout(); tl=QLabel(s.ds_); tl.setStyleSheet("font-size:18px;color:rgba(255,255,255,180);")
            cb=QPushButton("✕"); cb.setFixedSize(34,34); cb.setStyleSheet("font-size:24px;font-weight:700;"); cb.clicked.connect(s.cp_)
            tp.addWidget(tl); tp.addStretch(1); tp.addWidget(cb); lo.addLayout(tp)
            t=QLabel(f"{s.ic} {s.ct}"); t.setWordWrap(True); t.setAlignment(Qt.AlignCenter); t.setStyleSheet("font-size:34px;font-weight:800;")
            lo.addStretch(1); lo.addWidget(t); lo.addStretch(2)
    def _ac(s):
        return max(1,int(s.info.get("auto_close_seconds",5)))*1000
    def _show(s):
        g=s.sg; ms=s._ac(); s.show()
        if s.ps=="fullscreen":
            s.setWindowOpacity(0.0); s.fa=QPropertyAnimation(s,b"windowOpacity",s); s.fa.setDuration(260); s.fa.setStartValue(0.0); s.fa.setEndValue(1.0); s.fa.start(); s.move(g.left(),g.top())
            s.at=QTimer(s); s.at.setSingleShot(True); s.at.timeout.connect(s.cp_); s.at.start(ms); return
        w,h=s.cn.width(),s.cn.height(); mg=18; tx=g.left()+mg; ty=g.top()+mg; sx=tx; sy=ty
        if s.ps=="top_right": tx=g.right()-w-mg; ty=g.top()+36; sy=g.top()-h-20
        elif s.ps=="top_left": ty=g.top()+36; sy=g.top()-h-20
        elif s.ps=="bottom_right": tx=g.right()-w-mg; ty=g.bottom()-h-28; sy=g.bottom()+20
        elif s.ps=="bottom_left": ty=g.bottom()-h-28; sy=g.bottom()+20
        elif s.ps=="top_center": tx=g.center().x()-w//2; ty=g.top()+24; sy=g.top()-h-20
        elif s.ps=="bottom_center": tx=g.center().x()-w//2; ty=g.bottom()-h-24; sy=g.bottom()+20
        s.move(sx,sy); s.sa=QPropertyAnimation(s,b"pos",s); s.sa.setDuration(360); s.sa.setEasingCurve(QEasingCurve.OutCubic)
        s.sa.setStartValue(QPoint(sx,sy)); s.sa.setEndValue(QPoint(tx,ty)); s.sa.start()
        s.at=QTimer(s); s.at.setSingleShot(True); s.at.timeout.connect(s.cp_); s.at.start(ms)
    @Slot()
    def cp_(s):
        if s.at and s.at.isActive(): s.at.stop()
        s.close()
    def closeEvent(s,e):
        s.cl.emit(); super().closeEvent(e)

class RPM(QObject):
    pad=Signal(str)
    def __init__(s):
        super().__init__(); s.q=PQ(); s.q.rp.connect(s._sp,Qt.QueuedConnection); s.cp_=None; s._ci=None; s._lk=threading.Lock()
    @Slot(dict)
    def push(s,i):
        s.q.eq(i)
    @Slot(dict)
    def _sp(s,i):
        with s._lk:
            if s.cp_ is not None:
                s.q._q.insert(0,i); return
            p=RP(i); p.cl.connect(s._oc); s.cp_=p; s._ci=i; p.show()
    @Slot()
    def _oc(s):
        with s._lk:
            if s._ci and s._ci.get("auto_delete",False):
                rid=s._ci.get("id","")
                if rid: s.pad.emit(rid)
            if s.cp_: s.cp_.deleteLater(); s.cp_=None
            s._ci=None; s.q.oc()

class BW(QObject):
    tg=Signal(dict)
    def __init__(s,c):
        super().__init__(); s.c=c; s.t=None; s.td=dt.date.today()
    def me(s):
        return bool(s.c.get("general",{}).get("master_switch",True))
    def fr(s,r):
        for r_ in s.c.get("reminders",[]):
            if r_.get("type")==r: return r_
        return None
    def ep(s,r,c=None,wm=0):
        ds=dt.datetime.now().strftime("%Y/%m/%d %H:%M"); ac=s.c.get("general",{}).get("reminder_auto_close_seconds",5)
        ct=pw(c,wm) if c is not None else pw(r.get("content","提醒"),wm)
        s.tg.emit({"content":ct,"datetime_str":ds,"position":r.get("position","top_right"),"icon":r.get("icon","🔔"),"auto_close_seconds":ac,"auto_delete":r.get("auto_delete",False),"id":r.get("id","")})

class TRW(BW):
    def __init__(s,c):
        super().__init__(c); s.fk:set[Tuple[str,str]]=set(); s.wsd=None
    @Slot()
    def start(s):
        s.t=QTimer(s); s.t.timeout.connect(s.ck); s.t.start(20000); QTimer.singleShot(1200,s.sw); s.ck()
    @Slot()
    def sw(s):
        if not s.me(): return
        r=s.fr("welcome")
        if not r or not r.get("enabled",True): return
        tk=dt.date.today().isoformat()
        if s.wsd==tk: return
        s.wsd=tk; h=dt.datetime.now().hour
        ms=r.get("morning_start",5); me_=r.get("morning_end",12); as_=r.get("afternoon_start",12); ae=r.get("afternoon_end",17); es=r.get("evening_start",17); ee=r.get("evening_end",22)
        if ms<=h<me_: c=r.get("morning_content","早上好！")
        elif as_<=h<ae: c=r.get("afternoon_content","下午好！")
        elif es<=h<ee: c=r.get("evening_content","晚上好！")
        else: c=r.get("night_content","夜深了，请注意休息。")
        s.ep(r,c)
    @Slot()
    def ck(s):
        if not s.me(): return
        nw=dt.datetime.now(); tk=nw.date().isoformat()
        if tk!=s.td.isoformat(): s.td=nw.date(); s.fk={k for k in s.fk if k[1]==tk}
        for r in s.c.get("reminders",[]):
            if not r.get("enabled",True): continue
            rt=r.get("type","timed")
            if rt in("work","welcome"): continue
            ts=r.get("time","")
            if not ts: continue
            try: hh,mm=map(int,ts.split(":"))
            except: continue
            if nw.hour!=hh or nw.minute!=mm: continue
            if not sm(r,nw): continue
            ky=(r.get("id",str(id(r))),tk)
            if ky in s.fk: continue
            s.fk.add(ky); s.ep(r)

class WRW(BW):
    def __init__(s,c,im):
        super().__init__(c); s.im=im; s.st_=QTimer(s); s.st_.setSingleShot(True); s.st_.timeout.connect(s._sd); s.lnm=-1; s.ws=False
    @Slot()
    def start(s):
        s.t=QTimer(s); s.t.timeout.connect(s.ck); s.t.start(60000); s.ck()
    @Slot()
    def ck(s):
        if not s.me():
            if s.st_.isActive(): s.st_.stop()
            return
        r=s.fr("work")
        if not r or not r.get("enabled",True): return
        iv=int(r.get("interval_minutes",60)); mi=s.im.gcm()
        if mi>=iv and(s.lnm<0 or mi>=s.lnm+iv):
            s.lnm=mi; c=r.get("content","").strip()
            if not c:
                h,m=divmod(mi,60)
                ts=f"{h}小时{m}分钟" if h>0 and m>0 else(f"{h}小时" if h>0 else f"{m}分钟")
                cm=r.get("content_mode","smart")
                if cm=="always_remind":
                    c=f"你已连续使用设备{ts}，请休息一下吧！"
                else:
                    if h<3: c=f"你已连续使用设备{ts}。"
                    else: c=f"你已连续使用设备{ts}，为了身体健康，请休息一下吧！"
            s.ep(r,c,mi)
        idle=s.im.gim()
        ah=int(s.c.get("general",{}).get("auto_shutdown_hours",3))
        if idle>=ah*60:
            if not s.st_.isActive() and not s.ws:
                s.ws=True; fh=idle//60; s.ep(r,f"连续{fh}小时未操作，系统将在1分钟后自动关机！",idle); s.st_.start(60000)
        else:
            s.ws=False
            if s.st_.isActive() and idle<ah*60: s.st_.stop()
    @Slot()
    def _sd(s):
        try: os.system("shutdown /s /t 10")
        except: pass
        s.ws=False

class CB(QWidget):
    def __init__(s,p=None):
        super().__init__(p); s.pm=None; s.sc_=QColor(122,134,255); s.setAttribute(Qt.WA_TransparentForMouseEvents,True)
    def sbp(s,pm):
        s.pm=pm; s.update()
    def sbc(s,c):
        s.pm=None; s.sc_=c; s.update()
    def paintEvent(s,e):
        p=QPainter(s); p.setRenderHint(QPainter.Antialiasing); r=s.rect()
        if s.pm and not s.pm.isNull():
            sc=s.pm.scaled(r.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
            sx=max(0,(sc.width()-r.width())//2); sy=max(0,(sc.height()-r.height())//2)
            p.drawPixmap(r,sc,QRect(sx,sy,r.width(),r.height()))
        else:
            p.fillRect(r,s.sc_)
        g=QLinearGradient(0,0,s.width(),s.height()); g.setColorAt(0,QColor(255,255,255,26)); g.setColorAt(1,QColor(0,0,0,18))
        p.fillRect(r,QBrush(g))

class WS(QWidget):
    ch=Signal()
    def __init__(s,p=None):
        super().__init__(p); s._b=False; lo=QHBoxLayout(s); lo.setContentsMargins(0,0,0,0); lo.setSpacing(2); s.cbs=[]
        for i,n in enumerate(DN):
            cb=QCheckBox(n); cb.setStyleSheet("QCheckBox{font-size:12px;color:#263238;spacing:2px;}QCheckBox::indicator{width:16px;height:16px;border-radius:4px;border:1px solid #aaa;}QCheckBox::indicator:checked{background:#6c5ce7;border-color:#6c5ce7;}")
            cb.stateChanged.connect(s._oc); lo.addWidget(cb); s.cbs.append(cb)
    def sw(s,wd):
        s._b=True; [cb.setChecked(i in wd) for i,cb in enumerate(s.cbs)]; s._b=False
    def gw(s):
        return [i for i,cb in enumerate(s.cbs) if cb.isChecked()]
    def _oc(s):
        if not s._b: s.ch.emit()

def _add_whint(lo):
    lb=QLabel(WH); lb.setStyleSheet("color:#999;font-size:11px;"); lo.addWidget(lb)

class WRC(QWidget):
    def __init__(s,d,p=None):
        super().__init__(p); s.d=d; s._b=True; s.setStyleSheet(CS); s.setObjectName("card")
        sh=QGraphicsDropShadowEffect(s); sh.setBlurRadius(20); sh.setOffset(0,6); sh.setColor(QColor(0,0,0,45)); s.setGraphicsEffect(sh)
        lo=QVBoxLayout(s); lo.setContentsMargins(14,10,14,10); lo.setSpacing(6)
        r0=QHBoxLayout(); s.ecb=QCheckBox("启用"); s.ie=QLineEdit(); s.ie.setPlaceholderText("图标"); s.ie.setMaximumWidth(50); s.pc=QComboBox(); s.pc.addItems(list(PEN.keys()))
        r0.addWidget(s.ecb); r0.addWidget(QLabel("图标")); r0.addWidget(s.ie); r0.addWidget(QLabel("位置")); r0.addWidget(s.pc); r0.addStretch(1); lo.addLayout(r0)
        r1=QHBoxLayout(); r1.addWidget(QLabel("🌅 早上")); s.ms=QSpinBox(); s.ms.setRange(0,23); s.me_=QSpinBox(); s.me_.setRange(0,23); s.mc=QLineEdit(); s.mc.setMinimumWidth(200)
        r1.addWidget(s.ms); r1.addWidget(QLabel("时-")); r1.addWidget(s.me_); r1.addWidget(QLabel("时")); r1.addWidget(s.mc,1); lo.addLayout(r1)
        r2=QHBoxLayout(); r2.addWidget(QLabel("☀️ 下午")); s.as_=QSpinBox(); s.as_.setRange(0,23); s.ae=QSpinBox(); s.ae.setRange(0,23); s.ac=QLineEdit(); s.ac.setMinimumWidth(200)
        r2.addWidget(s.as_); r2.addWidget(QLabel("时-")); r2.addWidget(s.ae); r2.addWidget(QLabel("时")); r2.addWidget(s.ac,1); lo.addLayout(r2)
        r3=QHBoxLayout(); r3.addWidget(QLabel("🌆 晚上")); s.es=QSpinBox(); s.es.setRange(0,23); s.ee=QSpinBox(); s.ee.setRange(0,23); s.ec_=QLineEdit(); s.ec_.setMinimumWidth(200)
        r3.addWidget(s.es); r3.addWidget(QLabel("时-")); r3.addWidget(s.ee); r3.addWidget(QLabel("时")); r3.addWidget(s.ec_,1); lo.addLayout(r3)
        r4=QHBoxLayout(); r4.addWidget(QLabel("🌙 夜间")); s.nc=QLineEdit(); s.nc.setMinimumWidth(200); r4.addWidget(s.nc,1); r4.addStretch(1); lo.addLayout(r4)
        s.il=QLabel(""); s.il.setStyleSheet("color:#6c5ce7;font-size:12px;font-weight:600;"); lo.addWidget(s.il); _add_whint(lo)
        s._ld()
        for w in(s.ecb,s.ie,s.ms,s.me_,s.mc,s.as_,s.ae,s.ac,s.es,s.ee,s.ec_,s.nc,s.pc):
            if isinstance(w,QCheckBox): w.stateChanged.connect(s._oc)
            elif isinstance(w,QSpinBox): w.valueChanged.connect(s._oc)
            elif isinstance(w,QComboBox): w.currentTextChanged.connect(s._oc)
            else: w.textChanged.connect(s._oc)
        s._b=False; s._oc()
    def _ld(s):
        s.ecb.setChecked(bool(s.d.get("enabled",True))); s.ie.setText(s.d.get("icon","👋")); s.pc.setCurrentText(PCN.get(s.d.get("position","top_right"),"右上角"))
        s.ms.setValue(int(s.d.get("morning_start",5))); s.me_.setValue(int(s.d.get("morning_end",12))); s.mc.setText(s.d.get("morning_content",""))
        s.as_.setValue(int(s.d.get("afternoon_start",12))); s.ae.setValue(int(s.d.get("afternoon_end",17))); s.ac.setText(s.d.get("afternoon_content",""))
        s.es.setValue(int(s.d.get("evening_start",17))); s.ee.setValue(int(s.d.get("evening_end",22))); s.ec_.setText(s.d.get("evening_content",""))
        s.nc.setText(s.d.get("night_content",""))
    def _oc(s):
        if s._b: return
        s.d["enabled"]=s.ecb.isChecked(); s.d["icon"]=s.ie.text().strip() or "👋"; s.d["position"]=PEN.get(s.pc.currentText(),"top_right")
        s.d["morning_start"]=s.ms.value(); s.d["morning_end"]=s.me_.value(); s.d["morning_content"]=s.mc.text().strip()
        s.d["afternoon_start"]=s.as_.value(); s.d["afternoon_end"]=s.ae.value(); s.d["afternoon_content"]=s.ac.text().strip()
        s.d["evening_start"]=s.es.value(); s.d["evening_end"]=s.ee.value(); s.d["evening_content"]=s.ec_.text().strip()
        s.d["night_content"]=s.nc.text().strip(); s.il.setText(gnrt(s.d))
    def gd(s):
        return s.d

class TRC(QWidget):
    dr=Signal(str)
    def __init__(s,d,p=None):
        super().__init__(p); s.d=d; s._b=True; s.setStyleSheet(CS); s.setObjectName("card")
        sh=QGraphicsDropShadowEffect(s); sh.setBlurRadius(20); sh.setOffset(0,6); sh.setColor(QColor(0,0,0,45)); s.setGraphicsEffect(sh)
        lo=QVBoxLayout(s); lo.setContentsMargins(14,10,14,10); lo.setSpacing(6)
        r1=QHBoxLayout(); s.ecb=QCheckBox("启用"); s.ie=QLineEdit(); s.ie.setPlaceholderText("图标"); s.ie.setMaximumWidth(50); s.ce=QLineEdit(); s.ce.setMinimumWidth(140)
        db=QPushButton("🗑"); db.setFixedSize(28,28); db.setStyleSheet("QPushButton{background:rgba(231,76,60,180);color:white;border:none;border-radius:8px;font-size:13px;}QPushButton:hover{background:rgba(231,76,60,230);}")
        db.clicked.connect(lambda:s.dr.emit(s.d.get("id","")))
        r1.addWidget(s.ecb); r1.addWidget(QLabel("图标")); r1.addWidget(s.ie); r1.addWidget(QLabel("内容")); r1.addWidget(s.ce,1); r1.addWidget(db); lo.addLayout(r1)
        r2=QHBoxLayout(); s.te=QTimeEdit(); s.te.setDisplayFormat("HH:mm"); s.de=QDateEdit(); s.de.setCalendarPopup(True); s.de.setDisplayFormat("yyyy-MM-dd")
        s.rc=QComboBox(); s.rc.addItems(list(REN.keys())); s.pc=QComboBox(); s.pc.addItems(list(PEN.keys()))
        s.ws_=WS(); s.wl=QLabel(""); s.wl.setStyleSheet("color:#6c5ce7;font-weight:600;font-size:12px;")
        r2.addWidget(QLabel("时间")); r2.addWidget(s.te); r2.addWidget(QLabel("日期")); r2.addWidget(s.de); r2.addWidget(QLabel("重复")); r2.addWidget(s.rc)
        r2.addWidget(s.ws_); r2.addWidget(s.wl); r2.addWidget(QLabel("位置")); r2.addWidget(s.pc); r2.addStretch(1); lo.addLayout(r2)
        s.il=QLabel(""); s.il.setStyleSheet("color:#6c5ce7;font-size:12px;font-weight:600;"); lo.addWidget(s.il); _add_whint(lo)
        s._ld(); s.rc.currentTextChanged.connect(s._sy); s.ws_.ch.connect(s._ow)
        for w in(s.ecb,s.ie,s.ce,s.te,s.de,s.rc,s.pc):
            if isinstance(w,QCheckBox): w.stateChanged.connect(s._oc)
            elif isinstance(w,QTimeEdit): w.timeChanged.connect(s._oc)
            elif isinstance(w,QDateEdit): w.dateChanged.connect(s._oc)
            elif isinstance(w,QComboBox): w.currentTextChanged.connect(s._oc)
            else: w.textChanged.connect(s._oc)
        s._b=False; s._sy(); s._oc()
    def _ld(s):
        s.ecb.setChecked(bool(s.d.get("enabled",True))); s.ie.setText(s.d.get("icon","🔔")); s.ce.setText(s.d.get("content",""))
        t=s.d.get("time",""); qt=QTime.fromString(t,"HH:mm"); s.te.setTime(qt if qt.isValid() else QTime(12,0))
        sd=gnmd(s.d); qd=QDate(sd.year,sd.month,sd.day); ds=s.d.get("date","")
        if ds:
            try:
                p_=QDate.fromString(ds,"yyyy-MM-dd")
                if p_.isValid(): qd=p_
            except: pass
        s.de.setDate(qd); s.rc.setCurrentText(RCN.get(s.d.get("repeat","daily"),"每天")); s.pc.setCurrentText(PCN.get(s.d.get("position","top_right"),"右上角"))
        wd=s.d.get("weekdays",[])
        if isinstance(wd,list): s.ws_.sw(wd)
    def _sy(s):
        rp=s.rc.currentText(); s.de.setEnabled(rp=="指定日期"); sw=rp=="自定义"; s.ws_.setVisible(sw); s.wl.setVisible(sw)
        if sw:
            wd=s.ws_.gw(); s.wl.setText(fwc(wd) if wd else "请选择")
    def _ow(s):
        s.d["weekdays"]=s.ws_.gw(); s.wl.setText(fwc(s.d["weekdays"]) if s.d["weekdays"] else "请选择"); s._oc()
    def _oc(s):
        if s._b: return
        s.d["enabled"]=s.ecb.isChecked(); s.d["icon"]=s.ie.text().strip() or "🔔"; s.d["content"]=s.ce.text().strip(); s.d["time"]=s.te.time().toString("HH:mm")
        s.d["date"]=s.de.date().toString("yyyy-MM-dd") if s.rc.currentText()=="指定日期" else ""; s.d["repeat"]=REN.get(s.rc.currentText(),"daily")
        s.d["position"]=PEN.get(s.pc.currentText(),"top_right")
        if s.rc.currentText()=="自定义": s.d["weekdays"]=s.ws_.gw()
        s.il.setText(gnrt(s.d))
    def gd(s):
        return s.d

class LRC(QWidget):
    dr=Signal(str)
    def __init__(s,d,p=None):
        super().__init__(p); s.d=d; s._b=True; s.setStyleSheet(CS); s.setObjectName("card")
        sh=QGraphicsDropShadowEffect(s); sh.setBlurRadius(20); sh.setOffset(0,6); sh.setColor(QColor(0,0,0,45)); s.setGraphicsEffect(sh)
        lo=QVBoxLayout(s); lo.setContentsMargins(14,10,14,10); lo.setSpacing(6)
        r1=QHBoxLayout(); s.ecb=QCheckBox("启用"); s.ie=QLineEdit(); s.ie.setPlaceholderText("图标"); s.ie.setMaximumWidth(50); s.ce=QLineEdit(); s.ce.setMinimumWidth(140)
        db=QPushButton("🗑"); db.setFixedSize(28,28); db.setStyleSheet("QPushButton{background:rgba(231,76,60,180);color:white;border:none;border-radius:8px;font-size:13px;}QPushButton:hover{background:rgba(231,76,60,230);}")
        db.clicked.connect(lambda:s.dr.emit(s.d.get("id","")))
        r1.addWidget(s.ecb); r1.addWidget(QLabel("图标")); r1.addWidget(s.ie); r1.addWidget(QLabel("内容")); r1.addWidget(s.ce,1); r1.addWidget(db); lo.addLayout(r1)
        r2=QHBoxLayout(); s.te=QTimeEdit(); s.te.setDisplayFormat("HH:mm"); s.pc=QComboBox(); s.pc.addItems(list(PEN.keys())); s.ws_=WS(); s.wl=QLabel(""); s.wl.setStyleSheet("color:#6c5ce7;font-weight:600;font-size:12px;")
        r2.addWidget(QLabel("时间")); r2.addWidget(s.te); r2.addWidget(QLabel("星期")); r2.addWidget(s.ws_); r2.addWidget(s.wl); r2.addWidget(QLabel("位置")); r2.addWidget(s.pc); r2.addStretch(1); lo.addLayout(r2)
        s.il=QLabel(""); s.il.setStyleSheet("color:#6c5ce7;font-size:12px;font-weight:600;"); lo.addWidget(s.il); _add_whint(lo)
        s._ld(); s.ws_.ch.connect(s._ow)
        for w in(s.ecb,s.ie,s.ce,s.te,s.pc):
            if isinstance(w,QCheckBox): w.stateChanged.connect(s._oc)
            elif isinstance(w,QTimeEdit): w.timeChanged.connect(s._oc)
            elif isinstance(w,QComboBox): w.currentTextChanged.connect(s._oc)
            else: w.textChanged.connect(s._oc)
        s._b=False; s._oc()
    def _ld(s):
        s.ecb.setChecked(bool(s.d.get("enabled",True))); s.ie.setText(s.d.get("icon","💡")); s.ce.setText(s.d.get("content",""))
        t=s.d.get("time",""); qt=QTime.fromString(t,"HH:mm"); s.te.setTime(qt if qt.isValid() else QTime(23,0))
        s.pc.setCurrentText(PCN.get(s.d.get("position","top_right"),"右上角")); wd=s.d.get("weekdays",[])
        if isinstance(wd,list): s.ws_.sw(wd)
    def _ow(s):
        s.d["weekdays"]=s.ws_.gw(); s._oc()
    def _oc(s):
        if s._b: return
        s.d["enabled"]=s.ecb.isChecked(); s.d["icon"]=s.ie.text().strip() or "💡"; s.d["content"]=s.ce.text().strip(); s.d["time"]=s.te.time().toString("HH:mm")
        s.d["position"]=PEN.get(s.pc.currentText(),"top_right"); s.d["repeat"]="custom"; s.d["weekdays"]=s.ws_.gw()
        s.wl.setText(fwc(s.d["weekdays"]) if s.d["weekdays"] else "请选择"); s.il.setText(gnrt(s.d))
    def gd(s):
        return s.d

class WoRC(QWidget):
    def __init__(s,d,im=None,p=None):
        super().__init__(p); s.d=d; s._b=True; s.im=im; s.setStyleSheet(CS); s.setObjectName("card")
        sh=QGraphicsDropShadowEffect(s); sh.setBlurRadius(20); sh.setOffset(0,6); sh.setColor(QColor(0,0,0,45)); s.setGraphicsEffect(sh)
        lo=QVBoxLayout(s); lo.setContentsMargins(14,10,14,10); lo.setSpacing(6)
        r1=QHBoxLayout(); s.ecb=QCheckBox("启用"); s.ie=QLineEdit(); s.ie.setPlaceholderText("图标"); s.ie.setMaximumWidth(50); s.pc=QComboBox(); s.pc.addItems(list(PEN.keys()))
        r1.addWidget(s.ecb); r1.addWidget(QLabel("图标")); r1.addWidget(s.ie); r1.addWidget(QLabel("位置")); r1.addWidget(s.pc); r1.addStretch(1); lo.addLayout(r1)
        r2=QHBoxLayout(); r2.addWidget(QLabel("提醒间隔")); s.ivc=QComboBox(); s.ivc.addItems(["15分钟","30分钟","45分钟","1小时","1.5小时","2小时","3小时"]); r2.addWidget(s.ivc); r2.addStretch(1); lo.addLayout(r2)
        # 提醒内容放在内容模式之前，更突出
        r3=QHBoxLayout(); r3.addWidget(QLabel("提醒内容")); s.ce=QLineEdit(); s.ce.setPlaceholderText("留空按内容模式自动生成，自定义文字可覆盖模式（支持{Date}{Time}{WorkHours}）"); s.ce.setMinimumWidth(300); r3.addWidget(s.ce,1); lo.addLayout(r3)
        r2b=QHBoxLayout(); r2b.addWidget(QLabel("内容模式")); s.cmc=QComboBox(); s.cmc.addItems(list(CMEN.keys())); r2b.addWidget(s.cmc)
        s.cmdl=QLabel(""); s.cmdl.setStyleSheet("color:#888;font-size:11px;"); r2b.addWidget(s.cmdl); r2b.addStretch(1); lo.addLayout(r2b)
        # 动态提示：根据是否填写了自定义内容，显示不同提示
        s.chint=QLabel(""); s.chint.setStyleSheet("color:#6c5ce7;font-size:11px;font-weight:500;"); lo.addWidget(s.chint)
        s.ul=QLabel("当前使用：0分钟"); s.ul.setStyleSheet("color:#6c5ce7;font-size:13px;font-weight:600;"); lo.addWidget(s.ul)
        s.il=QLabel(""); s.il.setStyleSheet("color:#6c5ce7;font-size:12px;font-weight:600;"); lo.addWidget(s.il); _add_whint(lo)
        s._ld()
        for w in(s.ecb,s.ie,s.pc,s.ivc,s.cmc,s.ce):
            if isinstance(w,QCheckBox): w.stateChanged.connect(s._oc)
            elif isinstance(w,QComboBox): w.currentTextChanged.connect(s._oc)
            else: w.textChanged.connect(s._oc)
        s._b=False; s._oc()
        s._ut=QTimer(s); s._ut.timeout.connect(s._uu); s._ut.start(30000); s._uu()
    def _iv2m(s,t):
        return {"15分钟":15,"30分钟":30,"45分钟":45,"1小时":60,"1.5小时":90,"2小时":120,"3小时":180}.get(t,60)
    def _m2iv(s,m):
        return {15:"15分钟",30:"30分钟",45:"45分钟",60:"1小时",90:"1.5小时",120:"2小时",180:"3小时"}.get(m,"1小时")
    def _ld(s):
        s.ecb.setChecked(bool(s.d.get("enabled",True))); s.ie.setText(s.d.get("icon","⏳")); s.pc.setCurrentText(PCN.get(s.d.get("position","top_right"),"右上角"))
        s.ivc.setCurrentText(s._m2iv(int(s.d.get("interval_minutes",60)))); s.ce.setText(s.d.get("content",""))
        s.cmc.setCurrentText(CMCN.get(s.d.get("content_mode","smart"),"智能模式"))
    def _uu(s):
        if s.im:
            mi=s.im.gcm(); h,m=divmod(mi,60); s.ul.setText(f"当前使用：{h}小时{m}分钟" if h>0 and m>0 else(f"{h}小时" if h>0 else f"{m}分钟")); s.il.setText(gnrt(s.d,mi))
    def _ucmd(s):
        t=s.cmc.currentText()
        if t=="智能模式": s.cmdl.setText("3小时内仅提示时长，3小时以上提醒休息")
        else: s.cmdl.setText("每次都提醒休息")
    def _uchint(s):
        """动态提示：根据是否填写了自定义内容显示不同提示"""
        ct=s.ce.text().strip()
        if ct:
            s.chint.setText("✏️ 将使用自定义内容（内容模式仅在留空时生效）")
            s.chint.setStyleSheet("color:#e17055;font-size:11px;font-weight:600;")
        else:
            mt=s.cmc.currentText()
            if mt=="智能模式":
                s.chint.setText("📋 自动生成：3小时内仅提示时长，3小时以上加提醒休息")
            else:
                s.chint.setText("📋 自动生成：每次都提醒休息")
            s.chint.setStyleSheet("color:#6c5ce7;font-size:11px;font-weight:500;")
    def _oc(s):
        if s._b: return
        s.d["enabled"]=s.ecb.isChecked(); s.d["icon"]=s.ie.text().strip() or "⏳"; s.d["position"]=PEN.get(s.pc.currentText(),"top_right")
        s.d["interval_minutes"]=s._iv2m(s.ivc.currentText()); s.d["content"]=s.ce.text().strip()
        s.d["content_mode"]=CMEN.get(s.cmc.currentText(),"smart"); s._ucmd(); s._uchint(); s._uu()
    def gd(s):
        return s.d


class ToRC(QWidget):
    dr=Signal(str)
    def __init__(s,d,p=None):
        super().__init__(p); s.d=d; s._b=True; s.setStyleSheet(CS); s.setObjectName("card")
        sh=QGraphicsDropShadowEffect(s); sh.setBlurRadius(20); sh.setOffset(0,6); sh.setColor(QColor(0,0,0,45)); s.setGraphicsEffect(sh)
        lo=QVBoxLayout(s); lo.setContentsMargins(14,10,14,10); lo.setSpacing(6)
        r1=QHBoxLayout(); s.ecb=QCheckBox("启用"); s.ie=QLineEdit(); s.ie.setPlaceholderText("图标"); s.ie.setMaximumWidth(50); s.ce=QLineEdit(); s.ce.setMinimumWidth(140)
        s.adc=QCheckBox("提醒后删除"); s.adc.setStyleSheet("QCheckBox{color:#c0392b;font-size:12px;}")
        db=QPushButton("🗑"); db.setFixedSize(28,28); db.setStyleSheet("QPushButton{background:rgba(231,76,60,180);color:white;border:none;border-radius:8px;font-size:13px;}QPushButton:hover{background:rgba(231,76,60,230);}")
        db.clicked.connect(lambda:s.dr.emit(s.d.get("id","")))
        r1.addWidget(s.ecb); r1.addWidget(QLabel("图标")); r1.addWidget(s.ie); r1.addWidget(QLabel("内容")); r1.addWidget(s.ce,1); r1.addWidget(s.adc); r1.addWidget(db); lo.addLayout(r1)
        r2=QHBoxLayout(); s.te=QTimeEdit(); s.te.setDisplayFormat("HH:mm"); s.de=QDateEdit(); s.de.setCalendarPopup(True); s.de.setDisplayFormat("yyyy-MM-dd"); s.pc=QComboBox(); s.pc.addItems(list(PEN.keys()))
        r2.addWidget(QLabel("时间")); r2.addWidget(s.te); r2.addWidget(QLabel("日期")); r2.addWidget(s.de); r2.addWidget(QLabel("位置")); r2.addWidget(s.pc); r2.addStretch(1); lo.addLayout(r2)
        s.il=QLabel(""); s.il.setStyleSheet("color:#6c5ce7;font-size:12px;font-weight:600;"); lo.addWidget(s.il); _add_whint(lo)
        s._ld()
        for w in(s.ecb,s.ie,s.ce,s.te,s.de,s.pc,s.adc):
            if isinstance(w,QCheckBox): w.stateChanged.connect(s._oc)
            elif isinstance(w,QTimeEdit): w.timeChanged.connect(s._oc)
            elif isinstance(w,QDateEdit): w.dateChanged.connect(s._oc)
            elif isinstance(w,QComboBox): w.currentTextChanged.connect(s._oc)
            else: w.textChanged.connect(s._oc)
        s._b=False; s._oc()
    def _ld(s):
        s.ecb.setChecked(bool(s.d.get("enabled",True))); s.ie.setText(s.d.get("icon","⏰")); s.ce.setText(s.d.get("content",""))
        t=s.d.get("time",""); qt=QTime.fromString(t,"HH:mm"); s.te.setTime(qt if qt.isValid() else QTime(12,0))
        ds=s.d.get("date","")
        if ds:
            try:
                pd=dt.date.fromisoformat(ds); s.de.setDate(QDate(pd.year,pd.month,pd.day))
            except: s.de.setDate(QDate.currentDate())
        else: s.de.setDate(QDate.currentDate())
        s.pc.setCurrentText(PCN.get(s.d.get("position","top_right"),"右上角")); s.adc.setChecked(bool(s.d.get("auto_delete",True)))
    def _oc(s):
        if s._b: return
        s.d["enabled"]=s.ecb.isChecked(); s.d["icon"]=s.ie.text().strip() or "⏰"; s.d["content"]=s.ce.text().strip(); s.d["time"]=s.te.time().toString("HH:mm")
        s.d["date"]=s.de.date().toString("yyyy-MM-dd"); s.d["position"]=PEN.get(s.pc.currentText(),"top_right"); s.d["auto_delete"]=s.adc.isChecked(); s.d["repeat"]="once"
        s.il.setText(gnrt(s.d))
    def gd(s):
        return s.d

class RSD(DD):
    def __init__(s,c,sc_,p=None):
        super().__init__(p); s.c=c; s.sc_=sc_; s.setWindowTitle("提醒设置"); s.resize(980,720)
        s._backup=copy.deepcopy(s.c.get("reminders",[]))
        s._bu(); s._lat()
    def _bu(s):
        s.setStyleSheet("QDialog{background:rgba(240,244,248,250);}QLabel{color:#263238;}QPushButton{background:rgba(255,255,255,220);border:1px solid rgba(0,0,0,18);border-radius:14px;padding:8px 14px;color:#22313f;font-weight:600;}QPushButton:hover{background:rgba(226,231,255,240);}QTabWidget::pane{border:1px solid rgba(0,0,0,30);border-radius:12px;background:rgba(240,244,248,250);top:-1px;}QTabBar::tab{background:rgba(255,255,255,180);border:1px solid rgba(0,0,0,18);border-bottom:none;border-radius:10px 10px 0 0;padding:8px 16px;color:#263238;font-weight:600;margin-right:2px;}QTabBar::tab:selected{background:rgba(240,244,248,250);color:#6c5ce7;}QTabBar::tab:hover{background:rgba(226,231,255,240);}QScrollArea{background:transparent;border:none;}")
        sh=QGraphicsDropShadowEffect(s); sh.setBlurRadius(30); sh.setOffset(0,10); sh.setColor(QColor(0,0,0,70)); s.setGraphicsEffect(sh)
        root=QVBoxLayout(s); root.setContentsMargins(16,16,16,16); root.setSpacing(12)
        top=QHBoxLayout(); t=QLabel("提醒设置"); t.setStyleSheet("font-size:24px;font-weight:800;color:#243447;"); top.addWidget(t); top.addStretch(1); h=QLabel("按类别管理提醒"); h.setStyleSheet("color:#607080;"); top.addWidget(h); root.addLayout(top)
        s.tw=QTabWidget(); s.tls={}
        for rt,lb in TABS:
            sa=QScrollArea(); sa.setWidgetResizable(True); cw=QWidget(); cw.setStyleSheet("background:transparent;"); vl=QVBoxLayout(cw); vl.setSpacing(12); vl.addStretch(1); sa.setWidget(cw); s.tw.addTab(sa,lb); s.tls[rt]=vl
        root.addWidget(s.tw,1)
        bs=QHBoxLayout(); ab=QPushButton("新增提醒"); sv=QPushButton("保存"); cn=QPushButton("取消"); cl=QPushButton("关闭")
        sv.setStyleSheet("background:#6c5ce7;color:white;border:none;padding:9px 18px;")
        cn.setStyleSheet("background:rgba(255,255,255,220);color:#263238;border:1px solid rgba(0,0,0,18);padding:9px 18px;border-radius:14px;")
        ab.clicked.connect(s._ar); sv.clicked.connect(s._sc); cn.clicked.connect(s._cancel); cl.clicked.connect(s._close)
        bs.addWidget(ab); bs.addStretch(1); bs.addWidget(cn); bs.addWidget(sv); bs.addWidget(cl); root.addLayout(bs)
    def _ctt(s):
        i=s.tw.currentIndex()
        if 0<=i<len(TABS): return TABS[i][0]
        return "timed"
    def _stt(s,rt):
        for i,(r,_) in enumerate(TABS):
            if r==rt: s.tw.setCurrentIndex(i); break
    def _lat(s):
        for rt in s.tls:
            lo=s.tls[rt]
            while lo.count()>1:
                it=lo.takeAt(0)
                if it.widget(): it.widget().deleteLater()
        gd:Dict[str,List[dict]]={}
        for r in s.c.get("reminders",[]):
            rt=r.get("type","timed"); gd.setdefault(rt,[]).append(r)
        im=getattr(s.parent(),"_im",None) if s.parent() else None
        for rt in s.tls:
            rems=gd.get(rt,[]); lo=s.tls[rt]
            for r in rems:
                if rt=="welcome": w=WRC(r)
                elif rt in("timed","normal"): w=TRC(r)
                elif rt=="lights_out": w=LRC(r)
                elif rt=="work": w=WoRC(r,im)
                elif rt=="todo": w=ToRC(r)
                else: w=TRC(r)
                if hasattr(w,"dr"): w.dr.connect(s._dl)
                lo.insertWidget(lo.count()-1,w)
    @Slot()
    def _ar(s):
        rt=s._ctt()
        n={"id":f"c_{int(time.time()*1000)}","type":rt,"content":"新提醒","time":"12:00","date":dt.date.today().isoformat(),"repeat":"daily","position":"top_right","icon":"🔔","enabled":True,"weekdays":[],"auto_delete":rt=="todo"}
        if rt=="work": n["interval_minutes"]=60; n["content_mode"]="smart"
        s.c["reminders"].append(n); s._lat(); s._stt(rt)
    @Slot(str)
    def _dl(s,rid):
        s.c["reminders"]=[r for r in s.c.get("reminders",[]) if r.get("id")!=rid]; s._lat()
    def _sc(s):
        nr=[]
        for rt in s.tls:
            lo=s.tls[rt]
            for i in range(lo.count()):
                it=lo.itemAt(i)
                if it and it.widget() and hasattr(it.widget(),"gd"): nr.append(copy.deepcopy(it.widget().gd()))
        s.c["reminders"]=nr; s.sc_(); s._backup=copy.deepcopy(nr); sim(s,"提示","提醒设置已保存"); s._lat()
    def _cancel(s):
        s.c["reminders"]=s._backup; s.sc_(); super().reject()
    def _close(s):
        s.c["reminders"]=s._backup; s.sc_(); super().accept()
    def resizeEvent(s,e):
        super().resizeEvent(e); arm(s,20)

class MSW(QWidget):
    def __init__(s,c,sc_,p=None):
        super().__init__(p); s.c=c; s.sc_=sc_; s.setObjectName("ms"); s._bu()
    def _bu(s):
        s.setStyleSheet("QWidget#ms{background:rgba(240,244,248,250);border-radius:24px;}QLabel{color:#263238;font-size:15px;}QCheckBox{color:#263238;font-size:15px;}QCheckBox::indicator{width:20px;height:20px;border-radius:6px;border:2px solid #aaa;}QCheckBox::indicator:checked{background:#6c5ce7;border-color:#6c5ce7;}QSpinBox{background:rgba(255,255,255,230);border:1px solid rgba(0,0,0,18);border-radius:10px;padding:6px 8px;min-width:80px;color:#263238;}QPushButton{background:rgba(255,255,255,230);border:1px solid rgba(0,0,0,18);border-radius:14px;padding:9px 18px;font-weight:600;color:#263238;}QPushButton:hover{background:rgba(226,231,255,240);}")
        sh=QGraphicsDropShadowEffect(s); sh.setBlurRadius(25); sh.setOffset(0,8); sh.setColor(QColor(0,0,0,65)); s.setGraphicsEffect(sh)
        lo=QVBoxLayout(s); lo.setContentsMargins(28,28,28,28); lo.setSpacing(18)
        r1=QHBoxLayout(); s.asc=QCheckBox("开机自动启动"); s.asc.setChecked(bool(s.c.get("general",{}).get("auto_start",False))); r1.addWidget(s.asc); r1.addStretch(1); lo.addLayout(r1)
        r2=QHBoxLayout(); r2.addWidget(QLabel("连续未使用时长阈值（小时）：")); s.ss=QSpinBox(); s.ss.setRange(1,24); s.ss.setValue(int(s.c.get("general",{}).get("auto_shutdown_hours",3))); r2.addWidget(s.ss); r2.addStretch(1); lo.addLayout(r2)
        r3=QHBoxLayout(); r3.addWidget(QLabel("提醒自动关闭时间（秒）：")); s.acs=QSpinBox(); s.acs.setRange(1,300); s.acs.setValue(int(s.c.get("general",{}).get("reminder_auto_close_seconds",5))); r3.addWidget(s.acs); r3.addStretch(1); lo.addLayout(r3)
        r4=QHBoxLayout()
        ob=QPushButton("📁 打开配置文件位置"); ob.clicked.connect(s._ocd)
        rb=QPushButton("🔄 重置全部配置"); rb.setStyleSheet("background:rgba(231,76,60,200);color:white;border:none;"); rb.clicked.connect(s._rc)
        r4.addWidget(ob); r4.addWidget(rb); r4.addStretch(1); lo.addLayout(r4)
        lo.addStretch(1)
    def _ocd(s):
        ecd(); path=str(CONFIG_DIR)
        try: os.startfile(path)
        except:
            try: os.system(f'explorer "{path}"')
            except: sim(s,"提示",f"配置目录：{path}")
    def _rc(s):
        m=QMessageBox(s); m.setWindowTitle("重置确认"); m.setText("是否确定重置所有配置？这会导致您创建的提醒丢失！"); m.setIcon(QMessageBox.Warning)
        m.setStandardButtons(QMessageBox.Yes|QMessageBox.No); m.setDefaultButton(QMessageBox.No)
        m.setStyleSheet("QMessageBox{background:#f0f4f8;}QMessageBox QLabel{color:#263238;font-size:14px;}QMessageBox QPushButton{background:#6c5ce7;color:white;border:none;border-radius:10px;padding:8px 20px;font-weight:600;min-width:60px;}")
        if m.exec()==QMessageBox.Yes:
            nc=cdc(); s.c.clear(); s.c.update(nc); s.sc_()
            sim(s,"提示","配置已重置为默认值")
    def _aas(s,en):
        try:
            import winreg; ky=winreg.HKEY_CURRENT_USER; sub=r"Software\Microsoft\Windows\CurrentVersion\Run"
            ap=sys.executable; sp=os.path.abspath(sys.argv[0]); cmd='"'+ap+'" "'+sp+'"'
            with winreg.OpenKey(ky,sub,0,winreg.KEY_SET_VALUE) as reg:
                if en: winreg.SetValueEx(reg,APP_NAME,0,winreg.REG_SZ,cmd)
                else:
                    try: winreg.DeleteValue(reg,APP_NAME)
                    except FileNotFoundError: pass
        except Exception as e:
            sim(s,"错误",f"无法修改注册表：{e}")
    def atc(s):
        s.c.setdefault("general",{})["auto_start"]=s.asc.isChecked(); s.c["general"]["auto_shutdown_hours"]=int(s.ss.value()); s.c["general"]["reminder_auto_close_seconds"]=int(s.acs.value()); s._aas(s.asc.isChecked())
    def so(s):
        s.atc(); s.sc_(); sim(s,"提示","设置已保存")
    def ok(s):
        s.atc(); s.sc_(); s.window().close()
    def cancel(s):
        s.window().close()

class AD(DD):
    def __init__(s,p=None):
        super().__init__(p); s.setWindowTitle("关于"); s.setFixedSize(420,280)
        s.setStyleSheet("QDialog{background:rgba(240,244,248,250);}QLabel{color:#243447;}QPushButton{background:#6c5ce7;color:white;border:none;border-radius:14px;padding:10px 18px;font-weight:700;}QPushButton:hover{background:#594bd2;}")
        sh=QGraphicsDropShadowEffect(s); sh.setBlurRadius(25); sh.setOffset(0,8); sh.setColor(QColor(0,0,0,55)); s.setGraphicsEffect(sh)
        lo=QVBoxLayout(s); lo.setContentsMargins(28,28,28,28); lo.setSpacing(12)
        t=QLabel(APP_NAME); t.setAlignment(Qt.AlignCenter); t.setStyleSheet("font-size:28px;font-weight:800;"); lo.addWidget(t)
        v=QLabel(f"版本 {APP_VERSION} 由AI构建"); v.setAlignment(Qt.AlignCenter); v.setStyleSheet("color:#52616b;"); lo.addWidget(v)
        d=QLabel("一款简易的软件用来提醒您在使用设备时注意休息，可以设置待办日常提醒。"); d.setWordWrap(True); d.setAlignment(Qt.AlignCenter); d.setStyleSheet("color:#52616b;"); lo.addWidget(d)
        lo.addStretch(1)
        cb=QPushButton("关闭"); cb.clicked.connect(s.close); lo.addWidget(cb,alignment=Qt.AlignCenter)
    def resizeEvent(s,e):
        super().resizeEvent(e); arm(s,26)
    def showEvent(s,e):
        super().showEvent(e); arm(s,26)

class MW(QMainWindow):
    def __init__(s,c,sc_):
        super().__init__(); s.c=c; s.sc_=sc_; s.dp=None; s.bl=CB(s); s.bl.lower(); s._bu(); s._lb(); s.up(); s._spt()
    def _bu(s):
        s.setWindowTitle(APP_NAME); s.setMinimumSize(920,640); s.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint); s.setAttribute(Qt.WA_TranslucentBackground,True)
        cw=QWidget(); cw.setObjectName("cp"); cw.setStyleSheet("QWidget#cp{background:rgba(255,255,255,178);border-radius:32px;}QLabel{color:#263238;}QPushButton{background:rgba(255,255,255,200);border:1px solid rgba(0,0,0,14);border-bottom:3px solid rgba(0,0,0,16);border-radius:22px;color:#1f2d3d;font-weight:700;}QPushButton:hover{background:rgba(232,236,255,245);}QPushButton:pressed{background:rgba(215,220,255,245);}")
        sh=QGraphicsDropShadowEffect(cw); sh.setBlurRadius(36); sh.setOffset(0,12); sh.setColor(QColor(0,0,0,68)); cw.setGraphicsEffect(sh); s.setCentralWidget(cw)
        rt=QVBoxLayout(cw); rt.setContentsMargins(22,16,22,18); rt.setSpacing(12)
        tb=QHBoxLayout(); tb.addStretch(1)
        mb=QPushButton("—"); mb.setFixedSize(38,38); mb.setStyleSheet("background:transparent;border:none;font-size:22px;color:#22313f;"); mb.clicked.connect(s.showMinimized)
        cb=QPushButton("✕"); cb.setFixedSize(38,38); cb.setStyleSheet("background:transparent;border:none;font-size:22px;color:#22313f;"); cb.clicked.connect(s.hide)
        tb.addWidget(mb); tb.addWidget(cb); rt.addLayout(tb)
        t=QLabel(APP_NAME); t.setAlignment(Qt.AlignCenter); t.setStyleSheet("font-size:34px;font-weight:900;letter-spacing:1px;color:#263238;"); rt.addWidget(t)
        s.sl=QLabel(); s.sl.setAlignment(Qt.AlignCenter); s.sl.setWordWrap(True); s.sl.setStyleSheet("font-size:18px;color:#52616b;padding:6px 18px;"); rt.addWidget(s.sl)
        g=QGridLayout(); g.setHorizontalSpacing(18); g.setVerticalSpacing(18); s.mb=None
        bts=[("📨","添加待办",s.oat,"rgba(255,255,255,210)"),("🛎️","禁用提醒",s.otm,"rgba(255,236,208,230)"),("📝","提醒设置",s.ors,"rgba(225,241,255,230)"),("🛠️","更多设置",s.oms,"rgba(235,226,255,230)"),("🎗️","关于",s.oa,"rgba(226,255,241,230)")]
        for i,(em,tx,hd,bg) in enumerate(bts):
            b=QPushButton(f"{em}\n{tx}"); b.setFixedSize(160,120)
            b.setStyleSheet(f"QPushButton{{background:{bg};border-radius:22px;border:1px solid rgba(255,255,255,180);font-size:28px;color:#22313f;}}QPushButton:hover{{background:rgba(0,0,0,28);color:white;}}")
            b.clicked.connect(hd)
            if tx in("禁用提醒","启用提醒"): s.mb=b
            g.addWidget(b,i//3,i%3,alignment=Qt.AlignCenter)
        rt.addLayout(g); rt.addStretch(1)
        bm=QHBoxLayout(); bm.addStretch(1); eb=QPushButton("退出程序")
        eb.setStyleSheet("background:rgba(231,76,60,220);color:white;border:none;border-radius:16px;padding:10px 18px;font-size:15px;font-weight:700;"); eb.clicked.connect(s.ea); bm.addWidget(eb); rt.addLayout(bm); s.umb()
    def resizeEvent(s,e):
        super().resizeEvent(e); s.bl.setGeometry(s.rect()); arm(s,32)
    def showEvent(s,e):
        super().showEvent(e); s.bl.setGeometry(s.rect()); arm(s,32)
    def _lb(s):
        pm=None; bi=gbi()
        if bi and os.path.isfile(bi): pm=QPixmap(bi)
        else:
            wp=gsw()
            if wp and os.path.isfile(wp) and wp.lower().endswith((".png",".jpg",".jpeg",".bmp",".webp")): pm=QPixmap(wp)
        if pm and not pm.isNull(): s.bl.sbp(pm)
        else: s.bl.sbc(gsac())
    def _spt(s):
        s.pt=QTimer(s); s.pt.timeout.connect(s.up); s.pt.start(600000)
    def up(s):
        ps=s.c.get("phrases",DP); ph=random.choice(ps) if ps else "欢迎使用Fhy健康助手Lite"; s.sl.setText(f"{gcu()}，{ph}")
    def oat(s):
        d=DD(s); d.setWindowTitle("快速添加待办"); d.setFixedSize(480,580)
        d.setStyleSheet("QDialog{background:rgba(240,244,248,250);}QLabel{color:#263238;font-size:14px;}QLineEdit,QComboBox,QTimeEdit,QDateEdit{background:rgba(255,255,255,235);border:1px solid rgba(0,0,0,18);border-radius:10px;padding:7px 10px;color:#1f2d3d;min-height:26px;}QComboBox::drop-down{border:none;}QComboBox QAbstractItemView{background:white;color:#1f2d3d;selection-background-color:#dcd6f7;border:1px solid #ccc;}QCheckBox{color:#263238;font-size:13px;}QCheckBox::indicator{width:18px;height:18px;border-radius:5px;border:2px solid #aaa;}QCheckBox::indicator:checked{background:#6c5ce7;border-color:#6c5ce7;}QCalendarWidget QWidget{background-color:white;color:#263238;}QCalendarWidget QToolButton{color:#263238;background-color:#f0f4f8;}QCalendarWidget QAbstractItemView{background-color:white;color:#263238;selection-background-color:#dcd6f7;}")
        sh=QGraphicsDropShadowEffect(d); sh.setBlurRadius(25); sh.setOffset(0,8); sh.setColor(QColor(0,0,0,55)); d.setGraphicsEffect(sh)
        lo=QVBoxLayout(d); lo.setContentsMargins(24,24,24,24); lo.setSpacing(14)
        ce=QLineEdit("新待办提醒"); te=QTimeEdit(QTime.currentTime().addSecs(300)); te.setDisplayFormat("HH:mm")
        de=QDateEdit(QDate.currentDate()); de.setCalendarPopup(True); de.setDisplayFormat("yyyy-MM-dd")
        pc=QComboBox(); pc.addItems(list(PEN.keys())); ie=QLineEdit("⏰"); ie.setPlaceholderText("图标"); ie.setMaximumWidth(60)
        adc=QCheckBox("提醒后自动删除"); adc.setChecked(True)
        ob=QPushButton("添加"); ob.setStyleSheet("background:#6c5ce7;color:white;border:none;border-radius:12px;padding:10px;font-weight:700;font-size:15px;")
        cb=QPushButton("取消"); cb.setStyleSheet("background:rgba(255,255,255,230);color:#263238;border:1px solid rgba(0,0,0,18);border-radius:12px;padding:10px;font-weight:600;font-size:15px;")
        lo.addWidget(QLabel("内容：")); lo.addWidget(ce); lo.addWidget(QLabel("时间：")); lo.addWidget(te); lo.addWidget(QLabel("日期：")); lo.addWidget(de)
        ri=QHBoxLayout(); ri.addWidget(QLabel("图标：")); ri.addWidget(ie); ri.addStretch(1); lo.addLayout(ri)
        lo.addWidget(QLabel("位置：")); lo.addWidget(pc); lo.addWidget(adc); lo.addStretch(1)
        br=QHBoxLayout(); br.addWidget(ob); br.addWidget(cb); lo.addLayout(br)
        def add():
            ts=te.time().toString("HH:mm"); ds=de.date().toString("yyyy-MM-dd")
            s.c["reminders"].append({"id":f"q_{int(time.time()*1000)}","type":"todo","content":ce.text().strip() or "新待办提醒","time":ts,"date":ds,"repeat":"once","position":PEN.get(pc.currentText(),"top_right"),"icon":ie.text().strip() or "⏰","enabled":True,"weekdays":[],"auto_delete":adc.isChecked()})
            s.sc_(); d.accept(); sim(s,"提示","待办提醒已添加")
        ob.clicked.connect(add); cb.clicked.connect(d.reject)
        d.resizeEvent=lambda e:(DD.resizeEvent(d,e),arm(d,22)); d.showEvent=lambda e:(DD.showEvent(d,e),arm(d,22)); d.exec()
    def otm(s):
        cur=bool(s.c.get("general",{}).get("master_switch",True)); s.c.setdefault("general",{})["master_switch"]=not cur; s.sc_(); s.umb()
    def umb(s):
        if s.mb:
            en=bool(s.c.get("general",{}).get("master_switch",True)); s.mb.setText("🛎️\n禁用提醒" if en else "🛎️\n启用提醒")
    def ors(s):
        RSD(s.c,s.sc_,s).exec()
    def oms(s):
        d=DD(s); d.setWindowTitle("更多设置"); d.setFixedSize(660,480)
        d.setStyleSheet("QDialog{background:rgba(240,244,248,250);}")
        lo=QVBoxLayout(d); lo.setContentsMargins(12,12,12,12)
        p=MSW(s.c,s.sc_,d); lo.addWidget(p,1)
        br=QHBoxLayout(); cb=QPushButton("取消"); sv=QPushButton("保存"); ok=QPushButton("确定")
        sv.setStyleSheet("background:#6c5ce7;color:white;border:none;padding:9px 16px;border-radius:12px;font-weight:600;")
        ok.setStyleSheet("background:#4b7bec;color:white;border:none;padding:9px 16px;border-radius:12px;font-weight:600;")
        cb.setStyleSheet("background:rgba(255,255,255,230);color:#263238;border:1px solid rgba(0,0,0,18);padding:9px 16px;border-radius:12px;font-weight:600;")
        cb.clicked.connect(p.cancel); sv.clicked.connect(p.so); ok.clicked.connect(p.ok)
        br.addStretch(1); br.addWidget(cb); br.addWidget(sv); br.addWidget(ok); lo.addLayout(br)
        d.resizeEvent=lambda e:(DD.resizeEvent(d,e),arm(d,20)); d.showEvent=lambda e:(DD.showEvent(d,e),arm(d,20)); d.exec()
    def oa(s):
        AD(s).exec()
    def ea(s):
        QApplication.quit()
    def mousePressEvent(s,e):
        if e.button()==Qt.LeftButton: s.dp=e.globalPosition().toPoint()-s.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(s,e):
        if s.dp is not None and e.buttons()&Qt.LeftButton: s.move(e.globalPosition().toPoint()-s.dp); e.accept()
    def mouseReleaseEvent(s,e):
        s.dp=None

class TM(QObject):
    def __init__(s,app,mw):
        super().__init__(); s.app=app; s.mw=mw; s.tr=QSystemTrayIcon(s._ci(),s); s.tr.setToolTip(APP_NAME)
        m=QMenu(); m.addAction("显示主界面",s.sm); m.addSeparator(); m.addAction("退出",s.qa); s.tr.setContextMenu(m); s.tr.activated.connect(s._oa); s.tr.show()
    def _oa(s,r):
        if r==QSystemTrayIcon.DoubleClick: s.sm()
    def sm(s):
        s.mw.show(); s.mw.raise_(); s.mw.activateWindow()
    def qa(s):
        s.app.quit()
    def _ci(s):
        pm=QPixmap(64,64); pm.fill(Qt.transparent); p=QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        pa=QPainterPath(); pa.addRoundedRect(4,4,56,56,16,16); g=QLinearGradient(0,0,0,64); g.setColorAt(0,QColor("#9b8cff")); g.setColorAt(1,QColor("#6c5ce7"))
        p.setBrush(QBrush(g)); p.setPen(QPen(QColor(255,255,255,80),1.5)); p.drawPath(pa); p.setPen(QColor("white")); p.setFont(QFont("Microsoft YaHei",20,QFont.Bold)); p.drawText(pm.rect(),Qt.AlignCenter,"Fh"); p.end(); return QIcon(pm)

class SM(QObject):
    pad=Signal(str)
    def __init__(s,c,im,pm,sc_):
        super().__init__(); s.c=c; s.im=im; s.pm=pm; s.sc_=sc_; s.ths=[]; s.wks=[]
        s.pad.connect(s._had,Qt.QueuedConnection); s._sw()
    def _aw(s,w,sn):
        t=QThread(s); w.moveToThread(t); t.started.connect(getattr(w,sn))
        if hasattr(w,"tg"): w.tg.connect(s.pm.push,Qt.QueuedConnection)
        if hasattr(w,"pad"): w.pad.connect(s.pad,Qt.QueuedConnection)
        t.start(); s.ths.append(t); s.wks.append(w)
    def _sw(s):
        s.tw_=TRW(s.c); s.ww_=WRW(s.c,s.im); s._aw(s.tw_,"start"); s._aw(s.ww_,"start")
    @Slot(str)
    def _had(s,rid):
        s.c["reminders"]=[r for r in s.c.get("reminders",[]) if r.get("id")!=rid]; s.sc_()

def bas(app):
    app.setStyle("Fusion"); pal=app.palette()
    pal.setColor(QPalette.Window,QColor(245,247,250)); pal.setColor(QPalette.Base,QColor(255,255,255))
    pal.setColor(QPalette.Text,QColor(30,40,50)); pal.setColor(QPalette.WindowText,QColor(30,40,50)); pal.setColor(QPalette.ButtonText,QColor(30,40,50)); app.setPalette(pal)

def main()->int:
    app=QApplication(sys.argv); app.setQuitOnLastWindowClosed(False); bas(app)
    c=lc()
    def scb(): sc(c)
    im=IM(); pm=RPM(); mw=MW(c,scb); mw._im=im; tr=TM(app,mw); sm_=SM(c,im,pm,scb); _=(tr,sm_,pm)
    if CONFIG_FILE.exists(): mw.hide()
    else: mw.show()
    ec=app.exec(); im.stop(); return ec

if __name__=="__main__":
    raise SystemExit(main())
