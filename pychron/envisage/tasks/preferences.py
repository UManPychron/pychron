# ===============================================================================
# Copyright 2014 Jake Ross
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
from envisage.ui.tasks.preferences_pane import PreferencesPane
from traits.api import Directory, Bool, String, Float, Int, Str, Property
from traits.traits import Color
from traitsui.api import View, Item, VGroup

from pychron.core.ui.combobox_editor import ComboboxEditor
from pychron.envisage.tasks.base_preferences_helper import GitRepoPreferencesHelper, remote_status_item, \
    BasePreferencesHelper
from pychron.envisage.user_login import get_usernames


class GeneralPreferences(GitRepoPreferencesHelper):
    preferences_path = 'pychron.general'
    # root_dir = Directory
    # use_login = Bool
    # multi_user = Bool
    username = Str
    _usernames = Property
    environment = Directory
    confirm_quit = Bool
    show_random_tip = Bool
    # use_advanced_ui = Bool

    organization = String(enter_set=True, auto_set=False)
    default_principal_investigator = String

    def _get__usernames(self):
        return get_usernames()

    def _organization_changed(self, new):
        if not self.remote and new:
            self.remote = '{}/Laboratory'.format(new)


class GeneralPreferencesPane(PreferencesPane):
    model_factory = GeneralPreferences
    category = 'General'

    def traits_view(self):
        # root_grp = VGroup(Item('root_dir', label='Pychron Directory'),
        #                   show_border=True, label='Root')
        user_grp = VGroup(Item('username',
                               editor=ComboboxEditor(name='_usernames'),
                               label='Name'),
                          show_border=True, label='User')
        env_grp = VGroup(Item('environment', label='Directory'),
                         show_border=True, label='Environment')

        # login_grp = VGroup(Item('use_login', label='Use Login'),
        #                    Item('multi_user', label='Multi User'),
        #                    label='Login', show_border=True)

        o_grp = VGroup(Item('organization', resizable=True, label='Name'),
                       remote_status_item('Laboratory Repo'),
                       show_border=True,
                       label='Organization')

        v = View(VGroup(Item('confirm_quit', label='Confirm Quit',
                             tooltip='Ask user for confirmation when quitting application'),
                        Item('show_random_tip', label='Random Tip',
                             tooltip='Display a Random Tip whe the application starts'),
                        Item('default_principal_investigator', resizable=True, label='Default PI'),
                        # Item('use_advanced_ui', label='Advanced UI',
                        #      tooltip='Display the advanced UI'),
                        # root_grp,
                        # login_grp,
                        user_grp,
                        env_grp,
                        o_grp,
                        label='General',
                        show_border=True))
        return v


class BrowserPreferences(BasePreferencesHelper):
    preferences_path = 'pychron.browser'
    reference_hours_padding = Float
    max_history = Int
    unknown_color = Color
    blank_color = Color
    air_color = Color
    use_analysis_colors = Bool


class BrowserPreferencesPane(PreferencesPane):
    model_factory = BrowserPreferences
    category = 'Browser'

    def traits_view(self):
        acgrp = VGroup(Item('use_analysis_colors', label='Use Analysis Colors',
                            tooltip='Color analyses based on type in the Browser window'),
                       VGroup(Item('unknown_color'),
                              Item('blank_color'),
                              Item('air_color'), enabled_when='use_analysis_colors'),
                       show_border=True, label='Analysis Colors')

        v = View(
                 Item('reference_hours_padding',
                      label='References Padding (hrs)',
                      tooltip='Padding in hours when finding associated references'),
                 Item('max_history', label='Max. Analysis Sets',
                      tooltip='Maximum number of analysis sets to maintain'),
                 acgrp
                 )
        return v

# ============= EOF =============================================
