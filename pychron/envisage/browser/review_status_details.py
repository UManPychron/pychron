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
from traits.api import HasTraits, Str, Int, Bool, Property, List
from traitsui.api import View, UItem, Controller, TabularEditor
# ============= standard library imports ========================
# ============= local library imports  ==========================
from traitsui.tabular_adapter import TabularAdapter

from pychron.dvc.func import get_review_status
from pychron.envisage.resources import icon

GREENBALL = icon('green_ball')


class RSDAdapter(TabularAdapter):
    columns = [('Status', 'status'),
               ('Process', 'process'),
               ('Date', 'date')]

    status_image = Property
    status_text = Str('')
    status_width = Int(50)

    def _get_status_image(self):
        if self.item.status:
            return GREENBALL


class ReviewStatusDetailsModel(HasTraits):
    items = List
    record_id = Str

    def __init__(self, record, *args, **kw):
        super(ReviewStatusDetailsModel, self).__init__(*args, **kw)

        if not record.review_status:
            get_review_status(record)

        # self.items = [item for m in ('intercepts', 'blanks', 'icfactors')
        #                    for item in self._make_item(record, m)]
        self.items = record.review_items
        self.record_id = record.record_id

    # def _make_item(self, record, tag):
    #     items = []
    #     for i in record.review_items:
    #
    #         # try:
    #         #     # status, date = getattr(record, '{}_review_status'.format(tag))
    #         # except AttributeError:
    #         #     status, date = False, ''
    #         #
    #         item = RSDItem(process=tag.capitalize(),
    #                        status=status,
    #                        date=date)
    #         items.append(item)
    #
    #     return items



class ReviewStatusDetailsView(Controller):
    def traits_view(self):
        v = View(UItem('items', editor=TabularEditor(editable=False,
                                                     adapter=RSDAdapter())),
                 title='Review Status Details ({})'.format(self.model.record_id),
                 kind='livemodal',
                 buttons=['OK'],
                 width=500)
        return v

# ============= EOF =============================================
