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
from traits.api import Str, Bool, Enum, Int
from traitsui.api import View, UItem, Item, HGroup, VGroup
# ============= standard library imports ========================
# ============= local library imports  ==========================
from pychron.options.group.base_group_options import BaseGroupOptions


class SpectrumGroupOptions(BaseGroupOptions):

    calculate_fixed_plateau = Bool(False)
    calculate_fixed_plateau_start = Str
    calculate_fixed_plateau_end = Str
    center_line_style = Enum('No Line', 'solid', 'dash', 'dot dash', 'dot', 'long dash')
    center_line_width = Int(1)

    def traits_view(self):
        envelope_grp = HGroup(HGroup(UItem('use_fill'),
                                     Item('color')),
                              Item('alpha', label='Opacity'),
                              show_border=True,
                              label='Error Envelope')

        line_grp = HGroup(UItem('line_color'),
                          Item('line_width',
                               label='Width'),
                          show_border=True,
                          label='Plateau Line')

        center_line_grp = HGroup(UItem('center_line_style'),
                                 Item('center_line_width', enabled_when='center_line_style!="No Line"'),
                                 show_border=True,
                                 label='Center Line')

        plat_grp = HGroup(Item('calculate_fixed_plateau',
                               label='Fixed',
                               tooltip='Calculate a plateau over provided steps'),
                          Item('calculate_fixed_plateau_start', label='Start', enabled_when='calculate_fixed_plateau'),
                          Item('calculate_fixed_plateau_end', label='End', enabled_when='calculate_fixed_plateau'),
                          show_border=True, label='Calculate Plateau')

        g = VGroup(Item('bind_colors'),
                   envelope_grp, line_grp, plat_grp, center_line_grp,
                   show_border=True,
                   label='Group {}'.format(self.group_id + 1))

        v = View(g)
        return v

# def simple_view(self):
#         grps = self._get_groups()
#         g = VGroup(HGroup(Item('bind_colors', tooltip='Link line color and error envelope color'),
#                           icon_button_editor('edit_button', 'cog', tooltip='Edit group attributes')),
#                    *grps)
#         v = View(g)
#         return v
#
#
# class SpectrumGroupEditor(HasTraits):
#     option_groups = List
#
#     def traits_view(self):
#         v = View(UItem('option_groups',
#                        style='custom',
#                        editor=ListEditor(mutable=False,
#                                          style='custom',
#                                          editor=InstanceEditor())),
#                  buttons=['OK', 'Cancel', 'Revert'],
#                  kind='livemodal', resizable=True,
#                  height=700,
#                  title='Group Attributes')
#         return v

# ============= EOF =============================================
