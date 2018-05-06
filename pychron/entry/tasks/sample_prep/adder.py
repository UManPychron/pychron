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
from __future__ import absolute_import
from traits.api import HasTraits, Str
from traits.trait_types import BaseStr
from traitsui.api import View, UItem, Item, VGroup


# ============= standard library imports ========================
# ============= local library imports  ==========================
class LenStr(BaseStr):
    def validate(self, obj, name, value):
        if value and len(value) > self.n:
            self.error(obj, name, value)
        else:
            return value


def lenstr(n):
    l = LenStr()
    l.n = n
    return l


class AddWorker(HasTraits):
    name = lenstr(32)
    fullname = lenstr(45)
    phone = lenstr(45)
    email = lenstr(45)
    comment = lenstr(140)

    def traits_view(self):
        v = View(VGroup(Item('name'),
                        Item('fullname'),
                        Item('phone'),
                        Item('email'),
                        VGroup(UItem('comment', style='custom'),
                               show_border=True,
                               label='Comment')),
                 title='Add New Worker',
                 kind='livemodal',
                 resizable=True,
                 buttons=['OK', 'Cancel'])
        return v


class AddSession(HasTraits):
    name = Str
    comment = lenstr(140)
    title = Str('Add New Session')

    def traits_view(self):
        v = View(VGroup(Item('name', label='SessionName'),
                        VGroup(UItem('comment', style='custom'),
                               show_border=True,
                               label='Comment')),
                 title=self.title,
                 kind='livemodal',
                 resizable=True,
                 buttons=['OK', 'Cancel'])
        return v

# ============= EOF =============================================
