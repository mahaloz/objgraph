#!/usr/bin/env python3

from PySide2.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QMessageBox, QFileDialog,
                               QCheckBox, QGridLayout)
from PySide2.QtCore import QDir, QFile

my_bv = None

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


#
# work
#

class FooPlatform(Platform):
    name = "platform_foo"


def fix_platform():
    addr = 0x7154
    arch = Architecture['ObjgraphArch']
    foo_platform = FooPlatform(arch)
    my_bv.create_user_function(addr, plat=foo_platform)


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
        self._remote_edit = None  # type:QLineEdit
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
        regex_label = QLabel(self)
        regex_label.setText("Regex File")
        # regex path
        self._regex_edit = QLineEdit(self)
        self._regex_edit.setFixedWidth(150)
        # regex file selection button
        repo_button = QPushButton(self)
        repo_button.setText("...")
        repo_button.clicked.connect(self._on_regex_clicked)
        repo_button.setFixedWidth(40)
        # add it
        upper_layout.addWidget(regex_label, row, 0)
        upper_layout.addWidget(self._regex_edit, row, 1)
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
        path = self._binutils_edit.text()
        self.close()
        fix_platform()

    def _on_binutils_clicked(self):
        directory = QFileDialog.getExistingDirectory(self, "Select binutils folder", "",
                                                    QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        self._binutils_edit.setText(QDir.toNativeSeparators(directory))

    def _on_regex_clicked(self):
        directory = QFileDialog.getExistingDirectory(self, "Select regex file", "",
                                                     QFileDialog.DontResolveSymlinks)
        self._binutils_edit.setText(QFile.toNativeSeparators(directory))

    def _on_cancel_clicked(self):
        self.close()


def launch_objgraph_configure(context):
    global my_bv
    mv_bv = context.binaryView
    if context.binaryView is None:
        show_message_box(
            "No binary is loaded",
            "There is no Binary View available. Please open a binary in Binary Ninja first.",
            MessageBoxButtonSet.OKButtonSet,
            MessageBoxIcon.ErrorIcon,
        )
        return

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