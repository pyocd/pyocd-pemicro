# -*- coding: utf-8 -*-
#
# Copyright © 2020 NXP
# Copyright © 2020 Chris Reed
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# o Redistributions of source code must retain the above copyright notice, this list
#   of conditions and the following disclaimer.
#
# o Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
# o Neither the names of the copyright holders nor the names of the
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import six
from pypemicro import PyPemicro, PEMicroException, PEMicroTransferException, PEMicroInterfaces
import logging
from time import sleep

from pyocd.probe.debug_probe import DebugProbe
from pyocd.core.plugin import Plugin
from pyocd.core import exceptions

from ._version import version as plugin_version

LOG = logging.getLogger(__name__)

TRACE = LOG.getChild("trace")
TRACE.disabled = True


class PEMicroProbe(DebugProbe):
    """! @brief Wraps a PEMicro as a DebugProbe."""

    # Address of DP's SELECT register.
    DP_SELECT = 0x8

    # Bitmasks for AP register address fields.
    APBANKSEL = 0x000000f0
    APSEL = 0xff000000
    APSEL_SHIFT = 24
    APSEL_APBANKSEL = APSEL | APBANKSEL

    # Part of the error message for exceptions raised when there isn't a PEMicro library
    # matching the system's architecture, or other similar reasons.
    NO_LIBRARY_ERR = "Unable to find any usable library"

    @classmethod
    def _get_pemicro(cls):
        # PEMicroException is raised by PyPemicro if the PEMicro DLL cannot be found.
        try:
            return PyPemicro(log_debug=TRACE.debug,
                             log_err=TRACE.error,
                             log_war=TRACE.warning,
                             log_info=TRACE.info)
        except PEMicroException:
            return None

    @classmethod
    def get_all_connected_probes(cls, unique_id=None, is_explicit=False):
        try:
            pemicro = cls._get_pemicro()
            if pemicro is None:
                return []
            port_list = pemicro.list_ports()
            if port_list is None:
                return []
            return [cls(str(info["id"])) for info in port_list]
        except PEMicroException as exc:
            # Ignore errors about a missing library, which can happen on systems not supported by
            # the PEMicro library but on which the plugin is installed.
            if cls.NO_LIBRARY_ERR in str(exc):
                return []
            six.raise_from(cls._convert_exception(exc), exc)

    @classmethod
    def get_probe_with_id(cls, unique_id, is_explicit=False):
        try:
            pemicro = cls._get_pemicro()
            if pemicro is None:
                return None
            for info in pemicro.list_ports():
                if str(info["id"]) == unique_id:
                    return cls(str(info["id"]))
            else:
                return None
        except PEMicroException as exc:
            # Ignore errors about a missing library, which can happen on systems not supported by
            # the PEMicro library but on which the plugin is installed.
            if cls.NO_LIBRARY_ERR in str(exc):
                return None
            six.raise_from(cls._convert_exception(exc), exc)

    def __init__(self, serial_number):
        super(PEMicroProbe, self).__init__()
        self._pemicro = self._get_pemicro()
        if self._pemicro is None:
            raise PEMicroException("unable to get PEMicro DLL")

        self._serial_number = serial_number
        self._supported_protocols = None
        self._protocol = None
        self._default_protocol = None
        self._is_open = False
        self._reset_delay_ms = -1
        self.reset_pin_state = True
        try:
            self._pemicro.open(self._serial_number)
            self._product_name = self._pemicro.version() or "Unknown"
            self._pemicro.close()
        except PEMicroException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    @property
    def description(self):
        vendor = self.vendor_name
        product = self.product_name
        return  vendor + " " + product

    @property
    def vendor_name(self):
        return "PEMicro"

    @property
    def product_name(self):
        return self._product_name

    ## @brief Only valid after opening.
    @property
    def supported_wire_protocols(self):
        return self._supported_protocols

    @property
    def unique_id(self):
        return self._serial_number

    @property
    def wire_protocol(self):
        return self._protocol

    @property
    def is_open(self):
        return self._pemicro.opened

    @property
    def capabilities(self):
        return {self.Capability.SWO, self.Capability.MANAGED_AP_SELECTION, self.Capability.BANKED_DP_REGISTERS, self.Capability.MANAGED_DPBANKSEL}

    def open(self):
        try:
            self._pemicro.open(self._serial_number)
            self._is_open = True

            # Get available wire protocols.
            # ifaces = self._pemicro.supported_tifs()
            self._supported_protocols = [DebugProbe.Protocol.DEFAULT]
            self._supported_protocols.append(DebugProbe.Protocol.JTAG)
            self._supported_protocols.append(DebugProbe.Protocol.SWD)

            # Select default protocol, preferring SWD over JTAG.
            self._default_protocol = DebugProbe.Protocol.SWD

        except PEMicroException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    def close(self):
        try:
            self._pemicro.close()
            self._is_open = False
        except PEMicroException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    # ------------------------------------------- #
    #          Target control functions
    # ------------------------------------------- #
    def connect(self, protocol=None):
        """! @brief Connect to the target via JTAG or SWD."""
        # Handle default protocol.
        if (protocol is None) or (protocol == DebugProbe.Protocol.DEFAULT):
            protocol = self._default_protocol

        # Validate selected protocol.
        if protocol not in self._supported_protocols:
            raise ValueError("unsupported wire protocol %s" % protocol)

        # Convert protocol to port enum.
        if protocol == DebugProbe.Protocol.SWD:
            iface = PEMicroInterfaces.SWD
        elif protocol == DebugProbe.Protocol.JTAG:
            iface = PEMicroInterfaces.JTAG

        try:
            if self.session.options.get('pemicro.power'):
                self._pemicro.power_on()

            device_name = self.session.options.get('pemicro.device')

            if device_name is not None:
                if self._pemicro.set_device_name(device_name) is False:
                    LOG.warning("Set of PEMicro device name({name}) failed".format(name=device_name))

            self._pemicro.connect(iface, self.session.options.get("swv_clock"))
            self._protocol = protocol
        except PEMicroException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    def swj_sequence(self, length, bits):
        raise NotImplementedError()

    def disconnect(self):
        """! @brief Disconnect from the target."""
        self._protocol = None

    def set_clock(self, frequency):
        try:
            self._pemicro.set_debug_frequency(frequency)
        except PEMicroException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    def reset(self):
        try:
            # Just do read operation to flush last operation before reset
            # Obviously the Flush doesn't work as excepted :-(
            self.read_ap(0)
            self._pemicro.flush_any_queued_data()

            # If it's neccessary, change the reset delay
            # delay = int(1000 * max(self.session.options.get('reset.hold_time'), self.session.options.get('reset.post_delay')))
            # if delay is not self._reset_delay_ms:
            #     self._pemicro.set_reset_delay_in_ms(delay)
            #     self._reset_delay_ms = delay

            # # Try to force reset Hardware
            # self._pemicro.reset_target()

            # Resume the MCU from Halt state
            #self._pemicro.resume_target()

            self.assert_reset(asserted=True)
            sleep(self.session.options.get('reset.hold_time'))
            self.assert_reset(asserted=False)
            sleep(self.session.options.get('reset.post_delay'))

        except PEMicroException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    def assert_reset(self, asserted=False):
        try:
            self._pemicro.control_reset_line(asserted)
            self.reset_pin_state = not asserted
        except PEMicroException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    def is_reset_asserted(self):
        return not self.reset_pin_state

    # ------------------------------------------- #
    #          DAP Access functions
    # ------------------------------------------- #
    def flush(self):
        try:
            self._pemicro.flush_any_queued_data()
        except Exception as exc:
            six.raise_from(self._convert_exception(exc), exc)

    def read_dp(self, addr, now=True):
        try:
            value = self._pemicro.read_dp_register(addr=addr, now=now)
        except PEMicroTransferException as exc:
            six.raise_from(self._convert_exception(exc), exc)
        else:
            def read_reg_cb():
                return value

            return value if now else read_reg_cb

    def write_dp(self, addr, data, now = True):
        try:
            self._pemicro.write_dp_register(addr=addr, value=data)
        except PEMicroTransferException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    def read_ap(self, addr, now=True):
        assert type(addr) in (six.integer_types)
        try:
            value = self._pemicro.read_ap_register(addr=(addr & self.APADDR), now=now, apselect= ((addr & self.APSEL_APBANKSEL) >> self.APSEL_SHIFT))
        except PEMicroTransferException as exc:
            six.raise_from(self._convert_exception(exc), exc)
        else:
            def read_reg_cb():
                return value

            return value if now else read_reg_cb

    def write_ap(self, addr, data, now = True):
        assert type(addr) in (six.integer_types)
        try:
            self._pemicro.write_ap_register(addr=(addr & self.APADDR), value=data, apselect=((addr & self.APSEL_APBANKSEL) >> self.APSEL_SHIFT))
        except PEMicroTransferException as exc:
            six.raise_from(self._convert_exception(exc), exc)

    def read_ap_multiple(self, addr, count=1, now=True):
        results = [self.read_ap(addr, True) for n in range(count)]

        def read_ap_multiple_result_callback():
            return results

        return results if now else read_ap_multiple_result_callback

    def write_ap_multiple(self, addr, values, now = True):
        for v in values:
            self.write_ap(addr, v)

    @staticmethod
    def _convert_exception(exc):
        if isinstance(exc, PEMicroTransferException):
            return exceptions.TransferFaultError()
        elif isinstance(exc, PEMicroException):
            return exceptions.ProbeError(str(exc))
        else:
            return exc


class PEMicroProbePlugin(Plugin):
    """! @brief Plugin class for PEMicroProbe."""

    def load(self):
        return PEMicroProbe

    @property
    def name(self):
        return "pemicro"

    @property
    def description(self):
        return "PEMicro debug probe"

    @property
    def version(self):
        return plugin_version

