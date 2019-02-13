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
from traits.api import Str, Instance
from traitsui.api import Item
from traitsui.editors import DirectoryEditor
from uncertainties import ufloat

from pychron.core.confirmation import confirmation_dialog
from pychron.core.helpers.filetools import unique_path2
from pychron.core.progress import progress_iterator, progress_loader
from pychron.paths import paths
from pychron.pipeline.editors.set_ia_editor import SetInterpretedAgeEditor
from pychron.pipeline.nodes.base import BaseNode
from pychron.pipeline.nodes.data import BaseDVCNode
from pychron.pipeline.tables.xlsx_table_options import XLSXAnalysisTableWriterOptions
from pychron.pipeline.tables.xlsx_table_writer import XLSXAnalysisTableWriter


class PersistNode(BaseDVCNode):
    def configure(self, **kw):
        return True


class FileNode(PersistNode):
    root = Str
    extension = ''


class PDFNode(FileNode):
    extension = '.pdf'


class PDFFigureNode(PDFNode):
    name = 'PDF Figure'

    def configure(self, **kw):
        return BaseNode.configure(self, **kw)

    def traits_view(self):

        return self._view_factory(Item('root', editor=DirectoryEditor(root_path=paths.data_dir)),
                                  width=500)

    def _generate_path(self, ei):
        name = ei.name.replace(' ', '_')

        p, _ = unique_path2(self.root, name, extension=self.extension)
        return p

    def run(self, state):
        for ei in state.editors:
            if hasattr(ei, 'save_file'):
                print('save file to', self._generate_path(ei))
                ei.save_file(self._generate_path(ei))


class DVCPersistNode(PersistNode):
    dvc = Instance('pychron.dvc.dvc.DVC')
    commit_message = Str
    commit_tag = Str
    modifier = Str

    # def __init__(self, *args, **kwargs):
    #     super(DVCPersistNode, self).__init__(*args, **kwargs)

    def _persist(self, state, msg):
        mods = self.modifier
        if not isinstance(mods, tuple):
            mods = (self.modifier,)

        modp = []
        for mi in mods:
            modpi = self.dvc.update_analyses(state.unknowns,
                                             mi, '<{}> {}'.format(self.commit_tag, msg))
            modp.extend(modpi)

        if modp:
            state.modified = True
            for m in modp:
                state.modified_projects = state.modified_projects.union(m)


class DefineEquilibrationPersistNode(DVCPersistNode):
    name = 'Save Equilibration'

    def run(self, state):
        if not state.saveable_keys:
            return

        def wrapper(x, prog, i, n):
            return self._save_eq(x, prog, i, n, state.saveable_keys)

        msg = ','.join('{}({})'.format(*a) for a in zip(state.saveable_keys, state.saveable_fits))
        items = progress_loader(state.unknowns, wrapper, threshold=1, unpack=False)
        modpis = self.dvc.update_analysis_paths(items, '<DEFINE EQUIL> {}'.format(msg))
        modpps = self.dvc.update_analyses(state.unknowns, 'intercepts', '<ISOEVO> modified by DEFINE EQUIL')
        modpis.extend(modpps)

        if modpis:
            state.modified = True
            state.modified_projects = state.modified_projects.union(modpis)

    def _save_eq(self, x, prog, i, n, keys):
        if prog:
            prog.change_message('Save Equilibration {} {}/{}'.format(x.record_id, i, n))

        path = self.dvc.save_defined_equilibration(x, keys)
        self.dvc.save_fits(x, keys)
        return x, path


class IsotopeEvolutionPersistNode(DVCPersistNode):
    name = 'Save Iso Evo'
    commit_tag = 'ISOEVO'
    modifier = ('intercepts', 'baselines')

    def run(self, state):
        if not state.saveable_keys:
            return

        def wrapper(x, prog, i, n):
            self._save_fit(x, prog, i, n, state.saveable_keys)

        progress_iterator(state.unknowns, wrapper, threshold=1)

        msg = self.commit_message
        if not msg:
            f = ','.join('{}({})'.format(x, y) for x, y in zip(state.saveable_keys, state.saveable_fits))
            msg = 'fits={}'.format(f)

        self._persist(state, msg)

    def _save_fit(self, x, prog, i, n, keys):
        if prog:
            prog.change_message('Save Fits {} {}/{}'.format(x.record_id, i, n))

        self.dvc.save_fits(x, keys)


class BlanksPersistNode(DVCPersistNode):
    name = 'Save Blanks'
    commit_tag = 'BLANKS'
    modifier = 'blanks'

    def run(self, state):
        # if not state.user_review:
        # for ai in state.unknowns:
        #     self.dvc.save_blanks(ai, state.saveable_keys, state.references)
        wrapper = lambda x, prog, i, n: self._save_blanks(x, prog, i, n,
                                                          state.saveable_keys, state.references)
        progress_iterator(state.unknowns, wrapper, threshold=1)
        msg = self.commit_message
        if not msg:
            f = ','.join('{}({})'.format(x, y) for x, y in zip(state.saveable_keys, state.saveable_fits))
            msg = 'auto update blanks, fits={}'.format(f)

        self._persist(state, msg)

    def _save_blanks(self, ai, prog, i, n, saveable_keys, references):
        if prog:
            prog.change_message('Save Blanks {} {}/{}'.format(ai.record_id, i, n))
        # print 'sssss', saveable_keys
        self.dvc.save_blanks(ai, saveable_keys, references)


class ICFactorPersistNode(DVCPersistNode):
    name = 'Save ICFactor'
    commit_tag = 'ICFactor'
    modifier = 'icfactors'

    def run(self, state):
        wrapper = lambda ai, prog, i, n: self._save_icfactors(ai, prog, i, n,
                                                              state.saveable_keys,
                                                              state.saveable_fits,
                                                              state.references,
                                                              state.delete_existing_icfactors)
        progress_iterator(state.unknowns, wrapper, threshold=1)

        msg = self.commit_message
        if not msg:
            f = ','.join('{}({})'.format(x, y) for x, y in zip(state.saveable_keys, state.saveable_fits))
            msg = 'auto update ic_factors, fits={}'.format(f)

        self._persist(state, msg)

    def _save_icfactors(self, ai, prog, i, n, saveable_keys, saveable_fits, reference, delete_existing):
        if prog:
            prog.change_message('Save IC Factor for {} {}/{}'.format(ai.record_id, i, n))

        if delete_existing:
            self.dvc.delete_existing_icfactors(ai, saveable_keys)

        self.dvc.save_icfactors(ai, saveable_keys, saveable_fits, reference)


class FluxPersistNode(DVCPersistNode):
    name = 'Save Flux'
    commit_tag = 'FLUX'

    def run(self, state):
        if state.saveable_irradiation_positions:
            xs = [x for x in state.saveable_irradiation_positions if x.save]
            if xs:
                self.dvc.meta_repo.smart_pull()

                progress_iterator(xs,
                                  lambda *args: self._save_j(state, *args),
                                  threshold=1)

                p = self.dvc.meta_repo.get_level_path(state.irradiation, state.level)
                self.dvc.meta_repo.add(p)
                self.dvc.meta_commit('fit flux for {}'.format(state.irradiation, state.level))

                if confirmation_dialog('Would you like to share your changes?'):
                    self.dvc.meta_repo.smart_pull()
                    self.dvc.meta_repo.push()

    def _save_j(self, state, irp, prog, i, n):
        if prog:
            prog.change_message('Save J for {} {}/{}'.format(irp.identifier, i, n))

        po = state.flux_options
        lk = po.lambda_k

        decay_constants = {'lambda_k_total': lk, 'lambda_k_total_error': 0}
        options = dict(model_kind=po.model_kind,
                       predicted_j_error_type=po.predicted_j_error_type,
                       use_weighted_fit=po.use_weighted_fit,
                       monte_carlo_ntrials=po.monte_carlo_ntrials,
                       use_monte_carlo=po.use_monte_carlo,
                       monitor_sample_name=po.monitor_sample_name,
                       monitor_age=po.monitor_age,
                       monitor_reference=po.selected_decay)

        self.dvc.save_flux_position(irp, options, decay_constants, add=False)
        # self.dvc.save_j(irp.irradiation, irp.level, irp.hole_id, irp.identifier,
        #                 irp.j, irp.jerr,
        #                 irp.mean_j, irp.mean_jerr,irp.
        #                 decay_constants,
        #                 analyses=irp.analyses,
        #                 options=options,
        #                 add=False)

        j = ufloat(irp.j, irp.jerr, tag='j')
        for i in state.unknowns:
            if i.identifier == irp.identifier:
                i.j = j
                i.arar_constants.lambda_k = lk
                i.recalculate_age()


class XLSXAnalysisTablePersistNode(BaseNode):
    name = 'Excel Analysis Table'
    # auto_configure = False
    # configurable = False

    options_klass = XLSXAnalysisTableWriterOptions

    def _pre_run_hook(self, state):
        ri = tuple({ai.repository_identifier for ai in state.unknowns})
        self.options.root_name = ri[0]

    def _finish_configure(self):
        self.options.dump()

    def run(self, state):
        writer = XLSXAnalysisTableWriter()
        writer.build(state.run_groups, options=self.options)


class InterpretedAgePersistNode(BaseDVCNode):
    name = 'Save Interpreted Ages'
    configurable = False

    def run(self, state):
        dvc = self.dvc
        for e in state.editors:
            if isinstance(e, SetInterpretedAgeEditor):
                for ia in e.groups:
                    if ia.use:
                        dvc.add_interpreted_age(ia)


# class TablePersistNode(FileNode):
#     pass
#
#
# class XLSTablePersistNode(BaseNode):
#     name = 'Save Analysis Table'
#     options_klass = AnalysisTablePersistOptionsView
#
#     def _options_factory(self):
#         opt = AnalysisTablePersistOptions(name='foo')
#         return self.options_klass(model=opt)
#
#     def run(self, state):
#         from pychron.pipeline.editors.arar_table_editor import ArArTableEditor
#
#         for editor in state.editors:
#             if isinstance(editor, ArArTableEditor):
#                 opt = self.options.model
#                 if opt.extension == 'xls':
#                     editor.make_xls_table(opt)
#                     view_file(opt.path)
#
#                     # basename = 'test_xls_table'
#                     # path, _ = unique_path2(paths.data_dir, basename, extension='.xls')
#                     # editor.make_xls_table('FooBar', path)
#
#
#
# class SetInterpretedAgeNode(BaseDVCNode):
#     name = 'Set IA'
#
#     def configure(self, pre_run=False, **kw):
#         return True
#
#     def run(self, state):
#         for editor in state.editors:
#             if isinstance(editor, InterpretedAgeEditor):
#                 ias = editor.get_interpreted_ages()
#                 set_interpreted_age(self.dvc, ias)
#
#
# class InterpretedAgeTablePersistNode(BaseNode):
#     name = 'Save IA Table'
#     options_klass = InterpretedAgePersistOptionsView
#
#     def _options_factory(self):
#         opt = InterpretedAgePersistOptions(name='foo')
#         return self.options_klass(model=opt)
#
#     def run(self, state):
#         from pychron.pipeline.editors.interpreted_age_table_editor import InterpretedAgeTableEditor
#         for editor in state.editors:
#             if isinstance(editor, InterpretedAgeTableEditor):
#                 opt = self.options.model
#                 if opt.extension == 'xlsx':
#                     editor.make_xls_table(opt)
#                     view_file(opt.path)

# ============= EOF =============================================
