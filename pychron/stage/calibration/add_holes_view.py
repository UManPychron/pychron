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
from hashlib import md5

from traits.api import HasTraits, BaseStr
from traitsui.api import View, UItem
from six.moves import range


# ============= standard library imports ========================
# ============= local library imports  ==========================

def parse_holestr(hstr):
    hs = []
    for sublist in hstr.split(','):
        if '-' in sublist:
            s, e = sublist.split('-')
            s, e = int(s.strip()), int(e.strip())
            for i in range(s, e + 1):
                hs.append(i)
        else:
            hs.append(int(sublist))
    return hs


class HolesTrait(BaseStr):
    def validate(self, obj, name, value):
        try:
            parse_holestr(value)
            return value
        except BaseException:
            pass

        self.error(obj, name, value)


class AddHolesView(HasTraits):
    hole_str = HolesTrait

    @property
    def holes(self):
        return parse_holestr(self.hole_str)

    @property
    def holes_id(self):
        return md5(str(self.holes)).hexdigest()

    def traits_view(self):
        v = View(UItem('hole_str'),
                 buttons=['OK', 'Cancel'])
        return v

# ============= EOF =============================================
