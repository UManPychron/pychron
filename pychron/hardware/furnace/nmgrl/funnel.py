# ===============================================================================
# Copyright 2016 Jake Ross
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
from __future__ import absolute_import
import json
# ============= local library imports  ==========================
from pychron.hardware.furnace.nmgrl.nmgrl_furnace_drive import NMGRLFurnaceDrive


class NMGRLFurnaceFunnel(NMGRLFurnaceDrive):
    _simulation_funnel_up = True

    def in_up_position(self):
        if not self.simulation:
            return self.ask('InUpPosition') == 'OK'
        else:
            return self._simulation_funnel_up

    def in_down_position(self):
        if not self.simulation:
            return self.ask('InDownPosition') == 'OK'
        else:
            return not self._simulation_funnel_up

    def read_position(self):
        pos = self.ask(self._build_command('GetPosition'))
        try:
            return float(pos)
        except (TypeError, ValueError):
            pass

    def set_value(self, pos):
        self.ask(self._build_command('SetPosition', position=pos))

    def lower(self, block=True):
        self.ask(self._build_command('LowerFunnel'))
        if block:
            self._block(delay=20, period=1)

    def raise_(self, block=True):
        self.ask(self._build_command('RaiseFunnel'))
        if block:
            self._block(delay=20, period=1)
# ============= EOF =============================================



