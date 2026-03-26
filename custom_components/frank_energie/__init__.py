"""The Frank Energie component."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FrankEnergieApi
from .const import CONF_COORDINATOR, CONF_SITE_REFERENCE, DOMAIN
from .coordinator import FrankEnergieCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Frank Energie component from a config entry."""

    # For backwards compatibility, set unique ID
    if entry.unique_id is None or entry.unique_id == "frank_energie_component":
        hass.config_entries.async_update_entry(entry, unique_id="frank_energie")

    # Select site-reference, or find first one that has status 'IN_DELIVERY' if not set
    if entry.data.get(CONF_SITE_REFERENCE) is None and entry.data.get(CONF_ACCESS_TOKEN) is not None:
        api = FrankEnergieApi(
            session=async_get_clientsession(hass),
            auth_token=entry.data.get(CONF_ACCESS_TOKEN),
            refresh_token=entry.data.get(CONF_TOKEN),
        )
        sites = await api.user_sites()

        # Filter out all sites that are not in delivery
        sites = [site for site in sites if site.status == "IN_DELIVERY"]

        if len(sites) == 0:
            raise Exception("No suitable sites found for this account")

        site = sites[0]
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_SITE_REFERENCE: site.reference}
        )

        # Update title with address if available
        if site.address:
            hass.config_entries.async_update_entry(entry, title=site.address)

    # Initialise the coordinator and save it as domain-data
    api = FrankEnergieApi(
        session=async_get_clientsession(hass),
        auth_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_TOKEN),
    )
    frank_coordinator = FrankEnergieCoordinator(hass, entry, api)

    # Fetch initial data, so we have data when entities subscribe and set up the platform
    await frank_coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_COORDINATOR: frank_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
