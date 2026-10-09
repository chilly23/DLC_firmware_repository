"""Physical-switch UI lock. Input blocking and power timeout have one owner."""
import math,time
from PySide6.QtCore import QObject,Signal,Property,QTimer,QEvent,Qt,QRectF
from PySide6.QtGui import QPainter,QColor,QFont,QPen,QPixmap,QImage
from PySide6.QtWidgets import QWidget,QGraphicsScene,QGraphicsPixmapItem,QGraphicsBlurEffect

class LockWindow(QWidget):
    def __init__(self,guard):
        super().__init__();self.guard=guard;self.background=QPixmap()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
    def capture(self,source):
        pix=source.grab() if isinstance(source,QWidget) else source.grabWindow()
        if isinstance(pix,QImage):pix=QPixmap.fromImage(pix)
        if pix.isNull():self.background=pix;return
        scene=QGraphicsScene();item=QGraphicsPixmapItem(pix);effect=QGraphicsBlurEffect();effect.setBlurRadius(22)
        item.setGraphicsEffect(effect);scene.addItem(item);scene.setSceneRect(QRectF(pix.rect()))
        img=QImage(pix.size(),QImage.Format.Format_ARGB32_Premultiplied);img.fill(Qt.GlobalColor.black)
        p=QPainter(img);scene.render(p);p.end();self.background=QPixmap.fromImage(img)
    def closeEvent(self,event):
        if self.guard.locked:event.ignore()
        else:event.accept()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor('#111111'))
        if not self.background.isNull():p.drawPixmap(self.rect(),self.background)
        p.fillRect(self.rect(),QColor(0,0,0,190))
        s=min(self.width()/1600,self.height()/720);p.translate((self.width()-1600*s)/2,(self.height()-720*s)/2);p.scale(s,s)
        p.setPen(QPen(QColor('#D9D9D9'),7));p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(731,225,138,115),15,15);p.drawArc(QRectF(753,143,94,133),0,180*16)
        p.drawLine(800,268,800,301)
        for text,y,size,color in [('System locked',376,40,'#FFFFFF'),(self.guard.caption,445,22,'#D9D9D9'),('Unlock the physical switch to continue',494,18,'#AEB8AC')]:
            f=QFont(self.guard.ctl.theme.fontFamily);f.setPixelSize(size);p.setFont(f);p.setPen(QColor(color));p.drawText(QRectF(300,y,1000,55),Qt.AlignmentFlag.AlignCenter,text)
        p.end()

class SessionLock(QObject):
    changed=Signal()
    def __init__(self,app,ctl,parent=None):
        super().__init__(parent or app);self.app=app;self.ctl=ctl;self._locked=False;self.deadline=0;self.sent=False;self.error='';self.window=None;self.epoch=0;self.tour_was_playing=False
        self.timer=QTimer(self);self.timer.setInterval(100);self.timer.timeout.connect(self.tick);self.timer.start();app.installEventFilter(self)
    @Property(bool,notify=changed)
    def locked(self):return self._locked
    @property
    def caption(self):
        return self.error or ('Shutting down...' if self.sent else f'Automatic shutdown in {max(0,math.ceil(self.deadline-time.monotonic()))} seconds')
    def set_locked(self,value):
        if bool(value)==self._locked:return
        self._locked=bool(value);self.sent=False;self.error='';self.epoch+=1
        if value:
            self.deadline=time.monotonic()+int(self.ctl.theme.get('lock_shutdown_seconds'))
            self.ctl.system_settings.cancel_power();self.tour_was_playing=self.ctl.system_settings._tour_play;self.ctl.system_settings._tour_play=False
            self.ctl.knobs.suspended=True;self.ctl.knobs.held.clear();self.ctl.knobs.pushes.clear();self.ctl.navigation.clear_focus()
            self.ctl.knobs.panel_calibration=None
            if self.ctl.knobs.calibration:self.ctl.knobs.cancel_calibration()
            host=self.ctl.settings_host;source=host.window if host.window.isVisible() else host.home
            host.home.cancelInputForLock()
            native=host.window;native.pending=None;native.content_pressed=False;native.slider_action=None;native.slider_held=False;native.display_preview.clear();native.backspace_hold.stop();native.tip_timer.stop()
            self.window=self.window or LockWindow(self);self.window.capture(source);self.window.setGeometry(source.geometry());self.window.show();self.window.raise_();self.window.activateWindow()
            self.ctl.notifications.post('System locked by physical switch','warning','system-lock')
        else:
            self.deadline=0;self.ctl.knobs.suspended=False;self.ctl.knobs.armed.clear();self.ctl.knobs.quiet_since.clear()
            if self.window:self.window.hide()
            self.ctl.system_settings.idle_since=time.monotonic();self.ctl.notifications.post('System unlocked','normal','system-lock')
            self.ctl.system_settings._tour_play=self.tour_was_playing;self.ctl.system_settings.tour_deadline=time.monotonic()+9
        self.changed.emit()
    def tick(self):
        if not self.locked:return
        if self.window:self.window.update()
        if not self.sent and self.deadline and time.monotonic()>=self.deadline:
            self.sent=True;epoch=self.epoch;self.ctl.system_settings.submit(lambda:self.power_if_still_locked(epoch),self.power_result)
    def power_if_still_locked(self,epoch):
        # Recheck after any queued display work, immediately before issuing poweroff.
        if self.locked and self.sent and epoch==self.epoch:return self.ctl.system_settings.device.power('shutdown')
    def power_result(self,value,error):
        if error:self.error='Shutdown failed: '+error;self.ctl.notifications.post(self.error,'critical','shutdown')
        self.changed.emit()
    def eventFilter(self,obj,event):
        return self.locked and event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseButtonRelease,QEvent.Type.MouseButtonDblClick,QEvent.Type.MouseMove,QEvent.Type.Wheel,QEvent.Type.TouchBegin,QEvent.Type.TouchUpdate,QEvent.Type.TouchEnd,QEvent.Type.KeyPress,QEvent.Type.KeyRelease,QEvent.Type.Shortcut,QEvent.Type.ShortcutOverride,QEvent.Type.InputMethod)
    def shutdown(self):
        self.timer.stop();self.app.removeEventFilter(self);self._locked=False
        if self.window:self.window.close()
