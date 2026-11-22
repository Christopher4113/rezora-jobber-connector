"""Thin Jobber GraphQL client. Names verified against API version 2026-11-18 via introspection."""

import os
import time
from datetime import datetime, timedelta

import httpx

URL = "https://api.getjobber.com/api/graphql"


class JobberError(RuntimeError):
    pass


def digits(phone: str | None) -> str:
    """Normalize a phone to its last 10 digits so +1 (617) 555-0101 == 6175550101."""
    return "".join(c for c in phone or "" if c.isdigit())[-10:]


class JobberClient:
    def __init__(self, token: str | None = None, version: str | None = None):
        self.token = token or os.environ["JOBBER_ACCESS_TOKEN"]
        self.version = version or os.environ.get("JOBBER_API_VERSION", "2026-11-18")
        self.last_cost: dict | None = None
        self.http = httpx.Client(timeout=30)

    def gql(self, query: str, variables: dict | None = None, _retry: bool = True) -> dict:
        r = self.http.post(
            URL,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {self.token}", "X-JOBBER-GRAPHQL-VERSION": self.version},
        )
        if r.status_code == 401:
            raise JobberError("Jobber rejected the access token (401). GraphiQL tokens expire after ~1h; get a new one.")
        r.raise_for_status()
        body = r.json()
        self.last_cost = (body.get("extensions") or {}).get("cost")
        errors = body.get("errors") or []
        if any((e.get("extensions") or {}).get("code") == "THROTTLED" for e in errors) and _retry:
            # Back off long enough for the bucket to restore the requested cost, then retry once.
            status = (self.last_cost or {}).get("throttleStatus", {})
            need = (self.last_cost or {}).get("requestedQueryCost", 100)
            time.sleep(min(10, max(1, need / max(status.get("restoreRate", 500), 1))))
            return self.gql(query, variables, _retry=False)
        if errors:
            raise JobberError("Jobber GraphQL error: " + "; ".join(e.get("message", str(e)) for e in errors))
        data = body["data"]
        for payload in data.values():  # mutations return {<field>: {..., userErrors: [...]}}
            if isinstance(payload, dict) and payload.get("userErrors"):
                raise JobberError("Jobber userErrors: " + "; ".join(e["message"] for e in payload["userErrors"]))
        return data

    # --- clients -------------------------------------------------------

    def find_client_by_phone(self, phone: str) -> dict | None:
        q = """query($t: String!) { clients(searchTerm: $t, first: 10) { nodes {
              id name phones { number } clientProperties(first: 1) { nodes { id } } } } }"""
        want = digits(phone)
        # Jobber's search matches on the formatted number, so search the last 4 and compare digits ourselves.
        for c in self.gql(q, {"t": want[-4:]})["clients"]["nodes"]:
            if any(digits(p["number"]) == want for p in c["phones"]):
                props = c["clientProperties"]["nodes"]
                return {"id": c["id"], "name": c["name"], "property_id": props[0]["id"] if props else None}
        return None

    def create_client(self, name: str | None, phone: str, address: str | None) -> dict:
        q = """mutation($i: ClientCreateInput!) { clientCreate(input: $i) {
              client { id name clientProperties(first: 1) { nodes { id } } } userErrors { message path } } }"""
        first, _, last = (name or "").partition(" ")
        i = {
            "firstName": first or "Unknown",
            "lastName": last or "Caller",
            "phones": [{"number": phone, "primary": True, "description": "MAIN"}],
        }
        if address:
            # ponytail: whole address in street1; parse into city/postal when Jobber routing needs it
            i["properties"] = [{"address": {"street1": address}}]
        c = self.gql(q, {"i": i})["clientCreate"]["client"]
        props = c["clientProperties"]["nodes"]
        return {"id": c["id"], "name": c["name"], "property_id": props[0]["id"] if props else None}

    def add_property(self, client_id: str, address: str) -> str:
        q = """mutation($c: EncodedId!, $i: PropertyCreateInput!) { propertyCreate(clientId: $c, input: $i) {
              properties { id } userErrors { message path } } }"""
        return self.gql(q, {"c": client_id, "i": {"properties": [{"address": {"street1": address}}]}})[
            "propertyCreate"]["properties"][0]["id"]

    # --- schedule ------------------------------------------------------

    def visits_between(self, start: datetime, end: datetime) -> list[dict]:
        q = """query($f: VisitFilterAttributes!, $after: String) { visits(filter: $f, first: 50, after: $after) {
              nodes { id title startAt endAt allDay client { name } }
              pageInfo { hasNextPage endCursor } } }"""
        # Widen by a day on each side so visits that started earlier but overlap are included.
        f = {"startAt": {"after": (start - timedelta(days=1)).isoformat(), "before": end.isoformat()}}
        out, after = [], None
        while True:
            v = self.gql(q, {"f": f, "after": after})["visits"]
            out += [
                {**n, "startAt": datetime.fromisoformat(n["startAt"]), "endAt": datetime.fromisoformat(n["endAt"])}
                for n in v["nodes"] if n["startAt"] and n["endAt"]
            ]
            if not v["pageInfo"]["hasNextPage"]:
                return [n for n in out if n["endAt"] > start and n["startAt"] < end]
            after = v["pageInfo"]["endCursor"]

    def create_job_with_visit(self, property_id: str, title: str, start: datetime, minutes: int,
                              instructions: str | None) -> dict:
        q = """mutation($i: JobCreateAttributes!) { jobCreate(input: $i) {
              job { id jobNumber jobberWebUri visits(first: 1) { nodes { id startAt endAt } } }
              userErrors { message path } } }"""
        end = start + timedelta(minutes=minutes)
        i = {
            "propertyId": property_id,
            "title": title,
            "instructions": instructions or "",
            "invoicing": {"invoicingType": "FIXED_PRICE", "invoicingSchedule": "ON_COMPLETION"},
            "timeframe": {"startAt": start.date().isoformat()},
            # Start/end times are wall-clock in the Jobber account's timezone.
            "scheduling": {"createVisits": True, "notifyTeam": False,
                           "startTime": start.strftime("%H:%M:%S"), "endTime": end.strftime("%H:%M:%S")},
        }
        return self.gql(q, {"i": i})["jobCreate"]["job"]

    def create_request(self, client_id: str, title: str, details: str | None) -> dict:
        q = """mutation($i: RequestCreateInput!) { requestCreate(input: $i) {
              request { id title jobberWebUri } userErrors { message path } } }"""
        req = self.gql(q, {"i": {"clientId": client_id, "title": title}})["requestCreate"]["request"]
        if details:
            n = """mutation($r: EncodedId!, $i: RequestCreateNoteInput!) { requestCreateNote(requestId: $r, input: $i) {
                  userErrors { message path } } }"""
            self.gql(n, {"r": req["id"], "i": {"message": details}})
        return req
