"""Unexpected Python/Qt failures recorded independently of operator log clearing."""
import faulthandler,logging,platform,sys,threading,traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

def install(folder):
    from PySide6.QtCore import qInstallMessageHandler,QtMsgType,qVersion
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('nexatom.errors');logger.setLevel(logging.WARNING);logger.propagate=False
    if logger.handlers:return
    handler=RotatingFileHandler(folder/'errors.txt',maxBytes=2_000_000,backupCount=3,encoding='utf8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));logger.addHandler(handler)
    logger.warning('Session started | Python %s | Qt %s | OS %s | build interface',sys.version.split()[0],qVersion(),platform.platform())
    def exception(kind,value,tb):logger.critical('Unhandled Python exception',exc_info=(kind,value,tb))
    sys.excepthook=exception
    threading.excepthook=lambda args:exception(args.exc_type,args.exc_value,args.exc_traceback)
    previous=None
    def qt(kind,context,message):
        if kind in (QtMsgType.QtWarningMsg,QtMsgType.QtCriticalMsg,QtMsgType.QtFatalMsg):
            logger.log(logging.WARNING if kind==QtMsgType.QtWarningMsg else logging.ERROR,'Qt %s:%s %s',context.file or '',context.line,message)
        if previous:previous(kind,context,message)
    previous=qInstallMessageHandler(qt)
    fatalpath=folder/'fatal.txt'
    if fatalpath.exists() and fatalpath.stat().st_size>2_000_000:fatalpath.replace(folder/'fatal.previous.txt')
    fatal=fatalpath.open('a',encoding='utf8');faulthandler.enable(fatal,all_threads=True)
    # Keep the descriptor and handler alive throughout the process.
    install.references=(fatal,qt,previous)
    root=logging.getLogger('nexatom');errors=RotatingFileHandler(folder/'bugs.txt',maxBytes=2_000_000,backupCount=3,encoding='utf8')
    errors.setLevel(logging.ERROR);errors.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'));root.addHandler(errors)
