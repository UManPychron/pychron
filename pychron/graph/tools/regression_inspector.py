# ===============================================================================
# Copyright 2012 Jake Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

# ============= enthought library imports =======================
from __future__ import absolute_import
from pychron.core.helpers.formatting import floatfmt, format_percent_error
from pychron.core.regression.mean_regressor import MeanRegressor
from pychron.graph.tools.info_inspector import InfoInspector, InfoOverlay
from six.moves import map
import six


# ============= standard library imports ========================
# ============= local library imports  ==========================


class RegressionInspectorTool(InfoInspector):
    def assemble_lines(self):
        lines = []
        if self.current_position:
            reg = self.component.regressor

            v, e = reg.predict(0), reg.predict_error(0)
            x = self.current_position[0]
            vv, ee = reg.predict(x), reg.predict_error(x)

            lines = [reg.make_equation(),
                     'x=0, y={} +/-{}({}%)'.format(floatfmt(v, n=9),
                                                   floatfmt(e, n=9),
                                                   format_percent_error(v, e)),
                     'x={}, y={} +/-{}({}%)'.format(x, floatfmt(vv, n=9),
                                                    floatfmt(ee, n=9),
                                                    format_percent_error(vv, ee))]

            if reg.mswd not in ('NaN', None):
                valid = '' if reg.valid_mswd else '*'
                lines.append('MSWD= {}{}, n={}'.format(valid,
                                                       floatfmt(reg.mswd, n=3), reg.n))

            mi, ma = reg.min, reg.max
            lines.append('Min={}, Max={}, D={}%'.format(floatfmt(mi),
                                                        floatfmt(ma), floatfmt((ma - mi) / ma * 100)))

            lines.append('Mean={}, SD={}, SEM={}, N={}'.format(floatfmt(reg.mean), floatfmt(reg.std),
                                                               floatfmt(reg.sem), reg.n))
            lines.append('R2={}, R2-Adj.={}'.format(floatfmt(reg.rsquared), floatfmt(reg.rsquared_adj)))
            lines.extend([l.strip() for l in reg.tostring().split(',')])

        return lines


class RegressionInspectorOverlay(InfoOverlay):
    pass

# ============= EOF =============================================
