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
import re

from traits.trait_types import BaseStr
import six

pascalcase_regex = re.compile(r'^[A-Z0-9]{1}\w*$')


class PascalCase(BaseStr):
    def validate(self, obj, name, value):
        if not value or not pascalcase_regex.match(value):
            self.error(obj, name, value)
        else:
            return value


class SpacelessStr(BaseStr):
    def validate(self, object, name, value):
        if isinstance(value, six.string_types) and ' ' not in value:
            return value

        self.error(object, name, value)
# ============= EOF =============================================
