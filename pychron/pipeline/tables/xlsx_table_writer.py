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
import os

import six
import xlsxwriter
from pyface.confirmation_dialog import confirm
from pyface.constant import YES
from traits.api import Instance
from uncertainties import nominal_value, std_dev, ufloat
from uncertainties.core import Variable

from pychron.core.helpers.filetools import add_extension, view_file
from pychron.core.helpers.formatting import floatfmt
from pychron.core.helpers.isotope_utils import sort_detectors
from pychron.paths import paths, r_mkdir
from pychron.pipeline.tables.base_table_writer import BaseTableWriter
from pychron.pipeline.tables.column import Column, EColumn, VColumn
from pychron.pipeline.tables.util import iso_value, icf_value, icf_error, correction_value, age_value, supreg, \
    subreg, interpolate_noteline, value
from pychron.pipeline.tables.xlsx_table_options import XLSXAnalysisTableWriterOptions
from pychron.processing.analyses.analysis_group import InterpretedAgeGroup
from pychron.pychron_constants import PLUSMINUS_NSIGMA, NULL_STR, DESCENDING, PLUSMINUS


def format_mswd(t):
    m, v, _ = t
    return 'MSWD={}{:0.3f}'.format('' if v else '*', m)


class XLSXAnalysisTableWriter(BaseTableWriter):
    _workbook = None
    _current_row = 0
    _bold = None
    _superscript = None
    _subscript = None
    _ital = None
    _options = Instance(XLSXAnalysisTableWriterOptions)

    def _new_workbook(self, path):
        self._workbook = xlsxwriter.Workbook(add_extension(path, '.xlsx'), {'nan_inf_to_errors': True})

    def build(self, groups, path=None, options=None):
        if options is None:
            options = XLSXAnalysisTableWriterOptions()

        self._options = options
        if path is None:
            path = options.path

        self.debug('saving table to {}'.format(path))
        r_mkdir(os.path.dirname(path))

        self._new_workbook(path)

        self._bold = self._workbook.add_format({'bold': True})
        self._superscript = self._workbook.add_format({'font_script': 1})
        self._subscript = self._workbook.add_format({'font_script': 2})
        self._ital = self._workbook.add_format({'italic': True})

        unknowns = groups.get('unknowns')
        if unknowns:
            # make a human optimized table
            unknowns = self._make_human_unknowns(unknowns)

            # make a machine optimized table
        munknowns = groups.get('machine_unknowns')
        if munknowns:
            self._make_machine_unknowns(munknowns)

        airs = groups.get('airs')
        if airs:
            self._make_airs(airs)

        blanks = groups.get('blanks')
        if blanks:
            self._make_blanks(blanks)

        monitors = groups.get('monitors')
        if monitors:
            self._make_monitors(monitors)

        # if not self._options.include_production_ratios:
        #     self._make_irradiations(unknowns)

        if self._options.include_summary_sheet:
            if unknowns:
                self._make_summary_sheet(unknowns)

        self._workbook.close()

        view = self._options.auto_view
        if not view:
            view = confirm(None, 'Table saved to {}\n\nView Table?'.format(path)) == YES

        if view:
            view_file(path, application='Excel')

    # private
    def _get_detectors(self, grps):
        def rec_dets(dets, a):
            if isinstance(a, InterpretedAgeGroup):
                for aa in a.analyses:
                    rec_dets(dets, aa)
            else:
                return dets.update({i.detector for i in a.isotopes.values()})

        d = set()
        for g in grps:
            for a in g.analyses:
                rec_dets(d, a)
        # detectors = {i.detector for g in grps
        #              for a in g.analyses
        #              for i in a.isotopes.values()}
        return sort_detectors(d)

    def _get_columns(self, name, grps):

        detectors = self._get_detectors(grps)

        options = self._options

        ubit = name in ('Unknowns', 'Monitor')
        bkbit = ubit and options.include_blanks
        ibit = options.include_intercepts

        kcabit = ubit and options.include_kca
        age_units = '({})'.format(options.age_units)
        age_func = age_value(options.age_units)

        columns = [Column(attr='status', width=2),
                   Column(label='N', attr='aliquot_step_str'),
                   Column(label='Tag', attr='tag'),
                   Column(enabled=ubit, label='Power', units=options.power_units, attr='extract_value'),
                   Column(enabled=ubit, label='Age', units=age_units, attr='age', func=age_func),
                   EColumn(enabled=ubit, units=age_units, attr='age_err_wo_j', func=age_func,
                           sigformat='age'),
                   VColumn(enabled=kcabit, label='K/Ca', attr='kca'),
                   EColumn(enabled=ubit, attr='kca'),
                   VColumn(enabled=ubit and options.include_percent_ar39,
                           label=('Cum. %', '<sup>39</sup>', 'Ar'),
                           units='(%)', attr='cumulative_ar39'),
                   VColumn(enabled=ubit and options.include_radiogenic_yield,
                           label=('%', '<sup>40</sup>', 'Ar'),
                           units='(%)', attr='rad40_percent'),
                   VColumn(enabled=ubit and options.include_F,
                           label=('<sup>40</sup>', 'Ar*/', '<sup>39</sup>', 'Ar', '<sub>K</sub>'),
                           attr='uF'),
                   VColumn(enabled=ubit and options.include_k2o,
                           label=('K', '<sub>2</sub>', 'O'),
                           sigformat='k2o',
                           units='(wt. %)', attr='display_k2o'),
                   VColumn(enabled=options.include_sensitivity,
                           label='Sensitivity',
                           units=options.sensitivity_units,
                           attr='sensitivity',
                           use_scientific=True,
                           sigformat='sens'),

                   VColumn(enabled=ubit and options.include_isochron_ratios,
                           label=('<sup>39</sup>', 'Ar/', '<sup>40</sup>', 'Ar'),
                           attr='isochron3940'),
                   VColumn(enabled=ubit and options.include_isochron_ratios,
                           label=('<sup>36</sup>', 'Ar/', '<sup>40</sup>', 'Ar'),
                           attr='isochron3640')]

        # setup formats
        sigfigs = ('age', 'kca', 'rad40_percent', 'cumulative_ar39', 'uF')
        for c in columns:
            if c.attr in sigfigs:
                c.sigformat = c.attr

        self._signal_columns(columns, ibit, bkbit)
        self._intercalibration_columns(columns, detectors)
        self._run_columns(columns, ubit)
        self._flux_columns(columns)

        if options.include_production_ratios:
            pr = self._get_irradiation_columns(ubit)
            columns.extend(pr)
        else:
            irr = [Column(enabled=ubit, label='Irradiation', attr='irradiation_label')]
            columns.extend(irr)

        for c in columns:
            if c.sigformat:
                try:
                    sg = getattr(options, '{}_sig_figs'.format(c.sigformat))
                except AttributeError:
                    sg = options.sig_figs

                c.nsigfigs = sg

        return columns

    def _flux_columns(self, columns):
        columns.extend([Column(enabled=False, label='LambdaK', attr='lambda_k', func=value),
                        Column(enabled=False, label='MonitorAge', attr='monitor_age'),
                        Column(enabled=False, label='MonitorName', attr='monitor_name'),
                        Column(enabled=False, label='MonitorMaterial', attr='monitor_material')])

    def _run_columns(self, columns, ubit):
        options = self._options

        # fmt = self._workbook.add_format()
        # datefmt = fmt.set_num_format('mm/dd/yy hh:mm')
        # dfmt = self._get_number_format('decay')

        columns.extend([Column(enabled=options.include_rundate,
                               label='RunDate', attr='rundate',
                               width=15,
                               fformat=[('set_num_format', ('mm/dd/yy hh:mm',))]),
                        Column(enabled=options.include_time_delta,
                               label=(u'\u0394t', '<sup>3</sup>'),
                               units='(days)',
                               attr='decay_days'),
                        VColumn(enabled=ubit, label='J', attr='j', sigformat='j'),
                        EColumn(enabled=ubit, attr='j'),
                        VColumn(enabled=ubit, label=('<sup>39</sup>', 'Ar Decay'),
                                attr='ar39decayfactor', sigformat='decay'),
                        VColumn(enabled=ubit, label=('<sup>37</sup>', 'Ar Decay'),
                                attr='ar37decayfactor', sigformat='decay')])

    def _intercalibration_columns(self, columns, detectors):
        disc = [VColumn(label='Disc', attr='discrimination', sigformat='disc'),
                EColumn(attr='discrimination', sigformat='disc')]
        columns.extend(disc)

        for det in detectors:
            tag = '{}_ic_factor'.format(det)
            columns.extend([Column(label=('IC', '<sup>{}</sup>'.format(det)), attr=tag, func=icf_value, sigformat='ic'),
                            EColumn(attr=tag, func=icf_error, sigformat='ic')])

    def _signal_columns(self, columns, ibit, bkbit):
        isos = (('Ar', 40), ('Ar', 39), ('Ar', 38), ('Ar', 37), ('Ar', 36))
        for bit, tag in ((True, 'disc_ic_corrected'), (ibit, 'intercept'), (bkbit, 'blank')):
            cols = [c for iso, mass in isos
                    for c in (Column(enabled=bit, attr='{}{}'.format(iso, mass),
                                     label=('<sup>{}</sup>'.format(mass), iso),
                                     units='(fA)',
                                     func=iso_value(tag),
                                     sigformat='signal'),
                              EColumn(enabled=bit,
                                      attr='{}{}'.format(iso, mass),
                                      func=iso_value(tag, ve='error'),
                                      sigformat='signal'))]
            columns.extend(cols)

    def _get_machine_columns(self, name, grps):
        options = self._options

        detectors = self._get_detectors(grps)

        ubit = name in ('Unknowns', 'Monitor')
        bkbit = ubit and options.include_blanks
        ibit = options.include_intercepts

        kcabit = ubit and options.include_kca
        age_units = '({})'.format(options.age_units)
        age_func = age_value(options.age_units)

        columns = [Column(attr='status'),
                   Column(label='Identifier', attr='identifier'),
                   Column(label='Sample', attr='sample'),
                   Column(label='Material', attr='material'),
                   Column(label='Project', attr='project'),
                   Column(label='Tag', attr='tag'),

                   Column(label='N', attr='aliquot_step_str'),
                   Column(enabled=ubit, label='Power',
                          units=options.power_units,
                          attr='extract_value'),

                   Column(enabled=ubit, label='Age', units=age_units, attr='age', func=age_func),
                   EColumn(enabled=ubit, units=age_units, attr='age_err_wo_j', func=age_func),
                   VColumn(enabled=kcabit, label='K/Ca', attr='kca'),
                   EColumn(enabled=ubit, attr='kca'),
                   VColumn(enabled=ubit and options.include_radiogenic_yield,
                           label=('%', '<sup>40</sup>', 'Ar'),
                           units='(%)', attr='rad40_percent'),
                   VColumn(enabled=ubit and options.include_F,
                           label=('<sup>40</sup>', 'Ar*/', '<sup>39</sup>', 'Ar', '<sub>K</sub>'),
                           attr='uF'),
                   VColumn(enabled=ubit and options.include_k2o,
                           label=('K', '<sub>2</sub>', 'O'),
                           units='(wt. %)',
                           attr='k2o'),
                   VColumn(enabled=options.include_sensitivity,
                           label='Sensitivity',
                           units=options.sensitivity_units,
                           attr='sensitivity'),
                   VColumn(enabled=ubit and options.include_isochron_ratios,
                           label=('<sup>39</sup>', 'Ar/', '<sup>40</sup>', 'Ar'),
                           attr='isochron3940'),
                   VColumn(enabled=ubit and options.include_isochron_ratios,
                           label=('<sup>36</sup>', 'Ar/', '<sup>40</sup>', 'Ar'),
                           attr='isochron3640')]

        self._signal_columns(columns, ibit, bkbit)
        self._intercalibration_columns(columns, detectors)
        self._run_columns(columns, ubit)

        if options.include_production_ratios:
            pr = self._get_irradiation_columns(ubit)
            columns.extend(pr)
        else:
            c = Column(enabled=ubit, label='Irradiation', attr='irradiation_label')
            columns.append(c)

        return columns

    def _get_irradiation_columns(self, ubit):
        fmt = 'correction'

        cols = [c for (ai, am), (bi, bm), e in ((('Ar', 40), ('Ar', 39), 'K'),
                                                (('Ar', 38), ('Ar', 39), 'K'),
                                                (('Ar', 37), ('Ar', 39), 'K'),

                                                (('Ar', 39), ('Ar', 37), 'Ca'),
                                                (('Ar', 38), ('Ar', 37), 'Ca'),
                                                (('Ar', 36), ('Ar', 37), 'Ca'),

                                                (('Ar', 36), ('Ar', 38), 'Cl'))
                for c in (Column(label=('(', '<sup>{}</sup>'.format(am),
                                        '{}/'.format(ai),
                                        '<sup>{}</sup>'.format(bm), '{})'.format(bm), '<sub>{}</sub>'.format(e)),
                                 attr='{}{}{}'.format(e, am, bm),
                                 sigformat=fmt),
                          EColumn(attr='{}{}{}'.format(e, am, bm),
                                  sigformat=fmt))]

        cols.extend([Column(label='Ca/K', attr='Ca_K', sigformat=fmt),
                     EColumn(attr='Ca_K', sigformat=fmt),
                     Column(label='Cl/K ', attr='Cl_K', sigformat=fmt),
                     EColumn(attr='Cl_K', sigformat=fmt)])

        for c in cols:
            c.enabled = ubit
            if isinstance(c, EColumn):
                c.func = correction_value(ve='error')
            else:
                c.func = correction_value()

        return cols

    def _get_summary_columns(self):
        opt = self._options

        def get_kca(ag, *args):
            pv = ag.get_preferred_obj('kca')
            return pv.value

        def get_kca_error(ag, *args):
            pv = ag.get_preferred_obj('kca')
            return pv.error * opt.summary_kca_nsigma
            # return std_dev(ag.get_weighted_mean('kca')) * opt.summary_kca_nsigma

        def get_preferred_age_kind(ag, *args):
            pv = ag.get_preferred_obj('age')
            # _, label = ag.get_age()
            # ret = label.capitalize()
            return pv.computed_kind.capitalize()

        def get_preferred_age(ag, *args):
            pv = ag.get_preferred_obj('age')
            # a, _ = ag.get_age()
            return pv.value

        def get_preferred_age_error(ag, *args):
            pv = ag.get_preferred_obj('age')
            # a, _ = ag.get_age()
            return pv.error * opt.summary_age_nsigma

        age_units = '({})'.format(opt.age_units)

        cols = [Column(enabled=opt.include_summary_sample, label='Sample', attr='sample'),
                Column(enabled=opt.include_summary_identifier, label='Identifier', attr='identifier'),
                Column(enabled=opt.include_summary_unit, label='Unit', attr='unit'),
                Column(enabled=opt.include_summary_location, label='Location', attr='location'),
                Column(enabled=opt.include_summary_irradiation, label='Irradiation', attr='irradiation_label'),
                Column(enabled=opt.include_summary_material, label='Material', attr='material'),

                Column(enabled=opt.include_summary_age, label='Age Type', func=get_preferred_age_kind),

                Column(enabled=opt.include_summary_n, label='N', attr='nratio'),
                Column(enabled=opt.include_summary_percent_ar39, label=('%', '<sup>39</sup>', 'Ar'),
                       attr='percent_39Ar'),
                Column(enabled=opt.include_summary_mswd, label='MSWD', attr='mswd'),
                Column(enabled=opt.include_summary_kca, label='K/Ca', attr='weighted_kca', func=get_kca),

                Column(enabled=opt.include_summary_kca,
                       label=PLUSMINUS_NSIGMA.format(opt.summary_kca_nsigma),
                       attr='weighted_kca',
                       func=get_kca_error),

                Column(enabled=opt.include_summary_age,
                       label='Age {}'.format(age_units),
                       func=get_preferred_age),

                Column(enabled=opt.include_summary_age,
                       label=PLUSMINUS_NSIGMA.format(opt.summary_age_nsigma),
                       func=get_preferred_age_error),

                Column(enabled=opt.include_summary_comments, label='Comments', attr='comments'),

                # Hidden Cols
                VColumn(label='WeightedMeanAge', attr='weighted_age'),
                EColumn(attr='weighted_age'),
                VColumn(label='ArithmeticMeanAge', attr='arith_age'),
                EColumn(attr='arith_age'),
                VColumn(label='IsochronAge', attr='isochron_age'),
                EColumn(attr='isochron_age'),
                VColumn(label='PlateauAge', attr='plateau_age'),
                VColumn(attr='plateau_age'),
                VColumn(label='IntegratedAge', attr='integrated_age'),
                VColumn(attr='integrated_age')]

        return cols

    def _make_human_unknowns(self, unks):
        return self._make_sheet(unks, 'Unknowns')

    def _make_machine_unknowns(self, unks):
        self._make_machine_sheet(unks, 'Unknowns (Machine)')

    def _make_airs(self, airs):
        self._make_sheet(airs, 'Airs')

    def _make_blanks(self, blanks):
        self._make_sheet(blanks, 'Blanks')

    def _make_monitors(self, monitors):
        self._make_sheet(monitors, 'Monitors')

    def _make_summary_sheet(self, unks):
        self._current_row = 1
        sh = self._workbook.add_worksheet('Summary')
        self._format_generic_worksheet(sh)

        cols = self._get_summary_columns()
        cols = [c for c in cols if c.enabled]
        self._make_title(sh, 'Summary', cols)

        fmt = self._workbook.add_format({'bottom': 1, 'align': 'center'})
        sh.set_row(self._current_row, 5)
        self._current_row += 1

        idx = next((i for i, c in enumerate(cols) if c.label == 'Age Type'), 6)
        idx_e = next((i for i, c in enumerate(cols) if c.label == 'Age'), 12) + 1
        # sh.write_rich_string(self._current_row, idx, 'Preferred Age', border)
        sh.merge_range(self._current_row, idx, self._current_row, idx_e, 'Preferred Age', cell_format=fmt)

        # hide extra age columns
        for hidden in ('WeightedMeanAge', 'ArithmeticMeanAge', 'IsochronAge', 'PlateauAge', 'IntegratedAge'):
            hc = next((i for i, c in enumerate(cols) if c.label == hidden), None)
            if hc is not None:
                sh.set_column(hc, hc + 1, options={'hidden': True})

        self._current_row += 1
        sh.set_row(self._current_row, 5)
        self._current_row += 1
        self._write_header(sh, cols, include_units=False)
        center = self._workbook.add_format({'align': 'center'})
        for ug in unks:
            ug.set_temporary_age_units(self._options.age_units)
            for i, ci in enumerate(cols):
                txt = self._get_txt(ug, ci)
                sh.write(self._current_row, i, txt, center)
            self._current_row += 1
            ug.set_temporary_age_units(None)

        self._make_notes(None, sh, len(cols), 'summary')

    def _sort_groups(self, groups):
        # def group_age(group):
        #     nitems = []
        #     has_subgroups = False
        #
        #     ans = group.analyses
        #
        #     nsubgroups = len({subgrouping_key(i) for i in ans})
        #
        #     for subgroup, items in groupby(ans, key=subgrouping_key):
        #         items = list(items)
        #         ag = None
        #         if subgroup:
        #             sg = items[0].subgroup
        #             kind = sg['age_kind']
        #             ag = InterpretedAgeGroup(analyses=items)
        #             _, label = ag.get_age(kind, set_preferred=True)
        #             ag.set_preferred_kinds(sg)
        #         if ag:
        #             nitems.append(ag)
        #             has_subgroups = True
        #         else:
        #             if nsubgroups == 1:
        #                 ag = InterpretedAgeGroup(analyses=items)
        #                 ag.set_preferred_kinds()
        #                 nitems = [ag]
        #             else:
        #                 nitems.extend(items)
        #
        #     if has_subgroups and nsubgroups > 1:
        #         group.analyses = nitems
        #
        #     if nsubgroups == 1:
        #         group = nitems[0]
        #
        #     return group.age
        def group_age(g):
            return 0

        if self._options.group_age_sorting == NULL_STR:
            ngs = groups
        else:
            ngs = sorted(groups, key=group_age, reverse=self._options.group_age_sorting == DESCENDING)

        return ngs

    def _make_sheet(self, groups, name):
        self._current_row = 1

        worksheet = self._workbook.add_worksheet(name)

        cols = self._get_columns(name, groups)
        self._format_worksheet(worksheet, cols, (8, 2))

        self._make_title(worksheet, name, cols)

        options = self._options
        repeat_header = options.repeat_header

        groups = self._sort_groups(groups)
        ngroups = []
        for i, group in enumerate(groups):
            ans = group.analyses
            n = len(ans)
            if not n:
                continue

            group.set_j_error(options.include_j_position_error, options.include_j_error_in_mean)
            group.set_temporary_age_units(options.age_units)
            self._make_meta(worksheet, group)
            if repeat_header or i == 0:
                self._make_column_header(worksheet, cols, i)

            nsubgroups = len([a for a in ans if isinstance(a, InterpretedAgeGroup)])

            for j, a in enumerate(ans):
                if isinstance(a, InterpretedAgeGroup):
                    items = a.analyses

                    pv = a.get_preferred_obj('age')
                    label = pv.computed_kind.lower()

                    for ii, item in enumerate(items):
                        # ounits = item.arar_constants.age_units

                        is_plateau_step = None
                        if label == 'plateau':
                            is_plateau_step = a.get_is_plateau_step(ii)

                        self._make_analysis(worksheet, cols, item,
                                            is_last=False,
                                            is_plateau_step=is_plateau_step,
                                            cum=a.cumulative_ar39(ii) if a else '')

                    self._make_intermediate_summary(worksheet, a, cols, label)
                    self._current_row += 1
                else:
                    pv = group.get_preferred_obj('age')
                    label = pv.computed_kind.lower()
                    is_plateau_step = None
                    if label == 'plateau':
                        is_plateau_step = group.get_is_plateau_step(j)
                    self._make_analysis(worksheet, cols, a, is_last=j == n - 1, is_plateau_step=is_plateau_step)

            if nsubgroups == 1 and isinstance(a, InterpretedAgeGroup):
                ngroups.append(a)
                self._make_summary(worksheet, cols, a)
            else:
                ngroups.append(group)
                self._make_summary(worksheet, cols, group)

            self._current_row += 1
            group.set_temporary_age_units(None)

        self._make_notes(groups, worksheet, len(cols), name)
        self._current_row = 1

        for i, c in enumerate(cols):
            w = c.width
            if w is None:
                w = c.calculated_width
            if w > 0:
                worksheet.set_column(i, i, w)

        self._hide_columns(worksheet, cols)
        return ngroups

    def _make_machine_sheet(self, groups, name):
        self._current_row = 1
        worksheet = self._workbook.add_worksheet(name)

        cols = self._get_machine_columns(name, groups)
        self._format_worksheet(worksheet, cols, (5, 2))

        self._make_title(worksheet, name, cols)

        repeat_header = self._options.repeat_header

        for i, group in enumerate(groups):
            if repeat_header or i == 0:
                self._make_column_header(worksheet, cols, i)

            n = len(group.analyses) - 1
            for i, item in enumerate(group.analyses):
                self._make_analysis(worksheet, cols, item, is_last=i == n)
            self._current_row += 1

        self._current_row = 1

    def _format_generic_worksheet(self, sh):
        if self._options.hide_gridlines:
            sh.hide_gridlines(2)

    def _format_worksheet(self, sh, cols, freeze):
        self._format_generic_worksheet(sh)
        if not self._options.repeat_header:
            sh.freeze_panes(*freeze)

    def _hide_columns(self, sh, cols):
        for i, c in enumerate(cols):
            if not c.enabled:
                sh.set_column(i, i, options={'hidden': True})

    def _make_title(self, sh, name, cols):
        try:
            title = getattr(self._options, '{}_title'.format(name.lower()[:-1]))
        except AttributeError:
            title = None

        fmt = self._workbook.add_format({'font_size': 14, 'bold': True,
                                         'bottom': 6 if not title else 0})

        sh.write_string(self._current_row, 0, 'Table X. {}'.format(name), fmt)
        if title:
            self._current_row += 1
            sh.write_string(self._current_row, 0, title)

        for i in range(1, len(cols)):
            sh.write_blank(self._current_row, i, '', cell_format=fmt)
        self._current_row += 1

    def _make_column_header(self, sh, cols, it):

        start = next((i for i, c in enumerate(cols) if c.attr == 'Ar40'), 9)

        if self._options.repeat_header and it > 0:
            sh.write(self._current_row, start, 'Corrected')
            sh.write(self._current_row, start + 10, 'Intercepts')
        else:
            sh.write_rich_string(self._current_row, start, 'Corrected', self._superscript, '1')
            sh.write_rich_string(self._current_row, start + 10, 'Intercepts', self._superscript, '2')

        sh.write(self._current_row, start + 20, 'Blanks')
        self._current_row += 1
        self._write_header(sh, cols)

    def _write_header(self, sh, cols, include_units=True):
        names, units = self._get_names_units(cols)

        border = self._workbook.add_format({'bottom': 2, 'align': 'center'})
        center = self._workbook.add_format({'align': 'center'})
        if include_units:
            t = ((names, False), (units, True))
        else:
            t = ((names, True),)

        for items, use_border in t:
            row = self._current_row
            for i, ci in enumerate(items):
                if isinstance(ci, tuple):
                    args = []
                    for cii in ci:
                        for reg, fmt in ((supreg, self._superscript),
                                         (subreg, self._subscript)):
                            m = reg.match(cii)
                            if m:
                                args.append(fmt),
                                args.append(m.group('item'))
                                break
                        else:
                            args.append(cii)

                    if not use_border:
                        args.append(center)
                    else:
                        args.append(border)

                    # sh.write_rich_string(row, i, *args)
                    try:
                        sh.write_string(row, i, *args)
                    except TypeError:
                        sh.write_rich_string(row, i, *args)

                else:
                    if use_border:
                        # border.set_align('center')
                        sh.write_string(row, i, ci, border)
                    else:
                        sh.write_string(row, i, ci, center)
            self._current_row += 1

    def _make_meta(self, sh, group):
        fmt = self._bold
        row = self._current_row
        sh.write_string(row, 1, 'Sample:', fmt)
        sh.write_string(row, 2, group.sample, fmt)

        sh.write_string(row, 5, 'Identifier:', fmt)
        sh.write_string(row, 6, group.identifier, fmt)

        self._current_row += 1

        row = self._current_row
        sh.write_string(row, 1, 'Material:', fmt)
        sh.write_string(row, 2, group.material, fmt)

        self._current_row += 1

    def _make_intermediate_summary(self, sh, ag, cols, label):
        row = self._current_row

        age_idx = next((i for i, c in enumerate(cols) if c.label == 'Age'), 0)
        cum_idx = next((i for i, c in enumerate(cols) if c.attr == 'cumulative_ar39'), 0)

        fmt = self._get_number_format('summary_age')
        kcafmt = self._get_number_format('summary_kca')

        fmt.set_bottom(1)
        kcafmt.set_bottom(1)

        fmt2 = self._workbook.add_format({'bottom': 1, 'bold': True})
        border = self._workbook.add_format({'bottom': 1})

        for i in range(age_idx + 1):
            sh.write_blank(row, i, '', fmt)

        startcol = 1
        sh.write(row, startcol, '{:02n}'.format(ag.aliquot), fmt2)
        sh.write_string(row, startcol + 1, label, fmt2)
        cols[startcol + 1].calculate_width(label)

        age = ag.uage
        tn = ag.total_n
        if label == 'plateau':
            if not ag.plateau_steps:
                age = None
            else:
                txt = 'n={}/{} steps={}'.format(ag.nsteps, tn, ag.plateau_steps_str)
                sh.write(row, startcol + 2, txt, border)
                sh.write(row, cum_idx + 1, format_mswd(ag.get_plateau_mswd_tuple()), border)

        else:
            txt = 'n={}/{}'.format(ag.nanalyses, tn)
            sh.write(row, startcol + 2, txt, border)
            sh.write(row, cum_idx + 1, format_mswd(ag.get_mswd_tuple()), border)

        if age is not None:
            sh.write_number(row, age_idx, nominal_value(age), fmt)
            sh.write_number(row, age_idx + 1, std_dev(age), fmt)
        else:
            sh.write(row, age_idx, 'No plateau', border)

        sh.write_number(row, age_idx + 2, nominal_value(ag.kca), kcafmt)
        sh.write_number(row, age_idx + 3, std_dev(ag.kca), kcafmt)

        if label == 'plateau':
            sh.write_number(row, cum_idx, ag.plateau_total_ar39(), fmt)
        else:
            sh.write_number(row, cum_idx, ag.valid_total_ar39(), fmt)
        self._current_row += 1

    def _get_number_format(self, kind=None, use_scientific=False):
        try:
            sf = getattr(self._options, '{}_sig_figs'.format(kind))
        except AttributeError as e:
            sf = self._options.sig_figs

        fn = self._workbook.add_format()
        if use_scientific:
            fmt = '0.0E+00'
        else:
            fmt = '0.{}'.format('0' * sf)

        if not self._options.ensure_trailing_zeros:
            fmt = '{}#'.format(fmt)

        fn.set_num_format(fmt)
        return fn

    def _make_analysis(self, sh, cols, item, is_last=False, is_plateau_step=None, cum=''):
        item.arar_constants.age_units = self._options.age_units

        row = self._current_row

        fmt = self._workbook.add_format()

        status = 'X' if item.is_omitted() else ''
        highlight_color = self._options.highlight_color.name()
        if is_plateau_step is False:
            fmt.set_bg_color(highlight_color)
            sh.set_row(0, -1, fmt)
            if not status:
                status = 'pX'

        sh.write(row, 0, status, fmt)
        for j, c in enumerate(cols[1:]):
            cfmt = self._get_fmt(item, c)
            if c.attr == 'cumulative_ar39':
                txt = cum
            else:
                txt = self._get_txt(item, c)

            if cfmt:
                if is_plateau_step is False:
                    cfmt.set_bg_color(highlight_color)
            else:
                cfmt = fmt

            if is_last:
                cfmt.set_bottom(1)

            if c.label in ('N', 'Power'):
                sh.write(row, j + 1, txt, cfmt)
            elif c.label == 'RunDate':
                sh.write_datetime(row, j + 1, txt, cfmt)
            else:
                # self.debug('writing {} attr={} label={}'.format(type(txt), c.attr, c.label))
                if isinstance(txt, float):
                    sh.write_number(row, j + 1, txt, cell_format=cfmt)
                else:
                    sh.write(row, j + 1, txt, fmt)

            c.calculate_width(txt)
        self._current_row += 1

    def _make_summary(self, sh, cols, group):
        fmt = self._bold
        start_col = 0
        if self._options.include_kca:
            nfmt = self._get_number_format('summary_kca')
            nfmt.set_bold(True)
            idx = next((i for i, c in enumerate(cols) if c.label == 'K/Ca'))

            nsigma = self._options.asummary_kca_nsigma
            pmsigma = PLUSMINUS_NSIGMA.format(nsigma)
            pv = group.get_preferred_obj('kca')

            kind = pv.kind
            if 'integrated' in kind.lower():
                label = 'Integrated'
            else:
                label = kind.capitalize()

            sh.write_string(self._current_row, start_col,
                            u'{} K/Ca {}'.format(label, pmsigma),
                            fmt)

            sh.write_number(self._current_row, idx, pv.value, nfmt)
            sh.write_number(self._current_row, idx + 1, pv.error * nsigma, nfmt)
            sh.write_string(self._current_row, idx + 2, pv.error_kind, fmt)
            self._current_row += 1

        nfmt = self._get_number_format('summary_age')
        nfmt.set_bold(True)

        idx = next((i for i, c in enumerate(cols) if c.label == 'Age'))

        k2o_idx, k2o_col = next((c for c in enumerate(cols) if c[1].attr == 'display_k2o'))
        nsigma = self._options.asummary_age_nsigma
        pmsigma = PLUSMINUS_NSIGMA.format(nsigma)

        # a, label = group.get_age()
        # label = label.capitalize()
        age = group.get_preferred_obj('age')

        sh.write_string(self._current_row, start_col, u'{} Age {}'.format(age.computed_kind.capitalize(), pmsigma),
                        fmt)
        sh.write_number(self._current_row, idx, age.value, nfmt)
        sh.write_number(self._current_row, idx + 1, age.error * nsigma, nfmt)

        sh.write_string(self._current_row, idx + 2, 'n={}/{}'.format(group.nanalyses,
                                                                     group.total_n), fmt)

        mt = group.get_preferred_mswd_tuple()
        sh.write_string(self._current_row, idx + 3, format_mswd(mt), fmt)

        if age.computed_kind == 'Plateau':
            if self._options.include_plateau_age and hasattr(group, 'plateau_age'):
                sh.write(self._current_row, idx + 4, 'steps {}'.format(group.plateau_steps_str), fmt)

                self._current_row += 1

        else:
            self._current_row += 1

        if self._options.include_integrated_age and group.integrated_enabled:
            sh.write_string(self._current_row, start_col, u'Total Integrated Age {}'.format(pmsigma), fmt)
            sh.write_number(self._current_row, idx, nominal_value(group.integrated_age), nfmt)
            sh.write_number(self._current_row, idx + 1, std_dev(group.integrated_age) * nsigma, nfmt)

            # write total k2o
            v = floatfmt(nominal_value(group.total_k2o), k2o_col.nsigfigs)
            sh.write_rich_string(self._current_row, k2o_idx, 'K', self._subscript, '2', 'O wt. %={}'.format(v), fmt)

            self._current_row += 1

        if self._options.include_isochron_age:
            sh.write_string(self._current_row, start_col, u'Isochron Age {}'.format(pmsigma),
                            fmt)
            iage = group.isochron_age
            sh.write_number(self._current_row, idx, nominal_value(iage), nfmt)
            sh.write_number(self._current_row, idx + 1, std_dev(iage) * nsigma, nfmt)

            mt = group.isochron_mswd()
            try:
                trapped = 1 / group.isochron_4036
                trapped_value, trapped_error = nominal_value(trapped), std_dev(trapped)
            except ZeroDivisionError:
                trapped_value, trapped_error = 'NaN', 'NaN'

            sh.write_string(self._current_row, idx + 3, format_mswd(mt), fmt)
            sh.write_rich_string(self._current_row, idx + 4,
                                 '(', self._superscript, '40',
                                 'Ar/',
                                 self._superscript, '36', 'Ar', ')', self._subscript, 'trapped',
                                 '={:0.3f}{}{:0.3f}'.format(trapped_value, PLUSMINUS, trapped_error), fmt)
            self._current_row += 1

    def _make_notes(self, groups, sh, ncols, name):
        top = self._workbook.add_format({'top': 1, 'bold': True})

        sh.write_string(self._current_row, 0, 'Notes:', top)
        for i in range(1, ncols):
            sh.write_blank(self._current_row, i, '', cell_format=top)
        self._current_row += 1

        func = getattr(self, '_make_{}_notes'.format(name.lower()))
        func(groups, sh)

        for i in range(0, ncols):
            sh.write_blank(self._current_row, i, '', cell_format=top)

    def _make_summary_notes(self, groups, sh):
        notes = six.text_type(self._options.summary_notes)
        self._write_notes(sh, notes)
        # sh.write(self._current_row, 0, 'Plateau Criteria:')
        # self._current_row += 1
        #
        # sh.write(self._current_row, 0, '\t\tN Steps= {}'.format(self._options.plateau_nsteps))
        # self._current_row += 1
        #
        # sh.write(self._current_row, 0, '\t\tGas Fraction= {}'.format(self._options.plateau_gas_fraction))
        # self._current_row += 1
        # if self._options.fixed_step_low or self._options.fixed_step_high:
        #     sh.write(self._current_row, 0, '\t\tFixed Steps= {},{}'.format(self._options.fixed_step_low,
        #                                                                    self.fixed_step_high))
        #     self._current_row += 1

    def _make_unknowns_notes(self, groups, sh):

        g = groups[0]
        monitor_age, decay_ref = g.monitor_info

        if monitor_age is None:
            monitor_age = '<PLACEHOLDER'
        if decay_ref is None:
            decay_ref = '<PLACEHOLDER>'

        opt = self._options
        notes = opt.unknown_notes

        corrected_note = opt.unknown_corrected_note
        intercept_note = opt.unknown_intercept_note
        time_note = opt.unknown_time_note
        x_note = opt.unknown_x_note
        px_note = opt.unknown_px_note

        notes = notes.format(monitor_age=monitor_age, decay_ref=decay_ref)

        sh.write_rich_string(self._current_row, 0, self._superscript, '1', corrected_note)
        self._current_row += 1
        sh.write_rich_string(self._current_row, 0, self._superscript, '2', intercept_note)
        self._current_row += 1
        sh.write_rich_string(self._current_row, 0, self._superscript, '3', time_note)
        self._current_row += 1

        sh.write(self._current_row, 0, x_note)
        self._current_row += 1

        sh.write(self._current_row, 0, px_note)
        self._current_row += 1

        self._write_notes(sh, notes)

    def _make_blanks_notes(self, sh):
        notes = six.text_type(self._options.blank_notes)
        self._write_notes(sh, notes)

    def _make_airs_notes(self, sh):
        notes = six.text_type(self._options.air_notes)
        self._write_notes(sh, notes)

    def _make_monitor_notes(self, sh):
        notes = six.text_type(self._options.monitor_notes)
        self._write_notes(sh, notes)

    def _write_notes(self, sh, notes):
        for line in notes.splitlines():
            line = interpolate_noteline(line, self._superscript, self._subscript,
                                        self._ital, self._bold)
            try:
                sh.write_string(self._current_row, 0, *line)
            except TypeError:
                sh.write_rich_string(self._current_row, 0, *line)

            self._current_row += 1

    def _get_names_units(self, cols):
        names = [c.label for c in cols]
        units = [c.units for c in cols]
        return names, units

    def _get_fmt(self, item, col):
        fmt = None
        if col.sigformat:
            fmt = self._get_number_format(col.sigformat, col.use_scientific)

        elif col.fformat:
            fmt = self._workbook.add_format()
            for cmd, args in col.fformat:
                getattr(fmt, cmd)(*args)

        return fmt

    def _get_txt(self, item, col):
        attr = col.attr
        if attr is None:
            return ''

        func = col.func
        if func is None:
            func = getattr
        v = func(item, attr)
        if isinstance(v, Variable):
            v = nominal_value(v)
        return v


if __name__ == '__main__':
    x = XLSXAnalysisTableWriter()

    from random import random
    from datetime import datetime


    def frand(digits, scalar=1):
        return round(scalar * random(), digits)


    class Iso:
        def __init__(self, name):
            self.name = name
            self.uvalue = ufloat(frand(10, 10), frand(10))
            self.blank = Blank(name)
            self.detector = 'CDD'

        def get_intensity(self):
            return ufloat(frand(10, 10), frand(10))


    class Blank:
        def __init__(self, name):
            self.name = name
            self.uvalue = ufloat(frand(10, 1), frand(10))

        def get_intensity(self):
            return ufloat(frand(10, 1), frand(10))


    class AC:
        age_units = 'Ma'
        ma_age_scalar = 1


    class A:
        def is_omitted(self):
            return False

        def __init__(self, a):
            self.identifier = 'Foo'
            self.project = 'Bar'
            self.material = 'Moo'
            self.sample = 'Bat'
            self.aliquot_step_str = a
            self.isotopes = {'Ar40': Iso('Ar40'),
                             'Ar39': Iso('Ar39'),
                             'Ar38': Iso('Ar38'),
                             'Ar37': Iso('Ar37'),
                             'Ar36': Iso('Ar36')}
            self.arar_constants = AC()
            self.tag = 'ok'
            self.aliquot_step_str = '01'
            self.extract_value = frand(1)
            self.kca = ufloat(frand(2), frand(2))
            self.age = frand(10, 10)
            self.age_err_wo_j = frand(10)
            self.discrimination = 0
            self.j = 0

            self.ar39decayfactor = 0
            self.ar37decayfactor = 0
            self.interference_corrections = {}
            self.production_ratios = {'Ca_K': 1.312}
            self.uF = ufloat(frand(10, 10), frand(10))
            self.rad40_percent = frand(3, 100)
            self.rundate = datetime.now()
            self.decay_days = frand(2, 200)
            self.k2o = frand(2)
            self.irradiation_label = 'NM-284 E9o'
            self.irradiation = 'NM-284'
            self.isochron3940 = ufloat(frand(10), frand(10))
            self.isochron3640 = ufloat(frand(10), frand(10))

        def get_ic_factor(self, det):
            return 1
            # def __getattr__(self, item):
            #     return 0


    class G:
        sample = 'MB-1234'
        material = 'Groundmass'
        identifier = '13234'
        analyses = [A('01'), A('02')]
        arith_age = 132
        weighted_age = 10.01
        plateau_age = 123
        integrated_age = 1231
        plateau_steps_str = 'A-F'
        isochron_age = 123323
        weighted_kca = 1412
        arith_kca = 0.123
        preferred_age = 1213.123
        unit = ''
        location = ''
        mswd = frand(10)
        irradiation_label = 'Foo'
        preferred_age_kind = 'Plateau'
        nanalyses = 2
        percent_39Ar = 0.1234
        total_n = 2
        comments = ''

        def set_temporary_age_units(self, *args):
            pass


    g = G()
    p = '/Users/ross/Sandbox/testtable.xlsx'
    paths.build('_dev')
    options = XLSXAnalysisTableWriterOptions()
    options.configure_traits()
    x.build(groups={'unknowns': [g, g],
                    'machine_unknowns': [g, g]},
            path=p, options=options)
    options.dump()
    # app_path = '/Applications/Microsoft Office 2011/Microsoft Excel.app'
    #
    # try:
    #     subprocess.call(['open', '-a', app_path, p])
    # except OSError:
    #     subprocess.call(['open', p])
# ============= EOF =============================================
