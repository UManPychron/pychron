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
from __future__ import absolute_import
from __future__ import print_function
import re
# ============= local library imports  ==========================
"""
http://blog.amjith.com/fuzzyfinder-in-10-lines-of-python
"""


def func(regex, item, attr):
    txt = item
    if attr:
        txt = getattr(item, attr)

    match = regex.search(str(txt))
    if match:
        return len(match.group()), match.start(), item


def fuzzyfinder(user_input, collection, attr=None):
    pattern = '.*'.join(user_input)  # Converts 'djm' to 'd.*?j.*?m'
    try:
        regex = re.compile(pattern, re.IGNORECASE)  # Compiles a regex.
    except re.error:
        return []

    suggestions = [x for x in [func(regex, item, attr) for item in collection] if x is not None]
    return [x for _, _, x in suggestions]



if __name__ == '__main__':
    collection = ['django_migrations.py',
                  'django_admin_log.py',
                  'main_generator.py',
                  'migrations.py',
                  'api_user.doc',
                  'user_group.doc',
                  'accounts.txt']

    print(fuzzyfinder('djm', collection))
    print(fuzzyfinder('mig', collection))
    print(fuzzyfinder('user', collection))
# ============= EOF =============================================
