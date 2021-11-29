#!/usr/bin/env python3
import os
import re
import subprocess
from subprocess import PIPE
import importlib


from PySide2.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QMessageBox, QFileDialog,
                               QCheckBox, QGridLayout)
from PySide2.QtCore import QDir, QFile

from binaryninjaui import (
    UIContext,
    DockHandler,
    DockContextHandler,
    UIAction,
    UIActionHandler,
    Menu,
)
from binaryninja.interaction import show_message_box
from binaryninja.enums import MessageBoxButtonSet, MessageBoxIcon, VariableSourceType
from binaryninja.architecture import Architecture
from binaryninja.callingconvention import CallingConvention
from binaryninja.function import RegisterValue
from binaryninja.platform import Platform

class ObjgraphPlatform(Platform):
    name = "platform_objgraph"


objgrapher = None  # type: Objgrapher


def rebase_addr(addr, up=True):
    if up:
        return addr + 0x40000000 - 120
    else:
        return addr - 0x40000000 + 120


def get_instr(addr):
    global objgrapher

    if not objgrapher:
        raise Exception("Objgrapher not initialized yet!")

    r_addr = rebase_addr(addr)
    try:
        return objgrapher.dump[r_addr]
    except KeyError:
        return None

#
# Worker class
#


class Objgrapher:
    def __init__(self, binutils_path=None, bv=None, use_cache=False, arch_name=None):
        self.binutils_path = binutils_path
        self.bv = bv
        self.binary_path = bv.file.filename
        self.arch_name = arch_name

        self.dump = {}
        self.syms = {}


    def init_grapher(self, use_cache=False):
        self._init_objdump_dump(use_cache=use_cache)
        self._init_readelf_syms(use_cache=use_cache)

    def _init_objdump_dump(self, use_cache=False):
        if use_cache:
            with open(self.binary_path + ".objdump", "r") as fp:
                objdump_data = fp.read()
        else:
            objdump_data = subprocess.run(
                [os.path.join(self.binutils_path, "objdump"), "-D", "-M", "intel", self.binary_path],
                stdout=PIPE
            )

        regex = r"([0-9,a-f]{8}):\t([0-9,a-f]{2} .*)\t(.*)"
        out = re.findall(regex, objdump_data)

        # sample the instruction size
        sampled_insns = [len(insn[1].split(" ")) for insn in out[:20]]
        same_size = [sampled_insns[0] == insn_l for insn_l in sampled_insns]
        if all(same_size):
            self.set_insn_size = same_size
            self.max_insn_size = same_size
        else:
            self.max_insn_size = max(sampled_insns)

        self.dump = {int(o[0], 16): o[2] for o in out}

    def _init_readelf_syms(self, use_cache=False):
        if use_cache:
            with open(self.binary_path + ".readelf", "r") as fp:
                readelf_data = fp.read()
        else:
            readelf_data = subprocess.run(
                [os.path.join(self.binutils_path, "readelf"), "-s", self.binary_path],
                stdout=PIPE
            )

        # finds all functions
        regex = r".*: ([0-9,a-f]{8}).*FUNC.*GLOBAL.*DEFAULT\s+\d (.*)"
        out = re.findall(regex, readelf_data)
        self.syms = {rebase_addr(int(o[0], 16), up=False): o[1] for o in out}

    def create_functions(self):
        arch = Architecture[self.arch_name]
        objgraph_plat = ObjgraphPlatform(arch)
        self.bv.platform = objgraph_plat
        for addr, sym in self.syms.items():
            func = self.bv.create_user_function(addr)
            func.name = sym


#
# UI
#

class ObjgraphConfig(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Configure Objgraph")

        self._main_layout = QVBoxLayout()
        self._user_edit = None  # type:QLineEdit
        self._binutils_edit = None  # type:QLineEdit
        self._dumpfile_checkbox = None  # type:QCheckBox

        self._init_widgets()
        self.setLayout(self._main_layout)
        self.show()

    def _init_widgets(self):

        upper_layout = QGridLayout()
        row = 0

        # binutils label
        binutils_label = QLabel(self)
        binutils_label.setText("Binutils Folder")
        # binutils path
        self._binutils_edit = QLineEdit(self)
        self._binutils_edit.setFixedWidth(150)
        # repo path selection button
        repo_button = QPushButton(self)
        repo_button.setText("...")
        repo_button.clicked.connect(self._on_binutils_clicked)
        repo_button.setFixedWidth(40)
        # add it
        upper_layout.addWidget(binutils_label, row, 0)
        upper_layout.addWidget(self._binutils_edit, row, 1)
        upper_layout.addWidget(repo_button, row, 2)
        row += 1

        # regex label
        arch_label = QLabel(self)
        arch_label.setText("Arch class name")
        # regex path
        self._arch_edit = QLineEdit(self)
        self._arch_edit.setFixedWidth(150)
        # add it
        upper_layout.addWidget(arch_label, row, 0)
        upper_layout.addWidget(self._arch_edit, row, 1)
        upper_layout.addWidget(repo_button, row, 2)
        row += 1

        # dumpfile checkbox
        self._dumpfile_checkbox = QCheckBox(self)
        self._dumpfile_checkbox.setText("Use dumpfile")
        self._dumpfile_checkbox.setToolTip("I've already run objdump/readelf once; use those files instead of"
                                           "running my binutils.")
        self._dumpfile_checkbox.setChecked(False)
        # add it
        upper_layout.addWidget(self._dumpfile_checkbox, row, 1)
        row += 1

        # buttons
        self._ok_button = QPushButton(self)
        self._ok_button.setText("OK")
        self._ok_button.setDefault(True)
        self._ok_button.clicked.connect(self._on_ok_clicked)

        cancel_button = QPushButton(self)
        cancel_button.setText("Cancel")
        cancel_button.clicked.connect(self._on_cancel_clicked)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self._ok_button)
        buttons_layout.addWidget(cancel_button)

        # main layout
        self._main_layout.addLayout(upper_layout)
        self._main_layout.addLayout(buttons_layout)

    #
    # Event handlers
    #

    def _on_ok_clicked(self):
        global objgrapher
        path = self._binutils_edit.text()
        arch_name = self._arch_edit.text()
        use_cache = self._dumpfile_checkbox.isChecked()

        objgrapher.binutils_path = path
        objgrapher.arch_name = arch_name
        objgrapher.init_grapher(use_cache=use_cache)
        objgrapher.create_functions()

        self.close()

    def _on_binutils_clicked(self):
        directory = QFileDialog.getExistingDirectory(self, "Select binutils folder", "",
                                                    QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        self._binutils_edit.setText(QDir.toNativeSeparators(directory))

    def _on_regex_clicked(self):
        file = QFileDialog.getOpenFileName(self, "Select arch class file")
        self._arch_edit.setText(file[0])

    def _on_cancel_clicked(self):
        self.close()


def launch_objgraph_configure(context):
    global objgrapher
    if context.binaryView is None:
        show_message_box(
            "No binary is loaded",
            "There is no Binary View available. Please open a binary in Binary Ninja first.",
            MessageBoxButtonSet.OKButtonSet,
            MessageBoxIcon.ErrorIcon,
        )
        return

    objgrapher = Objgrapher(bv=context.binaryView)
    config = ObjgraphConfig()
    config.exec_()


#
# Binja Registration
#

configure_objgraph = "Objgraph: Configure"
UIAction.registerAction(configure_objgraph)
UIActionHandler.globalActions().bindAction(
    configure_objgraph, UIAction(launch_objgraph_configure)
)
Menu.mainMenu("Tools").addAction(configure_objgraph, "Objgraph")