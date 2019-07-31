import json
from _queue import Empty
from collections import defaultdict
from json import JSONDecodeError

from PyQt5 import  QtWidgets, QtGui, uic
from PyQt5.QtCore import QThread, pyqtSignal, QMutex
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox, QListWidgetItem

from AsynchronousFileReader import AsynchronousFileReader
import subprocess
import time
from multiprocessing import Process, Queue
Ui_MainWindow, QtBaseClass = uic.loadUiType("gui.ui")


class RunTasks(QThread):
    stderr = pyqtSignal(str)
    stdout = pyqtSignal(str)
    notify = pyqtSignal(list)
    finished = pyqtSignal()
    def __init__(self,commandQ):
        super(RunTasks,self).__init__()
        self.commandQ = commandQ
    def run(self):
        while True:
            print("RUN")
            cQ = self.commandQ.get()
            command = cQ[0]
            printstd = cQ[1]
            print (printstd)
            cmd=command.split(' ')
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.stdout
            stdout_queue = Queue()
            stderr_queue = Queue()
            stdout_reader = AsynchronousFileReader(process.stdout, stdout_queue)
            stdout_reader.start()
            stderr_reader = AsynchronousFileReader(process.stderr, stderr_queue)
            stderr_reader.start()
            stdout = ""
            stderr = ""
            while process.poll() is None:
                try:
                    while True:
                        a = stderr_queue.get_nowait()
                        stderr += str(a)
                        if len(a) > 0:
                            if printstd:
                                self.stderr.emit("<b>{}</b>".format(str(a, 'utf-8').replace("\n","<br />")))
                        else:
                            break
                except Empty:
                    a = ""
                try:
                    while True:
                        b = stdout_queue.get_nowait()
                        stdout += str(b)
                        if len(b) > 0:
                            self.stdout.emit(str(b,'utf-8').replace("\n","<br />"))
                        else:
                            break
                except Empty:
                    b = ""
                #if len(a) == 0 and len(b) == 0:
                #    break
                time.sleep(1)
            print(command, "finished")
            try:
                while True:
                    a = stderr_queue.get_nowait()
                    print(a, 'utf-8')
                    stderr += str(a, 'utf-8')
                    if len(a) > 0:
                        self.stderr.emit("<b>{}</b>".format(str(a, 'utf-8').replace("\n", "<br />")))
                    else: break
            except Empty:
                a = ""
            try:
                while True:
                    b = stdout_queue.get_nowait()
                    stdout += str(b,'utf-8')
                    if len(b) > 0:
                        if printstd:
                            self.stdout.emit(str(b, 'utf-8').replace("\n", "<br />"))
                    else:
                        break
            except Empty:
                b = ""
            self.notify.emit([command,stdout,stderr])


class myApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        #self.resize(600, 400)  # The resize() method resizes the widget.
        self.setWindowTitle("BrewStore")  # Here we set the title for our window.
        self.taskQ = Queue();
        self.tasker = RunTasks(self.taskQ)
        self.tasker.stderr.connect(self.console_writer)
        self.tasker.stdout.connect(self.console_writer)
        self.tasker.notify.connect(self.readNotif)
        self.tasker.start()
        self.on_startup()
        self.apps = defaultdict(list)
        self.appDict = defaultdict(dict)
        self.appListMutex = QMutex()
        self.initToolbar()
        self.viewstate = None
        self.AppList.itemSelectionChanged.connect(self.selectApp)
        self.defaultAppIcon = QIcon("icons/open_icon_library-mac/icons/32x32/mimetypes/package-x-generic-2.icns")
        self.FilterEdit.textChanged.connect(self.filterChange)
        self.InstallButton.clicked.connect(self.install)
        #print(self.toolBar.actionApplications)
        #self.consoleUi_MainWindow.ui.console



    def initToolbar(self):
        self.toolboxMutex = QMutex()
        self.toolBarActions = {}

        self.actionCasks = self.toolBar.addAction(
            QIcon("icons/open_icon_library-mac/icons/32x32/categories/applications-other-4.icns"), "Applications")
        self.actionCasks.setCheckable(True)
        self.actionCasks.triggered.connect(lambda a: self.newSelect(a,self.actionCasks,"Casks"))
        self.toolBarActions["Casks"] = self.actionCasks

        self.actionLibs = self.toolBar.addAction(
            QIcon("icons/open_icon_library-mac/icons/32x32/categories/applications-development-4.icns"), "Libraries")
        self.actionLibs.setCheckable(True)
        self.actionLibs.triggered.connect(lambda a:self.newSelect(a,self.actionLibs,"Libs"))
        self.toolBarActions["Libs"]= self.actionLibs

        self.actionUpdates = self.toolBar.addAction(
            QIcon("icons/open_icon_library-mac/icons/32x32/actions/update_misc.icns"), "Updates")
        self.actionUpdates.setCheckable(True)
        self.actionUpdates.triggered.connect(lambda a: self.newSelect(a, self.actionUpdates, "Updates"))
        self.toolBarActions["Updates"] = self.actionUpdates

    def newSelect(self,value,action,name):
        self.toolboxMutex.lock()
        if value:
            for k,v in self.toolBarActions.items():
                if k != name:
                    v.setChecked(False)
            self.changeCat(name)
        self.toolboxMutex.unlock()

    def install(self):
        if len(self.AppList.selectedItems())==0:
            self.DescriptionArea.setHtml("")
        else:
            item = self.AppList.selectedItems()[0]
            app = item.data(0x0100) #UserRole
            self.runcommand(app["installcommand"])
    def selectApp(self):
        if len(self.AppList.selectedItems())==0:
            self.DescriptionArea.setHtml("")
        else:
            item = self.AppList.selectedItems()[0]
            app = item.data(0x0100) #UserRole
            self.DescriptionArea.setHtml("<h1>{Name}</h1>{Token}<br/>Version: {Version}<h2>Description</h2>{Desc}<br /><a href=\"{Homepage}\">{Homepage}</a>".format(Token=app.get("token",""),Version=app.get("version",""),Name=app.get("name",""),Desc=app.get("desc",""),Homepage=app.get("homepage","")))

    def filterChange(self):
        if self.actionLibs.isChecked():
            self.changeCat("Libs")
        elif self.actionCasks.isChecked():
            self.changeCat("Casks")
        elif self.actionUpdates.isChecked():
            self.changeCat("Updates")

    def filterData(self,filter,data):
        if isinstance(data,list):
            for i in data:
                if self.filterData(filter,i):
                    return True
        elif isinstance(data,str):
            if filter.lower() in data.lower():
                return True
        elif isinstance(data, dict):
            for k,v in data:
                if self.filterData(filter,v):
                    return True
        return False

    def changeCat(self,new,force=False):
        self.appListMutex.lock()
        filter = self.FilterEdit.text()
        if self.viewstate != (new,filter) or force:
            self.AppList.clear()
            self.visiblePrograms = dict()
            for k,v in self.appDict[new].items():
                datalist = [v.get("name",""),v.get("full_name",""),v.get("desc",""),v.get("oldname","")]
                if not self.filterData(filter,datalist):
                    continue

                widget = QListWidgetItem()
                if "name" not in v:
                    widget.setText(v)
                else:
                    if isinstance(v["name"],list):
                        widget.setText(v["name"][0])
                    else:
                        widget.setText(v["name"])

                if "icon" not in v:
                    widget.setIcon(self.defaultAppIcon)
                else:
                    widget.setIcon(QIcon(v["icon"]))
                widget.setData(0x0100,v)#UserRole
                self.AppList.addItem(widget)
            self.viewstate = (new,filter)
        self.appListMutex.unlock()



    def readNotif(self,message):
        print("MESSAGE from {}".format(message[0]))
        if message[0] == "brew cask outdated --greedy":
            if message[1][-1] == "\n": message[1] = message[1][:-1]
            apps = message[1].split("\n")
            for a in apps:
                self.appDict["Updates"][a] = self.appDict["Updates"].get(a, {"token": a, "name": a,"installcommand": "brew cask upgrade {}".format(a)})
            if self.actionUpdates.isChecked():
                self.changeCat("Updates",True)

            programs_to_update=message[1].split('\n')
            reply = QMessageBox.question(self,"Update Software", "Do you want to update {} programs?<br>{}".format(len(programs_to_update),", ".join(programs_to_update)))
            if reply==QMessageBox.Yes:
                self.runcommand("brew cask upgrade --greedy")
                self.runcommand("brew cask outdated --greedy")
            #print(message[1])
            #print("####")
            #print(message[2])
        elif message[0] == "brew search --cask":
            if message[1][-1]=="\n": message[1]=message[1][:-1]
            apps = message[1].split("\n")
            #for a in apps:
            #    self.appDict["Casks"][a] = self.appDict["Casks"].get(a, {"token": a, "name": a})
            self.runcommand("brew cask info --json=v1 {}".format(" ".join(apps)), False)
            if self.actionCasks.isChecked():
                self.changeCat("Casks",True)

        elif message[0] == "brew search":
            if message[1][-1] == "\n": message[1] = message[1][:-1]
            apps = message[1].split("\n")
            for a in apps:
                self.appDict["Libs"][a] = self.appDict["Libs"].get(a, {"token": a, "name": a, "installcommand": "brew install {}".format(a)})
            if self.actionLibs.isChecked():
                self.changeCat("Libs",True)


        elif message[0] == "brew info --json=v1 --all":
            self.appDict["Libs"] = dict()
            try:
                raw = json.loads(message[1])
            except JSONDecodeError:
                print(message[1])
            for p in raw:
                p["token"]=p["name"]
                p["name"]=p["full_name"]
                p["installcommand"]= "brew install {}".format(p["token"])
                self.appDict["Libs"][p["name"]]=p
            if self.actionLibs.isChecked():
                self.changeCat("Libs",True)

        elif message[0].startswith("brew cask info --json=v1 "):
            appnames = message[0][len("brew cask info --json=v1 "):].split(" ")
            try:
                raw = json.loads(message[1])
            except JSONDecodeError:
                print(message[1])
            self.appDict["Casks"] = dict()
            for p in raw:
                if isinstance(p["name"],list):
                    p["all_names"]=p["name"]
                    p["name"]=p["name"][0]
                    p["installcommand"] = "brew cask install {}".format(p["token"])
                self.appDict["Casks"][p["token"]]=p
            if self.actionCasks.isChecked():
                self.changeCat("Casks",True)
    def console_writer(self,text):
        self.console.insertHtml(text)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def runcommand(self,command,printit=True):
        self.taskQ.put((command,printit))
    def on_startup(self):
        self.runcommand("brew search --cask", False)
        #self.runcommand("brew search", False)
        self.runcommand("brew info --json=v1 --all", False)
        self.runcommand("brew update --verbose")
        self.runcommand("brew cask outdated --greedy")
        #self.runcommand("brew search --cask", False)
        #self.runcommand("brew search", False)







