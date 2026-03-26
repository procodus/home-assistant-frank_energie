"""GraphQL API client for Frank Energie."""
from __future__ import annotations

import logging
from datetime import date

import aiohttp

from .const import DATA_URL
from .models import (
    Invoices,
    MarketPrices,
    MonthSummary,
    Price,
    PriceData,
    UserSite,
)

_LOGGER = logging.getLogger(__name__)


class AuthException(Exception):
    """Authentication error."""


class RequestException(Exception):
    """API request error."""


class FrankEnergieApi:
    """GraphQL API client for Frank Energie."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        self._session = session
        self._auth_token = auth_token
        self._refresh_token = refresh_token

    @property
    def is_authenticated(self) -> bool:
        return self._auth_token is not None

    async def _query(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query."""
        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            async with self._session.post(DATA_URL, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    raise RequestException(f"API returned status {resp.status}")

                result = await resp.json()
        except aiohttp.ClientError as ex:
            raise RequestException(f"Connection error: {ex}") from ex

        if "errors" in result and result["errors"]:
            error_msg = result["errors"][0].get("message", "Unknown error")
            if "auth" in error_msg.lower():
                raise AuthException(error_msg)
            if error_msg.startswith("user-error:"):
                raise RequestException(error_msg)
            raise RequestException(error_msg)

        return result.get("data", {})

    async def login(self, username: str, password: str) -> dict:
        """Login with email and password. Returns {authToken, refreshToken}."""
        query = """
            mutation Login($email: String!, $password: String!) {
                login(email: $email, password: $password) {
                    authToken
                    refreshToken
                }
            }
        """
        data = await self._query(query, {"email": username, "password": password})
        result = data.get("login", {})
        self._auth_token = result.get("authToken")
        self._refresh_token = result.get("refreshToken")
        return result

    async def renew_token(self) -> dict:
        """Renew authentication tokens. Returns {authToken, refreshToken}."""
        query = """
            mutation RenewToken($authToken: String!, $refreshToken: String!) {
                renewToken(authToken: $authToken, refreshToken: $refreshToken) {
                    authToken
                    refreshToken
                }
            }
        """
        data = await self._query(query, {
            "authToken": self._auth_token,
            "refreshToken": self._refresh_token,
        })
        result = data.get("renewToken", {})
        self._auth_token = result.get("authToken")
        self._refresh_token = result.get("refreshToken")
        return result

    async def prices(self, start_date: date, end_date: date) -> MarketPrices:
        """Fetch public market prices for electricity and gas."""
        query = """
            query MarketPrices($startDate: String!, $endDate: String!) {
                marketPricesElectricity(startDate: $startDate, endDate: $endDate) {
                    from
                    till
                    marketPrice
                    marketPriceTax
                    sourcingMarkupPrice
                    energyTaxPrice
                }
                marketPricesGas(startDate: $startDate, endDate: $endDate) {
                    from
                    till
                    marketPrice
                    marketPriceTax
                    sourcingMarkupPrice
                    energyTaxPrice
                }
            }
        """
        data = await self._query(query, {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        })

        electricity = PriceData(
            price_data=[Price.from_dict(p) for p in data.get("marketPricesElectricity", [])]
        )
        gas = PriceData(
            price_data=[Price.from_dict(p) for p in data.get("marketPricesGas", [])]
        )
        return MarketPrices(electricity=electricity, gas=gas)

    async def user_prices(self, price_date: date, site_reference: str) -> MarketPrices:
        """Fetch personalized market prices (requires authentication)."""
        query = """
            query CustomerMarketPrices($date: String!, $siteReference: String!) {
                customerMarketPrices(date: $date, siteReference: $siteReference) {
                    electricityPrices {
                        from
                        till
                        marketPrice
                        marketPriceTax
                        consumptionSourcingMarkupPrice
                        energyTax
                        perUnit
                    }
                    gasPrices {
                        from
                        till
                        marketPrice
                        marketPriceTax
                        consumptionSourcingMarkupPrice
                        energyTax
                        perUnit
                    }
                }
            }
        """
        data = await self._query(query, {
            "date": price_date.isoformat(),
            "siteReference": site_reference,
        })

        cmp = data.get("customerMarketPrices", {}) or {}
        electricity = PriceData(
            price_data=[Price.from_user_prices_dict(p) for p in cmp.get("electricityPrices", [])]
        )
        gas = PriceData(
            price_data=[Price.from_user_prices_dict(p) for p in cmp.get("gasPrices", [])]
        )
        return MarketPrices(electricity=electricity, gas=gas)

    async def user_sites(self) -> list[UserSite]:
        """Fetch user delivery sites (requires authentication)."""
        query = """
            query UserSites {
                userSites {
                    reference
                    status
                    address {
                        addressFormatted
                    }
                }
            }
        """
        data = await self._query(query)
        return [UserSite.from_dict(s) for s in data.get("userSites", [])]

    async def month_summary(self, site_reference: str) -> MonthSummary:
        """Fetch monthly cost summary (requires authentication)."""
        query = """
            query MonthSummary($siteReference: String!) {
                monthSummary(siteReference: $siteReference) {
                    lastMeterReadingDate
                    expectedCostsUntilLastMeterReadingDate
                    actualCostsUntilLastMeterReadingDate
                }
            }
        """
        data = await self._query(query, {"siteReference": site_reference})
        return MonthSummary.from_dict(data.get("monthSummary", {}))

    async def invoices(self, site_reference: str) -> Invoices:
        """Fetch invoice data (requires authentication)."""
        query = """
            query Invoices($siteReference: String!) {
                invoices(siteReference: $siteReference) {
                    previousPeriodInvoice {
                        periodDescription
                        startDate
                        totalAmount
                    }
                    currentPeriodInvoice {
                        periodDescription
                        startDate
                        totalAmount
                    }
                    upcomingPeriodInvoice {
                        periodDescription
                        startDate
                        totalAmount
                    }
                }
            }
        """
        data = await self._query(query, {"siteReference": site_reference})
        return Invoices.from_dict(data.get("invoices", {}))
