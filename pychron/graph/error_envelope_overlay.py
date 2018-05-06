# ===============================================================================
# Copyright 2013 Jake Ross
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
from chaco.abstract_overlay import AbstractOverlay
from enable.colors import black_color_trait
from traits.api import Array

# ============= standard library imports ========================
from numpy import array, zeros


# ============= local library imports  ==========================

class ErrorEnvelopeOverlay(AbstractOverlay):
    _cache_valid = False
    _screen_cache_valid = False

    upper = Array
    lower = Array
    use_downsampling = False
    line_color = black_color_trait

    xs = None

    def invalidate(self):
        self._cache_valid = False
        self._screen_cache_valid = False

    def _gather_points(self):
        if not self._cache_valid:
            index = self.component.index
            value = self.component.value
            if not index or not value:
                return

            xs = self.xs
            if xs is None:
                xs = index.get_data()

            ls = self.lower
            us = self.upper

            self._cached_data_pts_u = [array((xs, us)).T]
            self._cached_data_pts_l = [array((xs, ls)).T]

            self._cache_valid = True

        return

    def get_screen_points(self):
        self._gather_points()
        if self.use_downsampling:
            return self._downsample()
        else:
            return (self.component.map_screen(self._cached_data_pts_u),
                    self.component.map_screen(self._cached_data_pts_l))

    def overlay(self, other_component, gc, view_bounds=None, mode="normal"):
        with gc:
            gc.clip_to_rect(0, 0, other_component.width, other_component.height)
            upts, lpts = self.get_screen_points()
            gc.set_line_dash((5, 5))
            gc.set_stroke_color(self.line_color_)
            self._render_line(gc, upts)
            self._render_line(gc, lpts)

    def _render_line(self, gc, points):
        for ary in points:
            if len(ary) > 0:
                gc.begin_path()
                gc.lines(ary)
                gc.stroke_path()

    def _downsample(self):
        if not self._screen_cache_valid:
            self._cached_screen_pts_u = self.component.map_screen(self._cached_data_pts_u)[0]
            self._cached_screen_pts_l = self.component.map_screen(self._cached_data_pts_l)[0]

            self._screen_cache_valid = True

            for pt_arrays in (self._cached_screen_pts_l,
                              self._cached_screen_pts_u):
                r, c = pt_arrays.shape
                # some boneheaded short-circuits
                m = self.component.index_mapper
                total_numpoints = r * c
                if (total_numpoints < 400) or (total_numpoints < m.high_pos - m.low_pos):
                    return [self._cached_screen_pts_l], [self._cached_screen_pts_u]

                # the new point array and a counter of how many actual points we've added
                # to it
                new_arrays = []
                for pts in pt_arrays:
                    new_pts = zeros(pts.shape, "d")
                    numpoints = 1
                    new_pts[0] = pts[0]

                    last_x, last_y = pts[0]
                    for x, y in pts[1:]:
                        if (x - last_x) ** 2 + (y - last_y) ** 2 > 2:
                            new_pts[numpoints] = (x, y)
                            last_x = x
                            last_y = y
                            numpoints += 1

                    new_arrays.append(new_pts[:numpoints])

        return [self._cached_screen_pts_l], [self._cached_screen_pts_u]

# ============= EOF =============================================
