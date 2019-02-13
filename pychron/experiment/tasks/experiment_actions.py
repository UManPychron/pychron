# ===============================================================================
# Copyright 2011 Jake Ross
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
import os

from pyface.message_dialog import warning, information
from pyface.tasks.task_window_layout import TaskWindowLayout

from pychron.core.helpers.filetools import get_path
from pychron.envisage.resources import icon
from pychron.envisage.tasks.actions import PAction as Action, PTaskAction as TaskAction
from pychron.envisage.view_util import open_view
from pychron.extraction_line.ipyscript_runner import IPyScriptRunner
from pychron.globals import globalv
from pychron.paths import paths

EXP_ID = 'pychron.experiment.task'



class ExperimentAction(Action):
    task_id = EXP_ID

    # def _get_experimentor(self, event):
    # return self._get_service(event, 'pychron.experiment.experimentor.Experimentor')

    def _get_service(self, event, name):
        app = event.task.window.application
        return app.get_service(name)

    def _open_editor(self, event):
        application = event.task.window.application
        application.open_task(self.task_id)


class ConfigureEditorTableAction(TaskAction):
    name = 'Configure Experiment Table'
    dname = 'Configure Experiment Table'
    method = 'configure_experiment_table'


class BasePatternAction(TaskAction):
    _enabled = None

    def _task_changed(self):
        if self.task:
            if hasattr(self.task, 'open_pattern'):
                enabled = True
                if self.enabled_name:
                    if self.object:
                        enabled = bool(self._get_attr(self.object,
                                                      self.enabled_name, False))
                if enabled:
                    self._enabled = True
            else:
                self._enabled = False

    def _enabled_update(self):
        """
             reimplement ListeningAction's _enabled_update
        """
        if self.enabled_name:
            if self.object:
                self.enabled = bool(self._get_attr(self.object,
                                                   self.enabled_name, False))
            else:
                self.enabled = False
        elif self._enabled is not None:
            self.enabled = self._enabled
        else:
            self.enabled = bool(self.object)


class OpenPatternAction(BasePatternAction):
    name = 'Open Pattern...'
    dname = 'Open Pattern'
    method = 'open_pattern'


class NewPatternAction(BasePatternAction):
    name = 'New Pattern...'
    dname = 'New Pattern'
    method = 'new_pattern'


class DeselectAction(TaskAction):
    name = 'Deselect'
    dname = 'Deselect'
    method = 'deselect'
    tooltip = 'Deselect the selected run(s)'
    id = 'pychron.deselect'


class UndoAction(TaskAction):
    name = 'Undo'
    dname = 'Undo'
    method = 'undo'
    accelerator = 'Ctrl+Z'


class QueueConditionalsAction(Action):
    name = 'Edit Queue Conditionals'
    dname = 'Edit Queue Conditionals'

    def perform(self, event):
        task = event.task
        if hasattr(task, 'edit_queue_conditionals'):
            # edit the current queue's conditionals
            task.edit_queue_conditionals()
        else:
            # choose a conditionals file to edit
            from pychron.experiment.conditional.conditionals_edit_view import edit_conditionals

            dnames = None
            spec = task.application.get_service(
                'pychron.spectrometer.base_spectrometer_manager.BaseSpectrometerManager')
            if spec:
                dnames = spec.spectrometer.detector_names

            edit_conditionals(None, detectors=dnames)


class SystemConditionalsAction(Action):
    name = 'Edit System Conditionals'
    dname = 'Edit System Conditionals'

    def perform(self, event):
        from pychron.experiment.conditional.conditionals_edit_view import edit_conditionals

        task = event.task
        dnames = None
        spec = task.application.get_service(
            'pychron.spectrometer.base_spectrometer_manager.BaseSpectrometerManager')
        if spec:
            dnames = spec.spectrometer.detector_names

        p = get_path(paths.spectrometer_dir, '.*conditionals', ('.yaml', '.yml'))
        if p:
            edit_conditionals(p, detectors=dnames)
        else:
            warning(None, 'No system conditionals file at {}'.format(p))


def open_experiment(event, path=None):
    app = event.task.window.application
    task = event.task
    if task.id == EXP_ID:
        task.open(path)
    else:
        task = app.get_task(EXP_ID, False)
        if task.open(path):
            task.window.open()


# class QueueAction(ExperimentAction):
#     def _open_experiment(self, event, path=None):
#         open_experiment(event, path)


class NewExperimentQueueAction(ExperimentAction):
    description = 'Create a new experiment queue'
    name = 'New Experiment'
    dname = 'New Experiment'
    id = 'pychron.new_experiment'

    def perform(self, event):
        if event.task.id == EXP_ID:
            event.task.new()
        else:
            application = event.task.window.application
            win = application.create_window(TaskWindowLayout(EXP_ID))
            task = win.active_task
            if task.new():
                win.open()


class RunHistoryAction(Action):
    name = 'Run History'
    dname = 'Run History'

    def perform(self, event):
        app = event.task.window.application
        v = app.get_service('pychron.experiment.run_history_view.RunHistoryView')
        open_view(v)


class OpenExperimentHistoryAction(Action):
    name = 'Experiment Launch History'
    dname = 'Experiment Launch History'

    def perform(self, event):
        from pychron.experiment.experiment_launch_history import ExperimentLaunchHistory

        elh = ExperimentLaunchHistory()
        elh.load()
        info = elh.edit_traits()
        if info.result:
            if elh.selected:
                open_experiment(event, elh.selected.path)


class OpenLastExperimentQueueAction(ExperimentAction):
    description = 'Open last executed experiment'
    name = 'Open Last Experiment...'
    dname = 'Open Last Experiment'
    id = 'pychron.open_last_experiment'

    def __init__(self, *args, **kw):
        super(OpenLastExperimentQueueAction, self).__init__(*args, **kw)
        self.enabled = bool(self._get_last_experiment())

    def perform(self, event):
        path = self._get_last_experiment()
        if path:
            open_experiment(event, path)
        else:
            warning(None, 'No last experiment available')
            # if os.path.isfile(paths.last_experiment):
            # with open(paths.last_experiment, 'r') as rfile:
            #         path = fp.readline()
            #         if os.path.isfile(path):
            #             self._open_experiment(event, path)
            #         else:
            #             print 'asdfasdf', path
            # else:
            #     warning(None, 'No last experiment available')

    def _get_last_experiment(self):
        if os.path.isfile(paths.last_experiment):
            with open(paths.last_experiment, 'r') as rfile:
                path = rfile.readline()
                if os.path.isfile(path):
                    return path


class OpenExperimentQueueAction(ExperimentAction):
    description = 'Open experiment'
    name = 'Open Experiment...'
    dname = 'Open Experiment'
    image = icon('project-open')
    id = 'pychron.open_experiment'

    def perform(self, event):
        open_experiment(event)


class OpenCurrentExperimentQueueAction(ExperimentAction):
    description = 'Open Current Experiment'
    name = 'Open Current Experiment...'
    dname = 'Open Current Experiment'
    image = icon('project-open')
    id = 'pychron.open_current_experiment'

    def perform(self, event):
        name = 'CurrentExperiment.txt'
        path = os.path.join(paths.experiment_dir, name)

        if not os.path.isfile(path):
            information(None, 'No experiment called {}'.format(name))
        open_experiment(event, path)


class SaveAsCurrentExperimentAction(TaskAction):
    description = 'Save As Current Experiment'
    name = 'Save As Current Experiment...'
    dname = 'Save As Current Experiment'
    image = icon('document-save-as')
    id = 'pychron.experiment.save_as_current_experiment'
    method = 'save_as_current_experiment'


# ===============================================================================
# Utilities
# ===============================================================================

class SignalCalculatorAction(ExperimentAction):
    name = 'Signal Calculator'
    dname = 'Signal Calculator'

    def perform(self, event):
        obj = self._get_service(event, 'pychron.experiment.signal_calculator.SignalCalculator')
        open_view(obj)


class ResetQueuesAction(TaskAction):
    method = 'reset_queues'
    name = 'Reset Queues'
    dname = 'Reset Queues'


class SyncQueueAction(TaskAction):
    method = 'sync_queue'
    name = 'Sync Queue'
    dname = 'Sync Queue'


class LastAnalysisRecoveryAction(Action):
    name = 'Recover Last Analysis'
    dname = 'Recover Last Analysis'

    def perform(self, event):
        from pychron.experiment.analysis_recovery import AnalysisRecoverer
        a = AnalysisRecoverer()
        a.recover_last_analysis()


class RunnerAction(TaskAction):
    def _get_runner(self, event):
        app = event.task.application
        runner = app.get_service(IPyScriptRunner)
        if not runner:
            warning(None, 'No runner available')

        return runner


class AcquireSpectrometerAction(RunnerAction):
    def perform(self, event):
        runner = self._get_runner()
        if runner:
            if not runner.acquire(globalv.own_spectrometer):
                warning(None, 'Failed to acquire {}'.format(globalv.spectrometer))


class ReleaseSpectrometerAction(RunnerAction):
    def perform(self, event):
        runner = self._get_runner()
        if runner:
            runner.release(globalv.own_spectrometer)

# ============= EOF ====================================
