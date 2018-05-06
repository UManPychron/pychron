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
from pychron.pipeline.plot.panels.references_panel import ReferencesPanel
from pychron.pipeline.plot.plotter.icfactor import ICFactor
from pychron.processing.analysis_graph import AnalysisStackedRegressionGraph
# from pychron.pipeline.plot import ReferencesPanel
# from pychron.pipeline.plot import ICFactor


class ICFactorPanel(ReferencesPanel):
    _figure_klass = ICFactor
    _graph_klass = AnalysisStackedRegressionGraph

# ============= EOF =============================================
