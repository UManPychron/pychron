# ===============================================================================
# Copyright 2015 Jake Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

# ============= enthought library imports =======================
from __future__ import absolute_import
from pyface.qt.QtCore import Qt
from pyface.qt.QtGui import QPlainTextEdit
from pyface.qt.QtGui import QVBoxLayout
from pyface.qt.QtGui import QWidget, QLabel


# ============= standard library imports ========================
# ============= local library imports  ==========================


class GosubPopupWidget(QWidget):
    def __init__(self, text):
        super(GosubPopupWidget, self).__init__()
        self.setWindowFlags(Qt.ToolTip)
        layout = QVBoxLayout()

        if text:
            self.text = QPlainTextEdit()
            self.text.setPlainText(text)

        else:
            self.text = QLabel('Invalid Gosub')
            self.text.setStyleSheet('QLabel {color: green; font-size: 30px}')

        layout.addWidget(self.text)
        self.setLayout(layout)
        self.resize(500, 300)


# ============= EOF =============================================



