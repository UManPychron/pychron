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

from traits.api import HasTraits, Str, Int, Bool, Float, Property, List, Instance, Event, Button
from traitsui.api import View, UItem, TableEditor, VGroup, HGroup, Item, spring, Tabbed
from traitsui.extras.checkbox_column import CheckboxColumn
from traitsui.table_column import ObjectColumn
# ============= standard library imports ========================
from numpy import array, zeros, vstack, linspace, meshgrid, arctan2, sin, cos
# ============= local library imports  ==========================
from uncertainties import nominal_value, std_dev
from pychron.core.helpers.formatting import calc_percent_error, floatfmt
from pychron.core.regression.flux_regressor import PlaneFluxRegressor, BowlFluxRegressor
from pychron.envisage.icon_button_editor import icon_button_editor
from pychron.envisage.tasks.base_editor import BaseTraitsEditor
from pychron.graph.contour_graph import ContourGraph
from pychron.graph.error_bar_overlay import ErrorBarOverlay
from pychron.graph.graph import Graph
from pychron.graph.tools.analysis_inspector import AnalysisPointInspector
from pychron.pipeline.editors.irradiation_tray_overlay import IrradiationTrayOverlay
from pychron.pipeline.plot.plotter.arar_figure import SelectionFigure
from pychron.processing.flux.utilities import mean_j


def make_grid(r, n):
    xi = linspace(-r, r, n)
    yi = linspace(-r, r, n)
    return meshgrid(xi, yi)


def add_inspector(scatter):
    from pychron.graph.tools.point_inspector import PointInspector
    from pychron.graph.tools.point_inspector import PointInspectorOverlay

    point_inspector = PointInspector(scatter)
    pinspector_overlay = PointInspectorOverlay(component=scatter,
                                               tool=point_inspector)

    scatter.overlays.append(pinspector_overlay)
    scatter.tools.append(point_inspector)


def add_analysis_inspector(scatter, items, add_selection=True, value_format=None, convert_index=None):
    from chaco.tools.broadcaster import BroadcasterTool
    from pychron.graph.tools.rect_selection_tool import RectSelectionTool
    from pychron.graph.tools.rect_selection_tool import RectSelectionOverlay
    from pychron.graph.tools.point_inspector import PointInspectorOverlay

    broadcaster = BroadcasterTool()
    scatter.tools.append(broadcaster)
    if add_selection:
        rect_tool = RectSelectionTool(scatter)
        rect_overlay = RectSelectionOverlay(component=scatter,
                                            tool=rect_tool)

        scatter.overlays.append(rect_overlay)
        broadcaster.tools.append(rect_tool)

    if value_format is None:
        value_format = lambda x: '{:0.5f}'.format(x)

    if convert_index is None:
        convert_index = lambda x: '{:0.3f}'.format(x)

    point_inspector = AnalysisPointInspector(scatter,
                                             analyses=items,
                                             convert_index=convert_index,
                                             # index_tag=index_tag,
                                             # index_attr=index_attr,
                                             value_format=value_format)
    # additional_info=additional_info)

    pinspector_overlay = PointInspectorOverlay(component=scatter,
                                               tool=point_inspector)

    scatter.overlays.append(pinspector_overlay)
    broadcaster.tools.append(point_inspector)

    # u = lambda a, b, c, d: self.update_graph_metadata(a, b, c, d)
    # scatter.index.on_trait_change(self.update_graph_metadata, 'metadata_changed')


class FluxPosition(HasTraits):
    hole_id = Int
    identifier = Str
    sample = Str
    x = Float
    y = Float
    z = Float
    theta = Float
    saved_j = Float
    saved_jerr = Float

    mean_j = Float
    mean_jerr = Float

    n = Int

    j = Float(enter_set=True, auto_set=False)
    jerr = Float(enter_set=True, auto_set=False)
    use = Bool(True)
    save = Bool(True)
    dev = Float

    percent_saved_error = Property
    percent_mean_error = Property
    percent_pred_error = Property

    analyses = List
    error_kind = Str
    monitor_age = Float
    lambda_k = Float
    was_altered = Bool

    def set_mean_j(self):
        ans = [a for a in self.analyses if not a.is_omitted()]
        if ans:
            j = mean_j(ans, self.error_kind, self.monitor_age, self.lambda_k)
            self.mean_j = nominal_value(j)
            self.mean_jerr = std_dev(j)

        self.n = len(ans)

    def _get_percent_saved_error(self):
        return calc_percent_error(self.saved_j, self.saved_jerr)

    def _get_percent_mean_error(self):
        if self.mean_jerr and self.mean_jerr:
            return calc_percent_error(self.mean_j, self.mean_jerr)

    def _get_percent_pred_error(self):
        if self.j and self.jerr:
            return calc_percent_error(self.j, self.jerr)


class FluxResultsEditor(BaseTraitsEditor, SelectionFigure):
    geometry = List
    monitor_positions = List
    unknown_positions = List
    positions = List

    analyses = List
    graph = Instance('pychron.graph.graph.Graph')
    _regressor = None

    levels = 10
    show_labels = False

    color_map_name = 'jet'
    marker_size = Int(2)

    save_all_button = Event
    save_unknowns_button = Event
    recalculate_button = Button('Calculate')

    max_j = Float
    min_j = Float
    percent_j_change = Property
    # j_gradient = Property
    plotter_options = None

    def set_items(self, *args, **kw):
        pass

    def _recalculate_button_fired(self):
        self.predict_values()

    def set_positions(self, mon, unk):
        self.monitor_positions = mon
        self.unknown_positions = unk
        # self.positions = mon + unk

    def predict_values(self, refresh=False):
        try:
            x, y, z, ze = array([(pos.x, pos.y, pos.mean_j, pos.mean_jerr)
                                 for pos in self.monitor_positions
                                 if pos.use]).T

        except ValueError:
            # self.debug('no monitor positions to fit')
            return

        n = x.shape[0]
        if n >= 3:
            # n = z.shape[0] * 10
            r = max((max(abs(x)), max(abs(y))))
            r *= 1.25
            reg = self._regressor_factory(x, y, z, ze)
            self._regressor = reg
        else:
            # self.warning('not enough monitor positions. at least 3 required. Currently only {} active'.format(n))
            return

        if self.plotter_options.use_monte_carlo:
            from pychron.core.stats.monte_carlo import monte_carlo_error_estimation

            pts = array([[p.x, p.y] for p in self.positions])
            nominals = reg.predict(pts)
            errors = monte_carlo_error_estimation(reg, nominals, pts,
                                                  ntrials=self.plotter_options.monte_carlo_ntrials)
            for p, j, je in zip(self.positions, nominals, errors):
                oj = p.saved_j

                p.j = j
                p.jerr = je

                p.dev = (oj - j) / j * 100
        else:
            for positions in (self.unknown_positions, self.monitor_positions):
                for p in positions:
                    j = reg.predict([(p.x, p.y)])[0]
                    je = reg.predict_error([[(p.x, p.y)]])[0]
                    oj = p.saved_j

                    p.j = float(j)
                    p.jerr = float(je)

                    p.dev = (oj - j) / j * 100

        if self.plotter_options.plot_kind == '2D':
            self._graph_contour(x, y, z, r, reg, refresh)
        else:
            self._graph_hole_vs_j(x, y, r, reg, refresh)

    def _graph_contour(self, x, y, z, r, reg, refresh):

        g = self.graph
        if not isinstance(g, ContourGraph):
            g = ContourGraph(container_dict={'kind': 'h',
                                             'bgcolor': self.plotter_options.bgcolor})
            self.graph = g
        else:
            g.clear()

        p = g.new_plot(xtitle='X', ytitle='Y')

        ito = IrradiationTrayOverlay(component=p,
                                     geometry=self.geometry,
                                     show_labels=self.show_labels)
        self.irradiation_tray_overlay = ito
        p.overlays.append(ito)

        m = self._model_flux(reg, r)
        s, p = g.new_series(z=m,
                            xbounds=(-r, r),
                            ybounds=(-r, r),
                            levels=self.levels,
                            cmap=self.color_map_name,
                            colorbar=True,
                            style='contour')
        g.add_colorbar(s)

        # pts = vstack((x, y)).T
        s = g.new_series(x, y,
                         z=z,
                         style='cmap_scatter',
                         color_mapper=s.color_mapper,
                         marker='circle',
                         marker_size=self.marker_size)
        self.cmap_scatter = s[0]

    def _graph_hole_vs_j(self, x, y, r, reg, refresh):

        sel = [i for i, a in enumerate(self.analyses) if a.is_omitted()]

        g = self.graph
        if not isinstance(g, Graph):
            g = Graph(container_dict={'bgcolor': self.plotter_options.bgcolor})
            self.graph = g

        po = self.plotter_options

        xs = arctan2(x, y)
        ys = reg.ys
        a = max((abs(min(xs)), abs(max(xs))))
        fxs = linspace(-a, a)

        a = r * sin(fxs)
        b = r * cos(fxs)
        pts = vstack((a, b)).T

        fys = reg.predict(pts)
        yserr = reg.yserr
        if not refresh:
            g.clear()
            p = g.new_plot(xtitle='Hole (Theta)',
                           ytitle='J',
                           # padding=[90, 5, 5, 40],
                           padding=po.paddings())
            p.bgcolor = po.plot_bgcolor

            p.y_axis.tick_label_formatter = lambda x: floatfmt(x, n=2, s=4, use_scientific=True)

            scatter, _ = g.new_series(xs, ys,
                                      yerror=yserr,
                                      type='scatter', marker='circle')

            ebo = ErrorBarOverlay(component=scatter,
                                  orientation='y')
            scatter.overlays.append(ebo)
            add_inspector(scatter)
            g.new_series(fxs, fys)

            # plot the individual analyses
            s, iys = self._graph_individual_analyses()
            s.index.metadata['selections'] = sel
            # s.index.metadata_changed = True

            ymi = min(ys.min(), min(iys))
            yma = min(ys.max(), max(iys))

            g.set_x_limits(-3.2, 3.2)
            g.set_y_limits(ymi, yma, pad='0.1')

        else:
            plot = g.plots[0]

            s1 = plot.plots['plot0'][0]
            s1.yerror.set_data(yserr)

            ebo = next((o for o in s1.overlays if isinstance(o, ErrorBarOverlay)), None)
            if ebo:
                ebo.invalidate()

            g.set_data(ys, plotid=0, series=0, axis=1)
            g.set_data(fys, plotid=0, series=1, axis=1)
            s2 = plot.plots['plot2'][0]

            s2.index.metadata['selections'] = sel
            # s2.index.metadata = {'selections': sel}
            # s2.index.metadata_changed = True

        self._model_sin_flux(fxs, fys)

    def _graph_individual_analyses(self):
        po = self.plotter_options
        g = self.graph

        ixs = []
        iys = []
        ans = []
        m, k = po.monitor_age * 1e6, po.lambda_k
        slope = True
        prev = self.monitor_positions[-1].j
        for j, p in enumerate(self.monitor_positions):
            if p.use:
                if prev:
                    slope = prev < p.j
                prev = p.j
                pp = arctan2(p.x, p.y)
                xx = linspace(pp - .1, pp + .1, len(p.analyses))
                ans.extend(p.analyses)
                ixs.extend(xx)

                yy = [nominal_value(a.model_j(m, k)) for a in p.analyses]

                yy = sorted(yy, reverse=not slope)

                iys.extend(yy)
        s, _p = g.new_series(ixs, iys, type='scatter', marker='circle', marker_size=1.5)
        add_analysis_inspector(s, ans)

        self.analyses = ans
        s.index.on_trait_change(self._update_graph_metadata, 'metadata_changed')
        return s, iys

    def _update_graph_metadata(self, obj, name, old, new):
        # print obj, name, old, new
        # print obj.metadata
        sel = self._filter_metadata_changes(obj, self._recalculate_means, self.analyses)

    def _recalculate_means(self, sel):
        # print sel
        # if sel:

        # pos = next((p for p in self.monitor_positions if p.identifier==sel[0].identifier), None)
        # if pos:
        #     pos.set_mean_j()
        identifier = None
        if sel:
            ai = self.analyses[sel[0]]
            identifier = ai.identifier

        for p in self.monitor_positions:
            if p.was_altered:
                p.set_mean_j()
                p.was_altered = False
            elif p.identifier == identifier:
                p.set_mean_j()
                p.was_altered = True

        self.predict_values(refresh=True)

    def _model_sin_flux(self, fxs, fys):
        self.max_j = fys.max()
        self.min_j = fys.min()

        # maidx = fys.argmax()
        # miidx = fys.argmin()

        # x1,y1 = fxs[maidx], fys[maidx]
        # x2,y2 = fxs[miidx], fys[miidx]
        # d = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        # self.j_gradient = self.percent_j_change / d

    def _model_flux(self, reg, r):

        n = reg.n * 10
        gx, gy = make_grid(r, n)

        nz = zeros((n, n))
        for i in xrange(n):
            pts = vstack((gx[i], gy[i])).T
            nz[i] = reg.predict(pts)

        self.max_j = nz.max()
        self.min_j = nz.min()

        # x1, y1 = unravel_index(nz.argmax(), nz.shape)
        # x2, y2 = unravel_index(nz.argmin(), nz.shape)
        #
        # d = 2 * r / n * ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        # self.j_gradient = self.percent_j_change / d

        return nz

    def _regressor_factory(self, x, y, z, ze):
        if self.plotter_options.model_kind == 'Bowl':
            # from pychron.core.regression.flux_regressor import BowlFluxRegressor
            klass = BowlFluxRegressor
        else:
            # from pychron.core.regression.flux_regressor import PlaneFluxRegressor
            klass = PlaneFluxRegressor

        x = array(x)
        y = array(y)
        xy = vstack((x, y)).T
        wf = self.plotter_options.use_weighted_fit
        if wf:
            ec = 'SD'
        else:
            ec = self.plotter_options.predicted_j_error_type

        reg = klass(xs=xy, ys=z, yserr=ze,
                    error_calc_type=ec,
                    use_weighted_fit=wf)
        # error_calc_type=self.tool.predicted_j_error_type)
        reg.calculate()
        return reg

    def traits_view(self):
        def column(klass=ObjectColumn, editable=False, **kw):
            return klass(text_font='arial 10', editable=editable, **kw)

        cols = [
            column(klass=CheckboxColumn, name='use', label='Use', editable=True, width=30),
            column(name='hole_id', label='Hole'),
            column(name='identifier', label='Identifier'),
            column(name='sample', label='Sample', width=115),

            # column(name='x', label='X', format='%0.3f', width=50),
            # column(name='y', label='Y', format='%0.3f', width=50),
            # column(name='theta', label=u'\u03b8', format='%0.3f', width=50),

            column(name='n', label='N'),
            column(name='saved_j', label='Saved J',
                   format_func=lambda x: floatfmt(x, n=6, s=4)),
            column(name='saved_jerr', label=u'\u00b1\u03c3',
                   format_func=lambda x: floatfmt(x, n=6, s=4)),
            column(name='percent_saved_error',
                   label='%',
                   format_func=lambda x: floatfmt(x, n=2)),
            column(name='mean_j', label='Mean J',
                   format_func=lambda x: floatfmt(x, n=6, s=4) if x else ''),
            column(name='mean_jerr', label=u'\u00b1\u03c3',
                   format_func=lambda x: floatfmt(x, n=6, s=4) if x else ''),
            column(name='percent_mean_error',
                   label='%',
                   format_func=lambda x: floatfmt(x, n=2) if x else ''),
            column(name='j', label='Pred. J',
                   format_func=lambda x: floatfmt(x, n=8, s=4),
                   width=75),
            column(name='jerr',
                   format_func=lambda x: floatfmt(x, n=10, s=4),
                   label=u'\u00b1\u03c3',
                   width=75),
            column(name='percent_pred_error',
                   label='%',
                   format_func=lambda x: floatfmt(x, n=2) if x else ''),
            column(name='dev', label='dev',
                   format='%0.2f',
                   width=70),
            column(klass=CheckboxColumn, name='save', label='Save', editable=True, width=30)]

        unk_cols = [column(klass=CheckboxColumn, name='use', label='Use', editable=True, width=30),
                    column(name='hole_id', label='Hole'),
                    column(name='identifier', label='Identifier'),
                    column(name='sample', label='Sample', width=115),
                    column(name='saved_j', label='Saved J',
                           format_func=lambda x: floatfmt(x, n=7, s=5)),
                    column(name='saved_jerr', label=u'\u00b1\u03c3',
                           format_func=lambda x: floatfmt(x, n=7, s=5)),
                    column(name='percent_saved_error',
                           label='%',
                           format_func=lambda x: floatfmt(x, n=2)),
                    column(name='j', label='Pred. J',
                           format_func=lambda x: floatfmt(x, n=8, s=5),
                           width=75),
                    column(name='jerr',
                           format_func=lambda x: floatfmt(x, n=10, s=5),
                           label=u'\u00b1\u03c3',
                           width=75),
                    column(name='percent_pred_error',
                           label='%',
                           format_func=lambda x: floatfmt(x, n=2) if x else ''),
                    column(name='dev', label='dev',
                           format='%0.2f',
                           width=70),
                    column(klass=CheckboxColumn, name='save', label='Save', editable=True, width=30)]
        mon_editor = TableEditor(columns=cols, sortable=False,
                                 reorderable=False)

        unk_editor = TableEditor(columns=unk_cols, sortable=False,
                                 reorderable=False)

        pgrp = VGroup(UItem('monitor_positions', editor=mon_editor),
                      UItem('unknown_positions', editor=unk_editor),
                      label='Tables')

        ggrp = UItem('graph', style='custom')
        tgrp = HGroup(UItem('recalculate_button'),
                      Item('min_j', format_str='%0.4e',
                           style='readonly',
                           label='Min. J'),
                      Item('max_j',
                           style='readonly',
                           format_str='%0.4e', label='Max. J'),
                      Item('percent_j_change',
                           style='readonly',
                           format_func=floatfmt,
                           label='Delta J(%)'),
                      # Item('j_gradient',
                      #      style='readonly',
                      #      format_func=floatfmt,
                      #      label='Gradient J(%/cm)'),
                      spring, icon_button_editor('save_unknowns_button', 'dialog-ok-5',
                                                 tooltip='Toggle "save" for unknown positions'),
                      icon_button_editor('save_all_button', 'dialog-ok-apply-5',
                                         tooltip='Toggle "save" for all positions'))
        # v = View(VGroup(ggrp, tgrp, pgrp))
        v = View(VGroup(tgrp, Tabbed(ggrp, pgrp)))
        return v

    def _get_percent_j_change(self):
        maj, mij = self.max_j, self.min_j
        try:
            return (maj - mij) / maj * 100
        except ZeroDivisionError:
            return 0

# ============= EOF =============================================
