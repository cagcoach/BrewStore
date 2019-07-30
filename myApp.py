from _queue import Empty
from collections import defaultdict

from PyQt5 import  QtWidgets, QtGui, uic
from PyQt5.QtCore import QThread, pyqtSignal, QMutex
from PyQt5.QtWidgets import QMessageBox

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
        self.resize(600, 400)  # The resize() method resizes the widget.
        self.setWindowTitle("BrewStore")  # Here we set the title for our window.
        self.taskQ = Queue();
        self.tasker = RunTasks(self.taskQ)
        self.tasker.stderr.connect(self.console_writer)
        self.tasker.stdout.connect(self.console_writer)
        self.tasker.notify.connect(self.readNotif)
        self.tasker.start()
        self.on_startup()
        self.apps = defaultdict(list)
        self.AppCategories.currentItemChanged.connect(self.changeCat)
        #self.consoleUi_MainWindow.ui.console

    def changeCat(self,item,old):
        if not item is None:
            print(item.text())
            self.AppList.clear()
            self.AppList.addItems(self.apps[item.text()])

    def readNotif(self,message):
        print("MESSAGE from {}".format(message[0]))
        if message[0] == "brew cask outdated --greedy":
            programs_to_update=message[1].split('\n')
            reply = QMessageBox.question(self,"Update Software", "Do you want to update {} programs?<br>{}".format(len(programs_to_update),", ".join(programs_to_update)))
            if reply==QMessageBox.Yes:
                self.runcommand("brew cask upgrade --greedy")
            #print(message[1])
            #print("####")
            #print(message[2])
        elif message[0] == "brew search --cask":
            self.apps["Software (Casks)"] = message[1].split("\n")
            selectedCats = [i.text() for i in self.AppCategories.selectedItems()]
            if "Software (Casks)" in selectedCats:
                self.AppList.clear()
                self.AppList.addItems(self.apps["Software (Casks)"])
        elif message[0] == "brew search":
            self.apps["Resources"] = message[1].split("\n")
            selectedCats = [i.text() for i in self.AppCategories.selectedItems()]
            if "Resources" in selectedCats:
                self.AppList.clear()
                self.AppList.addItems(self.apps["Resources"])
    def console_writer(self,text):
        self.console.insertHtml(text)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())


    def runcommand(self,command,printit=True):
        self.taskQ.put((command,printit))
    def on_startup(self):
        self.runcommand("brew search --cask", False)
        self.runcommand("brew search", False)
        self.runcommand("brew update --verbose")
        self.runcommand("brew cask outdated --greedy")
        self.runcommand("brew search --cask", False)
        self.runcommand("brew search", False)






