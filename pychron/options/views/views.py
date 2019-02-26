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
from traits.api import Property
from traitsui.api import UItem, Item, HGroup, VGroup, EnumEditor
# ============= standard library imports ========================
# ============= local library imports  ==========================
from traitsui.editors import TabularEditor
from traitsui.tabular_adapter import TabularAdapter

from pychron.core.helpers.traitsui_shortcuts import okcancel_view
from pychron.envisage.icon_button_editor import icon_button_editor


class SubviewAdapter(TabularAdapter):
    columns = [('', 'name')]
    name_text = Property
    font = '10'

    def _get_name_text(self):
        return self.item


def view(title):
    agrp = HGroup(Item('selected', show_label=False,
                       editor=EnumEditor(name='names'),
                       tooltip='List of available plot options'),
                  icon_button_editor('controller.save_options', 'disk',
                                     tooltip='Save changes to options'),
                  icon_button_editor('controller.save_as_options', 'save_as',
                                     tooltip='Save options with a new name'),
                  icon_button_editor('controller.add_options',
                                     'add',
                                     tooltip='Add new plot options'),
                  icon_button_editor('controller.delete_options',
                                     'delete',
                                     tooltip='Delete current plot options',
                                     enabled_when='delete_enabled'),
                  icon_button_editor('controller.factory_default', 'edit-bomb',
                                     enabled_when='selected',
                                     tooltip='Apply factory defaults'))

    sgrp = UItem('subview_names',
                 width=-120,
                 editor=TabularEditor(editable=False,
                                      adapter=SubviewAdapter(),
                                      selected='selected_subview'))

    ogrp = UItem('subview',
                 style='custom')
    bgrp = HGroup(sgrp, ogrp)

    v = okcancel_view(VGroup(agrp, bgrp),
                      width=800,
                      height=750,
                      resizable=True,
                      title=title)
    return v

# ============= EOF =============================================
