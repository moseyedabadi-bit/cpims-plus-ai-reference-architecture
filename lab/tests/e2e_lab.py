from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services" / "service.py"

PORTS = {
    "idp-a": 18101,
    "idp-b": 18102,
    "idp-c": 18103,
    "oversight": 18104,
    "policy": 18105,
    "case": 18106,
    "data-gateway": 18107,
    "ai": 18108,
    "audit": 18109,
    "gateway": 18110,
}


def post(url, body, session=None, expect=None):
    headers = {"Content-Type": "application/json"}
    if session:
        headers["X-Session"] = session
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            payload = json.loads(r.read())
            if expect is not None and r.status != expect:
                raise AssertionError((r.status, payload))
            return r.status, payload
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read())
        if expect is not None and exc.code == expect:
            return exc.code, payload
        raise


def get(url, session=None):
    headers = {"X-Session": session} if session else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=3) as r:
        return r.status, json.loads(r.read())


def wait_health(port):
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=.5) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(.1)
    raise RuntimeError(f"service on {port} did not start")


def launch(mode, port, extra=None):
    env = os.environ.copy()
    env.update({"MODE": mode, "PORT": str(port), "PYTHONUNBUFFERED": "1"})
    if extra:
        env.update(extra)
    return subprocess.Popen([sys.executable, str(SERVICE)], cwd=str(SERVICE.parent), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    procs = []
    with tempfile.TemporaryDirectory() as td:
        audit_file = str(Path(td) / "audit.jsonl")
        try:
            procs.append(launch("idp", PORTS["idp-a"], {"IDP_ID": "A", "IDP_SIGNING_KEY": "synthetic-idp-A-only"}))
            procs.append(launch("idp", PORTS["idp-b"], {"IDP_ID": "B", "IDP_SIGNING_KEY": "synthetic-idp-B-only"}))
            procs.append(launch("idp", PORTS["idp-c"], {"IDP_ID": "C", "IDP_SIGNING_KEY": "synthetic-idp-C-only"}))
            procs.append(launch("oversight", PORTS["oversight"], {"OVERSIGHT_SIGNING_KEY": "synthetic-oversight-only"}))
            procs.append(launch("policy", PORTS["policy"], {"POLICY_SIGNING_KEY": "synthetic-policy-only", "OVERSIGHT_SIGNING_KEY": "synthetic-oversight-only"}))
            procs.append(launch("case", PORTS["case"], {"CASE_PEER_KEY": "synthetic-case-peer-only"}))
            procs.append(launch("data_gateway", PORTS["data-gateway"], {
                "POLICY_SIGNING_KEY": "synthetic-policy-only",
                "CASE_PEER_KEY": "synthetic-case-peer-only",
                "CASE_URL": f"http://127.0.0.1:{PORTS['case']}",
            }))
            procs.append(launch("ai", PORTS["ai"], {"DATA_GATEWAY_URL": f"http://127.0.0.1:{PORTS['data-gateway']}"}))
            procs.append(launch("audit", PORTS["audit"], {"AUDIT_FILE": audit_file}))
            procs.append(launch("gateway", PORTS["gateway"], {
                "IDP_A_URL": f"http://127.0.0.1:{PORTS['idp-a']}",
                "IDP_B_URL": f"http://127.0.0.1:{PORTS['idp-b']}",
                "IDP_C_URL": f"http://127.0.0.1:{PORTS['idp-c']}",
                "IDP_A_KEY": "synthetic-idp-A-only",
                "IDP_B_KEY": "synthetic-idp-B-only",
                "IDP_C_KEY": "synthetic-idp-C-only",
                "POLICY_URL": f"http://127.0.0.1:{PORTS['policy']}",
                "DATA_GATEWAY_URL": f"http://127.0.0.1:{PORTS['data-gateway']}",
                "AI_URL": f"http://127.0.0.1:{PORTS['ai']}",
                "OVERSIGHT_URL": f"http://127.0.0.1:{PORTS['oversight']}",
                "AUDIT_URL": f"http://127.0.0.1:{PORTS['audit']}",
            }))

            for port in PORTS.values():
                wait_health(port)

            base = f"http://127.0.0.1:{PORTS['gateway']}"
            status, auth = post(base + "/api/authenticate", {"slot": "demo-001", "skip_provider": "C"}, expect=200)
            assert auth["threshold"] == "2-of-3" and len(auth["providers"]) == 2
            session = auth["session"]

            post(base + "/api/consent", {"level": "L2", "purpose": "family_reunification"}, session, 200)
            _, listed = post(base + "/api/cases", {"purpose": "family_reunification"}, session, 200)
            assert listed["records"][0]["case_id"] == "CASE-SYN-001"

            _, l2 = post(base + "/api/case", {"case_id": "CASE-SYN-001", "layer": "L2", "purpose": "family_reunification"}, session, 200)
            l2_record = l2.get("record") or l2.get("case") or {}
            assert "family_structure" in l2_record and "sealed_note" not in l2_record

            _, ai = post(base + "/api/analyze", {"case_id": "CASE-SYN-001", "layer": "L2", "purpose": "family_reunification"}, session, 200)
            assert ai["decision_authority"] is False

            status, denied = post(base + "/api/case", {"case_id": "CASE-SYN-001", "layer": "L3", "purpose": "family_reunification"}, session, 403)
            assert "step-up-consent-required" in (denied.get("reason") or denied.get("error", ""))

            post(base + "/api/consent", {"level": "L3", "purpose": "family_reunification"}, session, 200)
            post(base + "/api/case", {"case_id": "CASE-SYN-001", "layer": "L3", "purpose": "family_reunification"}, session, 200)

            status, denied_l4 = post(base + "/api/case", {"case_id": "CASE-SYN-001", "layer": "L4", "purpose": "family_reunification"}, session, 403)
            assert "independent-legal-authorization-required" in (denied_l4.get("reason") or denied_l4.get("error", ""))

            _, order = post(base + "/api/mock-judicial-order", {"case_id": "CASE-SYN-001", "purpose": "family_reunification"}, session, 200)
            _, l4 = post(base + "/api/case", {"case_id": "CASE-SYN-001", "layer": "L4", "purpose": "family_reunification", "order_id": order["order_id"]}, session, 200)
            l4_record = l4.get("record") or l4.get("case") or {}
            assert "sealed_note" in l4_record

            post(base + "/api/decision", {"case_id": "CASE-SYN-001", "purpose": "family_reunification", "outcome": "follow_up", "reason": "synthetic e2e"}, session, 200)
            _, audit = get(base + "/api/audit", session)
            assert audit["verification"]["valid"] is True and len(audit["events"]) >= 8

            post(base + "/api/revoke-consent", {"purpose": "family_reunification"}, session, 200)
            _, revoked = post(base + "/api/case", {"case_id": "CASE-SYN-001", "layer": "L2", "purpose": "family_reunification"}, session, 403)
            assert "consent-required" in (revoked.get("reason") or revoked.get("error", ""))

            print("Synthetic CPIMS+ lab E2E: PASS")
        finally:
            for proc in reversed(procs):
                proc.terminate()
            for proc in reversed(procs):
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    main()
