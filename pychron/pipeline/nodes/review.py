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
# ============= standard library imports ========================
# ============= local library imports  ==========================
from __future__ import absolute_import
from pychron.core.confirmation import confirmation_dialog
from pychron.pipeline.nodes.base import BaseNode


class ReviewNode(BaseNode):
    name = 'Review'
    auto_configure = False
    auto_review = True

    def configure(self, pre_run=False, **kw):
        return True

    def run(self, state):
        review = True
        if not self.auto_review:
            review = confirmation_dialog('Would you like to review before continuing?')

        if review:
            state.veto = self

# ============= EOF =============================================
