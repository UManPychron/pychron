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
from __future__ import print_function

import time
from datetime import datetime
from traits.api import List

from pychron.hardware.isotopx_spectrometer_controller import NGXController
from pychron.pychron_constants import ISOTOPX_DEFAULT_INTEGRATION_TIME, ISOTOPX_INTEGRATION_TIMES, NULL_STR
from pychron.spectrometer.base_spectrometer import BaseSpectrometer
from pychron.spectrometer.isotopx import SOURCE_CONTROL_PARAMETERS, IsotopxMixin
from pychron.spectrometer.isotopx.detector.ngx import NGXDetector
from pychron.spectrometer.isotopx.magnet.ngx import NGXMagnet
from pychron.spectrometer.isotopx.source.ngx import NGXSource


class NGXSpectrometer(BaseSpectrometer, IsotopxMixin):
    # integration_time = Int
    integration_times = List(ISOTOPX_INTEGRATION_TIMES)

    magnet_klass = NGXMagnet
    detector_klass = NGXDetector
    source_klass = NGXSource
    microcontroller_klass = NGXController

    rcs_id = 'NOM'
    # username = Str('')
    # password = Str('')

    _test_connect_command = 'GETMASS'
    _read_enabled = True
    use_deflection_correction = False
    use_hv_correction = False

    def _microcontroller_default(self):
        service = 'pychron.hardware.isotopx_spectrometer_controller.NGXController'
        s = self.application.get_service(service)
        return s

    def make_configuration_dict(self):
        return {}

    def make_gains_dict(self):
        return {}

    def make_deflection_dict(self):
        return {}

    def convert_to_axial(self, det, v):
        print('asdfsadf', det, det.index, v)
        v = v - (det.index - 2)
        return v

    def start(self):
        self.set_integration_time(1, force=True)

    def finish_loading(self):
        super(NGXSpectrometer, self).finish_loading()
        ret = self._get_cached_config()
        if ret is not None:
            specparams, defl, trap, magnet = ret
            mftable_name = magnet.get('mftable')
            if mftable_name:
                self.debug('updating mftable name {}'.format(mftable_name))
                self.magnet.field_table.path = mftable_name
                self.magnet.field_table.load_table(load_items=True)

    def _send_configuration(self, **kw):
        pass

    def get_update_period(self, it=None, is_scan=False):
        """
        """

        if is_scan:
            return 0.1

        return self.integration_time * 0.95

    def trigger_acq(self, verbose=False):
        # self.debug('trigger acquie {}'.format(self.microcontroller.lock))
        # locking the microcontroller not necessary and detrimental when doing long integration times
        # other commands can be executed when waiting 10-20 sec integration period.
        # locking prevents those other command from happening. locking only ok when integration time < 5 seconds
        # probably (min time probably has to do with the update valve state frequency).
        # Disable locking complete for now

        # another trick could be to make it an rlock. if lock is acquired by reading data then valve commands ok.
        # but not vis versa.
        # while self.microcontroller.lock.locked():
        #    time.sleep(0.25)

        self.ask('StopAcq', verbose=verbose)
        return self.ask('StartAcq 1,{}'.format(self.rcs_id), verbose=verbose)

    def readline(self, verbose=False):
        if verbose:
            self.debug('readline')
        st = time.time()
        ds = ''
        while 1:
            if time.time() - st > (1.25 * self.integration_time):
                if verbose:
                    self.debug('readline timeout')
                return

            if not self._read_enabled:
                self.debug('readline canceled')
                return

            try:
                ds += self.read(16)
            except BaseException:
                self.debug_exception()
                self.debug(f'data left: {ds}')

            if ds.endswith('\r\n'):
                return ds.strip()

    def cancel(self):
        self.debug('canceling')
        self._read_enabled = False

    def read_intensities(self, timeout=60, trigger=False, target='ACQ.B', verbose=False):
        self._read_enabled = True
        if verbose:
            self.debug('read intensities')
        resp = True
        if trigger:
            resp = self.trigger_acq()
            if resp is not None:
                if verbose:
                    self.debug(f'waiting {self.integration_time * 0.95} before trying to get data')
                time.sleep(self.integration_time * 0.95)
                if verbose:
                    self.debug('trigger wait finished')

        keys = []
        signals = []
        collection_time = None

        # self.microcontroller.lock.acquire()
        # self.debug(f'acquired mcir lock {self.microcontroller.lock}')
        target = f'#EVENT:{target},{self.rcs_id}'
        if resp is not None:
            keys = self.detector_names[::-1]
            while 1:
                line = self.readline()
                if line is None:
                    break

                if verbose:
                    self.debug(f'raw: {line}')
                if line and line.startswith(target):
                    args = line[:-1].split(',')
                    ct = datetime.strptime(args[4], '%H:%M:%S.%f')

                    collection_time = datetime.now()

                    # copy to collection time
                    collection_time.replace(hour=ct.hour, minute=ct.minute, second=ct.second,
                                            microsecond=ct.microsecond)
                    signals = [float(i) for i in args[5:]]
                    if verbose:
                        self.debug(f'line: {line[:15]}')
                    break

        # self.microcontroller.lock.release()
        if len(signals) != len(keys):
            keys, signals = [], []
        return keys, signals, collection_time

    def read_integration_time(self):
        return self.integration_time

    def set_integration_time(self, it, force=False):
        """

        :param it: float, integration time in seconds
        :param force: set integration even if "it" is not different than self.integration_time
        :return: float, integration time
        """
        if self.integration_time != it or force:
            self.ask('StopAcq')
            self.debug('setting integration time = {}'.format(it))
            self.ask('SetAcqPeriod {}'.format(int(it * 1000)))
            self.trait_setq(integration_time=it)

        return it

    def read_parameter_word(self, keys):
        self.debug('read parameter word. keys={}'.format(keys))
        values = []
        for kk in keys:
            try:
                key = SOURCE_CONTROL_PARAMETERS[kk]
            except KeyError:
                values.append(NULL_STR)
                continue

            resp = self.ask('GetSourceOutput {}'.format(key))
            if resp is not None:
                try:
                    last_set, readback = resp.split(',')
                    values.append(float(readback))
                except ValueError:
                    values.append(NULL_STR)
        return values

    def _get_simulation_data(self):
        signals = [1, 100, 3, 0.01, 0.01, 0.01]  # + random(6)
        keys = ['H2', 'H1', 'AX', 'L1', 'L2', 'CDD']
        return keys, signals, None

    def _integration_time_default(self):
        self.default_integration_time = ISOTOPX_DEFAULT_INTEGRATION_TIME
        return ISOTOPX_DEFAULT_INTEGRATION_TIME

# ============= EOF =============================================
