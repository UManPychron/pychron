# ===============================================================================
# Copyright 2014 Jake Ross
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
import time
from threading import Thread

import struct
from numpy import array, vstack
from traits.api import Array, Any, Instance, Float

from pychron.core.helpers.binpack import pack
from pychron.core.helpers.formatting import floatfmt
from pychron.loggable import Loggable
from pychron.managers.data_managers.csv_data_manager import CSVDataManager


class ResponseRecorder(Loggable):
    period = Float(2)
    response_data = Array
    output_data = Array
    setpoint_data = Array

    _alive = False

    output_device = Any
    response_device = Any
    response_device_secondary = Any
    data_manager = Instance(CSVDataManager)

    _start_time = 0
    _write_data = False

    def start(self, base_frame_name=None):
        if self._alive:
            self.debug('response recorder already alive')
            return

        t = time.time()
        self._start_time = t
        self.response_data = array([(t, 0)])
        self.output_data = array([(t, 0)])
        self.setpoint_data = array([(t, 0)])
        self._write_data = False

        if base_frame_name:
            self._write_data = True
            self.data_manager = CSVDataManager()
            self.data_manager.new_frame(base_frame_name=base_frame_name)
            self.data_manager.write_to_frame(('#time', self.output_device.name,
                                              self.response_device.name,
                                              self.response_device_secondary.name))

        t = Thread(target=self.run)
        t.setDaemon(True)
        t.start()

    def run(self):
        self.debug('start response recorder')
        self._alive = True
        st = self._start_time
        p = self.period
        rd = self.response_device
        rds = self.response_device_secondary
        od = self.output_device
        dm = self.data_manager

        wd = self._write_data

        odata = self.output_data
        rdata = self.response_data
        sdata = self.setpoint_data
        r2 = None
        while self._alive:
            to = time.time()
            t = to - st
            out = od.get_output()
            odata = vstack((odata, (t, out)))

            sp = od.get_setpoint()
            sdata = vstack((sdata, (t, sp)))

            r = rd.get_response(force=True)
            rdata = vstack((rdata, (t, r)))

            self.debug('response t={}, out={}, setpoint={}, response={}'.format(t, out, sp, r))
            if rds:
                r2 = rds.get_response(force=True)

            if wd:
                if r2:
                    datum = (t, out, sp, r, r2)
                else:
                    datum = (t, out, sp, r)

                datum = [floatfmt(x, n=3) for x in datum]

                dm.write_to_frame(datum)

            et = time.time() - to
            slt = p - et - 0.001
            if slt > 0:
                time.sleep(slt)

            self.output_data = odata
            self.response_data = rdata
            self.setpoint_data = sdata

    def check_reached_setpoint(self, v, n, tol, std=None):
        """
        return True if response is OK, i.e. average of last n points is within tol of v.
        if std is not None then standard dev must be less than std
        :param v:
        :param n:
        :param tol:
        :param std:
        :return:
        """
        pts = self.response_data[-n:, 1]

        std_bit = True
        if std:
            std_bit = pts.std() < std

        error_bit = abs(pts.mean() - v) < tol

        return std_bit and error_bit

    def stop(self):
        self.debug('stop response recorder')
        self._alive = False
        if self.data_manager:
            self.data_manager.close_file()

    def get_response_blob(self):
        if len(self.response_data):
            # return ''.join([struct.pack('<ff', x, y) for x, y in self.response_data])
            return pack('<ff', self.response_data)

    def get_output_blob(self):
        if len(self.output_data):
            return pack('<ff', self.output_data)
            # return ''.join([struct.pack('<ff', x, y) for x, y in self.output_data])

    def get_setpoint_blob(self):
        if len(self.setpoint_data):
            return pack('<ff', self.setpoint_data)
            # return ''.join([struct.pack('<ff', x, y) for x, y in self.setpoint_data])

    @property
    def max_response(self):
        if len(self.response_data):
            return self.response_data.max()

# ============= EOF =============================================
