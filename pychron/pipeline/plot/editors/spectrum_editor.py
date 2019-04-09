# ===============================================================================
# Copyright 2013 Jake Ross
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
from traits.api import Instance, on_trait_change

# ============= standard library imports ========================
# ============= local library imports  ==========================
from pychron.options.options_manager import SpectrumOptionsManager
from pychron.pipeline.plot.editors.interpreted_age_editor import InterpretedAgeEditor
from pychron.pipeline.plot.models.spectrum_model import SpectrumModel


class SpectrumEditor(InterpretedAgeEditor):
    plotter_options_manager = Instance(SpectrumOptionsManager, ())
    basename = 'spec'
    figure_model_klass = SpectrumModel

    @on_trait_change('figure_model:panels:make_ideogram_event')
    def handle_make_ideogram(self, evt):
        self.information_dialog('make ideogram from spectrum not yet enabled')

    def _set_preferred_age_kind(self, ias):
        for ia in ias:
            if ia.plateau_age:
                ia.preferred_age_kind = 'Plateau'
            else:
                ia.preferred_age_kind = 'Integrated'

# ============= EOF =============================================

