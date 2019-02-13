# ===============================================================================
# Copyright 2017 ross
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

import os

from traits.api import File

from pychron.data_mapper.sources.nu_source import NuFileSource
from pychron.data_mapper.sources.wiscar_meta_parser import WiscArMetaParser


class WiscArNuSource(NuFileSource):
    metadata_path = File

    def get_analysis_import_spec(self, delimiter=None):
        spec = super(WiscArNuSource, self).get_analysis_import_spec(delimiter=delimiter)

        mp = self.metadata_path
        if mp and os.path.isfile(mp):
            p = WiscArMetaParser()
            p.populate_spec(mp, spec)

        return spec

# ============= EOF =============================================
