"""Init file for HassIO homeassistant rest api."""
import asyncio
import logging

import voluptuous as vol

from .utils import api_process, api_process_raw, api_validate
from ..const import (
    ATTR_VERSION, ATTR_LAST_VERSION, ATTR_IMAGE, ATTR_CUSTOM, ATTR_BOOT,
    ATTR_PORT, ATTR_PASSWORD, ATTR_SSL, ATTR_WATCHDOG, ATTR_CPU_PERCENT,
    ATTR_MEMORY_USAGE, ATTR_MEMORY_LIMIT, ATTR_NETWORK_RX, ATTR_NETWORK_TX,
    ATTR_BLK_READ, ATTR_BLK_WRITE, ATTR_STARTUP_TIME, CONTENT_TYPE_BINARY)
from ..coresys import CoreSysAttributes
from ..validate import NETWORK_PORT, DOCKER_IMAGE

_LOGGER = logging.getLogger(__name__)


# pylint: disable=no-value-for-parameter
SCHEMA_OPTIONS = vol.Schema({
    vol.Optional(ATTR_BOOT): vol.Boolean(),
    vol.Inclusive(ATTR_IMAGE, 'custom_hass'):
        vol.Any(None, vol.Coerce(str)),
    vol.Inclusive(ATTR_LAST_VERSION, 'custom_hass'):
        vol.Any(None, DOCKER_IMAGE),
    vol.Optional(ATTR_PORT): NETWORK_PORT,
    vol.Optional(ATTR_PASSWORD): vol.Any(None, vol.Coerce(str)),
    vol.Optional(ATTR_SSL): vol.Boolean(),
    vol.Optional(ATTR_WATCHDOG): vol.Boolean(),
    vol.Optional(ATTR_STARTUP_TIME):
        vol.All(vol.Coerce(int), vol.Range(min=60)),
})

SCHEMA_VERSION = vol.Schema({
    vol.Optional(ATTR_VERSION): vol.Coerce(str),
})


class APIHomeAssistant(CoreSysAttributes):
    """Handle rest api for homeassistant functions."""

    @api_process
    async def info(self, request):
        """Return host information."""
        return {
            ATTR_VERSION: self._homeassistant.version,
            ATTR_LAST_VERSION: self._homeassistant.last_version,
            ATTR_IMAGE: self._homeassistant.image,
            ATTR_CUSTOM: self._homeassistant.is_custom_image,
            ATTR_BOOT: self._homeassistant.boot,
            ATTR_PORT: self._homeassistant.api_port,
            ATTR_SSL: self._homeassistant.api_ssl,
            ATTR_WATCHDOG: self._homeassistant.watchdog,
            ATTR_STARTUP_TIME: self._homeassistant.startup_time,
        }

    @api_process
    async def options(self, request):
        """Set homeassistant options."""
        body = await api_validate(SCHEMA_OPTIONS, request)

        if ATTR_IMAGE in body and ATTR_LAST_VERSION in body:
            self._homeassistant.image = body[ATTR_IMAGE]
            self._homeassistant.last_version = body[ATTR_LAST_VERSION]

        if ATTR_BOOT in body:
            self._homeassistant.boot = body[ATTR_BOOT]

        if ATTR_PORT in body:
            self._homeassistant.api_port = body[ATTR_PORT]

        if ATTR_PASSWORD in body:
            self._homeassistant.api_password = body[ATTR_PASSWORD]

        if ATTR_SSL in body:
            self._homeassistant.api_ssl = body[ATTR_SSL]

        if ATTR_WATCHDOG in body:
            self._homeassistant.watchdog = body[ATTR_WATCHDOG]

        if ATTR_STARTUP_TIME in body:
            self._homeassistant.startup_time = body[ATTR_STARTUP_TIME]

        self._homeassistant.save_data()
        return True

    @api_process
    async def stats(self, request):
        """Return resource information."""
        stats = await self._homeassistant.stats()
        if not stats:
            raise RuntimeError("No stats available")

        return {
            ATTR_CPU_PERCENT: stats.cpu_percent,
            ATTR_MEMORY_USAGE: stats.memory_usage,
            ATTR_MEMORY_LIMIT: stats.memory_limit,
            ATTR_NETWORK_RX: stats.network_rx,
            ATTR_NETWORK_TX: stats.network_tx,
            ATTR_BLK_READ: stats.blk_read,
            ATTR_BLK_WRITE: stats.blk_write,
        }

    @api_process
    async def update(self, request):
        """Update homeassistant."""
        body = await api_validate(SCHEMA_VERSION, request)
        version = body.get(ATTR_VERSION, self._homeassistant.last_version)

        if version == self._homeassistant.version:
            raise RuntimeError("Version {} is already in use".format(version))

        return await asyncio.shield(
            self._homeassistant.update(version), loop=self._loop)

    @api_process
    def stop(self, request):
        """Stop homeassistant."""
        return asyncio.shield(self._homeassistant.stop(), loop=self._loop)

    @api_process
    def start(self, request):
        """Start homeassistant."""
        return asyncio.shield(self._homeassistant.start(), loop=self._loop)

    @api_process
    def restart(self, request):
        """Restart homeassistant."""
        return asyncio.shield(self._homeassistant.restart(), loop=self._loop)

    @api_process_raw(CONTENT_TYPE_BINARY)
    def logs(self, request):
        """Return homeassistant docker logs."""
        return self._homeassistant.logs()

    @api_process
    async def check(self, request):
        """Check config of homeassistant."""
        result = await self._homeassistant.check_config()
        if not result.valid:
            raise RuntimeError(result.log)

        return True
