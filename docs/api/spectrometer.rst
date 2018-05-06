Spectrometer Package
====================

.. autoclass:: pychron.spectrometer.field_table.FieldTable
   :members:

.. autoclass:: pychron.spectrometer.fieldmixin.FieldMixin
   :members:

.. autoclass:: pychron.spectrometer.base_magnet.BaseMagnet
   :members:

.. autoclass:: pychron.spectrometer.base_detector.BaseDetector
   :members:

Thermo
------
The thermo package (pychron.spectrometer.thermo) contains abstractions for interfacing a Thermo Scientific mass spectrometer
via RemoteControlService.cs

Spectrometers
~~~~~~~~~~~~~
.. autoclass:: pychron.spectrometer.thermo.spectrometer.base.ThermoSpectrometer
   :members:

.. autoclass:: pychron.spectrometer.thermo.spectrometer.argus.ArgusSpectrometer
   :members:

.. autoclass:: pychron.spectrometer.thermo.spectrometer.helix.HelixSpectrometer
   :members:

.. autoclass:: pychron.spectrometer.thermo.magnet.base.ThermoMagnet
   :members:

.. autoclass:: pychron.spectrometer.thermo.magnet.argus.ArgusMagnet
   :members:

.. autoclass:: pychron.spectrometer.thermo.magnet.helix.HelixMagnet
   :members:


Isotopx
----------
The Isotopx package (pychron.spectrometer.isotopx) contains abstractions for interfacing a Isotopx mass 
spectrometer via IsotopxRCS

Spectrometers
~~~~~~~~~~~~~
.. autoclass:: pychron.spectrometer.isotopx.spectrometer.base.IsotopxSpectrometer
   :members:

.. autoclass:: pychron.spectrometer.isotopx.spectrometer.ngx.NGXSpectrometer
   :members:

.. autoclass:: pychron.spectrometer.isotopx.magnet.base.IsotopxMagnet
   :members:

.. autoclass:: pychron.spectrometer.isotopx.magnet.ngx.NGXMagnet
   :members:


MAP
--------------
The map package (pychron.spectrometer.map) contains abstractions for interfacing with a Mass Analyzer Products (MAP)
mass spectromter. Developed for New Mexico Geochronology Research Laboratory's MAP215-50

.. autoclass:: pychron.spectrometer.map.magnet.MapMagnet
   :members:
