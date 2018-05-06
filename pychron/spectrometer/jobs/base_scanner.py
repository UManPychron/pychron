# ===============================================================================
# Copyright 2016 Jake Ross
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
from traits.api import Bool, Any, Float, \
    Button, Instance, List
# ============= standard library imports ========================
from threading import Thread, Event
from numpy import hstack, array
import time
import os
# ============= local library imports  ==========================
from pychron.graph.graph import Graph
from pychron.paths import paths
from pychron.persistence_loggable import PersistenceLoggable


class BaseScanner(PersistenceLoggable):
    spectrometer = Any

    step = Float(0.1)

    clear_graph_button = Button
    start_scanner = Button
    stop_scanner = Button
    new_scanner = Button('New Magnet Scan')
    start_scanner_enabled = Bool
    stop_scanner_enabled = Bool
    new_scanner_enabled = Bool(True)

    graph = Instance(Graph)
    plotid = 0

    _cancel_event = None

    def stop(self):
        """
        Cancel the current scan

        :return:
        """
        if self._cancel_event:
            self._cancel_event.set()

    def scan(self):
        """
        Start a scan thread. calls ``Scanner._scan`` on a new thread

        :return:
        """
        # if self.plotid>0:
        # self.graph.new_series()
        self.set_plot_visiblity()

        self._cancel_event = Event()

        t = Thread(target=self._scan)
        t.start()

    def set_plot_visibility(self):
        pass

    def reset(self):
        self._clear_graph_button_fired()
        self._reset_hook()

    # private
    def _scan(self):
        graph = self.graph

        plot = graph.plots[0]
        try:
            line = plot.plots['plot{}'.format(self.plotid)][0]
        except KeyError:
            line, _ = graph.new_series()
        # xs = line.index.get_data()
        # ys = line.index.get_data()

        spec = self.spectrometer
        magnet = spec.magnet

        period = spec.integration_time - magnet.settling_time
        # period = 0.1
        st = time.time()

        limits = self._get_limits()
        graph.set_x_limits(*limits, pad='0.1')
        refdet = self.spectrometer.reference_detector

        for i, si in enumerate(self._calculate_steps(*limits)):
            if self._cancel_event.is_set():
                self.debug('exiting scan. dac={}'.format(si))
                break

            self._do_step(magnet, si)
            time.sleep(period)
            if i == 0:
                time.sleep(3)

            ks, ss = spec.get_intensities()

            refsig = refdet.intensity
            refk = '{}y{}'.format(refdet, self.plotid)
            rys = plot.data.get_data(refk)
            if i == 0:
                rys = array([refsig])
                xs = array([si])
            else:
                rys = hstack((rys, refsig))
                xs = hstack((xs, si))

            plot.data.update_data({'x{}'.format(self.plotid): xs})
            plot.data.set_data(refk, rys)

            ref_mi, ref_ma = mi, ma = rys.min(), rys.max()
            ref_r = rys.max() - ref_mi
            for det, sig in zip(ks, ss):
                if det == refdet.name:
                    continue

                oys = None
                k = 'odata{}_{}'.format(i, self.plotid)
                if hasattr(plot, k):
                    oys = getattr(plot, k)

                oys = array([sig]) if oys is None else hstack((oys, sig))
                setattr(plot, k, oys)

                mir = oys.min()
                r = oys.max() - mir
                oys = (oys - mir) * ref_r / r + ref_mi

                plot.data.update_data({'{}y{}'.format(det, self.plotid): oys})
                det = self.spectrometer.get_detector(det)
                if det.active:
                    mi, ma = min(mi, min(oys)), max(ma, max(oys))

            self.graph.set_y_limits(min_=mi, max_=ma, pad='0.05',
                                    pad_style='upper')

        self.plotid += 1
        self.debug('duration={:0.3f}'.format(time.time() - st))
        self.new_scanner_enabled = True
        self.start_scanner_enabled = True
        self.stop_scanner_enabled = False

    def _do_step(self, magnet, step):
        raise NotImplementedError

    def _calculate_steps(self):
        raise NotImplementedError

    def _reset_hook(self):
        pass

    # persistence
    @property
    def persistence_path(self):
        return os.path.join(paths.hidden_dir, self.__class__.__name__.lower())

    def _graph_factory(self):
        g = Graph()
        p = g.new_plot(padding_top=30, padding_right=10)
        self._setup_graph(g, p)
        return g

    def _setup_graph(self, g, p):
        pass

    def _graph_default(self):
        g = self._graph_factory()
        return g

    # handlers
    def _start_scanner_fired(self):
        print('start scanner')
        self.info('starting scanner')
        self.new_scanner_enabled = False
        self.start_scanner_enabled = False
        self.stop_scanner_enabled = True
        self.scan()

    def _stop_scanner_fired(self):
        self.stop()
        self.stop_scanner_enabled = False
        self.new_scanner_enabled = True

    def _new_scanner_fired(self):
        print('new scanner')
        self.info('new scanner')
        self.new_scanner_enabled = False
        self.start_scanner_enabled = True

    def _clear_graph_button_fired(self):
        self.graph.clear_plots()
        self.plotid = 0
        self.graph.redraw()

# ============= EOF =============================================
