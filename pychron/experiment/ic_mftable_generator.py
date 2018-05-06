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
import csv
import time
from contextlib import contextmanager

from pychron.loggable import Loggable
from pychron.paths import paths

ARGON_IC_MFTABLE = True


class ICMFTableGenerator(Loggable):
    def make_mftable(self, arun, detectors, refiso, peak_center_config='ic_peakhop', update_existing=True):
        """
            peak center `refiso` for each detector in detectors
        :return:
        """
        ion = arun.ion_optics_manager
        plot_panel = arun.plot_panel

        def func(x):
            if not x:
                ion.cancel_peak_center()

        @contextmanager
        def listen():
            arun.on_trait_change(func, '_alive')
            yield
            arun.on_trait_change(func, '_alive', remove=True)

        with listen():
            self.info('Making IC MFTable')
            results = []
            for di in detectors:
                if not arun.is_alive():
                    return False

                self.info('Peak centering {}@{}'.format(di, refiso))
                ion.setup_peak_center(detector=[di], isotope=refiso,
                                      config_name=peak_center_config,
                                      plot_panel=plot_panel, show_label=True, use_configuration_dac=False)

                arun.peak_center = ion.peak_center
                ion.do_peak_center(new_thread=False, save=False, warn=False)
                apc = ion.adjusted_peak_center_result
                if apc:
                    self.info('Peak Center {}@{}={:0.6f}'.format(di, refiso, apc))
                    results.append((di, apc))
                    time.sleep(0.25)
                else:
                    return False

        if update_existing:
            self._update_table(arun, refiso, results)
        else:
            self._write_table(detectors, refiso, results)
        return True

    def _update_table(self, arun, refiso, results):
        magnet = arun.ion_optics_manager.spectrometer.magnet
        for det, apc in results:
            magnet.update_field_table(det, refiso, apc, 'ic_generator', update_others=False)

    def _write_table(self, detectors, refiso, results):
        p = paths.ic_mftable
        self.info('Writing new IC MFTable to {}'.format(p))
        with open(p, 'w') as wfile:
            w = csv.writer(wfile)

            w.writerow(['parabolic' if ARGON_IC_MFTABLE else 'discrete'])
            header = ['iso'] + list(detectors)
            w.writerow(header)
            w.writerow([refiso] + results)

            # temporary hack to full write the ic mf table
            if ARGON_IC_MFTABLE and refiso == 'Ar40' and detectors[0] in ('H1', 'H2'):
                row = ['Ar39', results[0] - 0.1]
                row.extend(results[1:])

                w.writerow(row)

                row = ['Ar36', results[0] - 0.4]
                row.extend(results[1:])

                w.writerow(row)

# ============= EOF =============================================
