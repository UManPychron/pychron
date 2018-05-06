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
from traits.api import Str, Property, cached_property, Instance, Event, Any

from pychron.loggable import Loggable


class DVCAble(Loggable):
    dvc = Instance('pychron.dvc.dvc.DVC')
    iso_db_man = Any

    def get_database(self):
        if self.dvc:
            db = self.dvc.db
        else:
            db = self.iso_db_man.db
        return db


class DVCIrradiationable(DVCAble):

    level = Str
    levels = Property(depends_on='irradiation, updated')
    irradiation = Str
    irradiations = Property(depends_on='updated')

    updated = Event
    _suppress_auto_select_irradiation = False

    def verify_database_connection(self, inform=True):
        # return self.dvc.initialize(inform)
        self.debug('Verify database connection')

        ret = self.dvc.initialize(inform)
        if ret:
            # trigger reload of irradiations, and levels
            self.updated = True
        return ret

    def load(self):
        pass

    def setup(self):
        pass

    @cached_property
    def _get_irradiations(self):
        irrad_names = []
        db = self.get_database()
        if db.connect():
            with db.session_ctx():
                irs = db.get_irradiations()
                if irs:
                    irrad_names = [i.name for i in irs]
                    if irrad_names:
                        self.irradiation = irrad_names[0]
        return irrad_names

    @cached_property
    def _get_levels(self):
        levels = []
        db = self.get_database()
        if db.connect():
            with db.session_ctx():
                irrad = db.get_irradiation(self.irradiation)
                if irrad:
                    levels = sorted([li.name for li in irrad.levels])
                    if levels:
                        self.level = levels[0]
        return levels
# ============= EOF =============================================
