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
from __future__ import absolute_import
from traits.api import HasTraits, Any, List, Str, Bool, Float
from traitsui.api import View, UItem, InstanceEditor, VGroup, Item, EnumEditor, TableEditor
from traitsui.extras.checkbox_column import CheckboxColumn
from traitsui.table_column import TableColumn, ObjectColumn

from pychron.persistence_loggable import PersistenceMixin


class Detector(HasTraits):
    name = Str
    enabled = Bool
    deflection = Float

    def __init__(self, obj):
        self.name = obj.name
        self.enabled = False
        self.deflection = obj.deflection


class MFTableConfig(HasTraits, PersistenceMixin):
    peak_center_config = Any
    detectors = List
    available_detector_names = List
    finish_detector = Str(dump=True)
    finish_isotope = Str(dump=True)

    isotopes = List
    isotope = Str(dump=True)

    pdetectors = List(dump=True)

    def dump(self, verbose=False):
        self.pdetectors = [(d.name, d.enabled, d.deflection) for d in self.detectors if d.enabled]
        super(MFTableConfig, self).dump(verbose=verbose)

    def get_finish_position(self):
        return self.finish_isotope, self.finish_detector

    def set_detectors(self, dets):
        self.detectors = [Detector(d) for d in dets]
        self.available_detector_names = [di.name for di in self.detectors]
        for d in self.detectors:
            for name, e, defl, in self.pdetectors:
                if name == d.name:
                    d.enabled, d.deflection = e, defl

    def traits_view(self):
        pcc = VGroup(UItem('peak_center_config',
                           editor=InstanceEditor(),
                           style='custom'), label='Peak Center Config.', show_border=True)

        cols = [CheckboxColumn(name='enabled'), ObjectColumn(name='name'),
                ObjectColumn(name='deflection')]

        v = View(VGroup(Item('detectors',
                             editor=TableEditor(columns=cols)),
                        Item('isotope', editor=EnumEditor(name='isotopes')),
                        VGroup(Item('finish_detector', editor=EnumEditor(name='available_detector_names')),
                               Item('finish_isotope', editor=EnumEditor(name='isotopes')),
                               show_border=True, label='End Position'),
                        pcc),
                 title='Populate Magnetic Field Table',
                 kind='livemodal',
                 buttons=['OK', 'Cancel'])
        return v

# ============= EOF =============================================
