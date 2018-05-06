# ===============================================================================
# Copyright 2016 ross
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
from __future__ import print_function
import os

from traits.etsconfig.etsconfig import ETSConfig

from pychron.paths import global_hidden


def get_path(appname):
    return os.path.join(global_hidden, '{}.active_env'.format(appname))


def get_environment(appname):
    p = get_path(appname)
    if os.path.isfile(p):
        with open(p, 'r') as rfile:
            env = rfile.readline()
            return env.strip()


def set_environment(appname, env_path):
    p = get_path(appname)
    if not os.path.isdir(os.path.dirname(p)):
        os.mkdir(os.path.dirname(p))

    with open(p, 'w') as wfile:
        wfile.write('{}\n'.format(env_path))

    set_application_home(appname, env_path)


def set_application_home(appname, env=None):
    if env is None:
        env = get_environment(appname)

    if env:
        p = os.path.join(env, '.appdata', appname)
        print('setting application home to {}'.format(p))
        ETSConfig.application_home = p

        if not os.path.exists(ETSConfig.application_home):
            os.makedirs(ETSConfig.application_home)

# ============= EOF =============================================
