# ===============================================================================
# Copyright 2012 Jake Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

# ============= enthought library imports =======================
from __future__ import absolute_import
from sqlalchemy import Column, Integer, DateTime, String, Float, TEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func

# ============= standard library imports ========================
# ============= local library imports  ==========================
from pychron.database.core.base_orm import BaseMixin

Base = declarative_base()


class LabTable(Base, BaseMixin):
    labnumber = Column(String(40))
    step = Column(String(20))
    uuid = Column(String(40))
    aliquot = Column(Integer)
    mass_spectrometer = Column(String(40))
    extract_device = Column(String(40))
    extract_units = Column(String(10))
    extract_value = Column(Float)
    cleanup = Column(Float)
    duration = Column(Float)

    weight = Column(Float)
    comment = Column(TEXT)

    collection_path = Column(String(200))
    repository_path = Column(String(200))
    create_date = Column(DateTime, default=func.now())

# ============= EOF =============================================
