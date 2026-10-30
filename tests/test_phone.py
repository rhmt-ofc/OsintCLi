"""Unit tests for Phone Intelligence Module in OsintCLI."""
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock

from osintcli.core import Config, target
from osintcli.db import Store
from osintcli.engine import Context, run
from osintcli.phone.hlr import lookup_hlr
from osintcli.phone.truecaller import parse_truecaller_response
from osintcli.phone.getcontact import sign_payload, extract_candidate_handles, parse_getcontact_response
from osintcli.phone.messaging import probe_whatsapp, probe_telegram
from osintcli.phone.aggregator import collect_phone_intel


class TestPhoneIntel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name)
        self.config = Config(p / 'data', p / 'config')
        self.db = Store(self.config)

    def tearDown(self):
        self.tmp.cleanup()

    def test_hlr_lookup_telkomsel(self):
        res = lookup_hlr("+6281234567890")
        self.assertTrue(res["valid"])
        self.assertEqual(res["country_code"], "62")
        self.assertEqual(res["carrier"], "Telkomsel")
        self.assertIn("Jawa Timur", res["region"])

    def test_hlr_lookup_indosat(self):
        res = lookup_hlr("+6285712345678")
        self.assertTrue(res["valid"])
        self.assertEqual(res["carrier"], "Indosat Ooredoo")
        self.assertIn("Jabodetabek", res["region"])

    def test_hlr_lookup_international(self):
        res = lookup_hlr("+14155552671")
        self.assertTrue(res["valid"])
        self.assertIn("Amerika Serikat", res["country"])

        res_uk = lookup_hlr("+447911123456")
        self.assertTrue(res_uk["valid"])
        self.assertIn("Britania Raya", res_uk["country"])

    def test_getcontact_handle_extraction(self):
        tags = [
            "Rahmat Hidayat",
            "@rhmt_ofc",
            "Kang Bakso",
            "ig: rhmt_dev",
            "Teman Kantor",
            "mamat_koding"
        ]
        handles = extract_candidate_handles(tags)
        self.assertIn("rhmt_ofc", handles)
        self.assertIn("rhmt_dev", handles)
        self.assertIn("mamat_koding", handles)
        self.assertNotIn("teman kantor", handles)

    def test_getcontact_signing(self):
        ts = "1700000000"
        payload = b'{"phoneNumber":"+6281234567890"}'
        sig = sign_payload(ts, payload)
        self.assertEqual(len(sig), 64)  # SHA-256 hex string

    def test_truecaller_parser(self):
        sample = {
            "data": [{
                "name": "Rahmat Hidayat",
                "phones": [{"e164Format": "+6281234567890", "carrier": "Telkomsel"}],
                "spamScore": 2,
                "badges": ["VERIFIED"],
                "addresses": [{"city": "Surabaya", "countryCode": "id"}],
                "internetAddresses": [{"id": "rahmat@example.com"}]
            }]
        }
        parsed = parse_truecaller_response(sample)
        self.assertTrue(parsed["found"])
        self.assertEqual(parsed["name"], "Rahmat Hidayat")
        self.assertEqual(parsed["carrier"], "Telkomsel")
        self.assertEqual(parsed["spam_score"], 2)
        self.assertEqual(parsed["email"], "rahmat@example.com")

    def test_messaging_probes(self):
        wa = probe_whatsapp("+6281234567890")
        self.assertEqual(wa["direct_link"], "https://wa.me/6281234567890")

        tg = probe_telegram("+6281234567890")
        self.assertEqual(tg["direct_link"], "https://t.me/+6281234567890")

    def test_aggregator_yields_evidence_and_relationships(self):
        ctx = Context("+6281234567890", "phone", self.config, Mock(), threading.Event())
        items = list(collect_phone_intel(ctx))

        types = [i["entity_type"] for i in items]
        self.assertIn("phone_format", types)
        self.assertIn("phone_hlr", types)
        self.assertIn("phone_region", types)
        self.assertIn("messaging_wa", types)
        self.assertIn("messaging_tg", types)
        self.assertIn("relationship", types)

        # Ensure relationships contain OPERATED_BY and REGISTERED_ON
        relations = [i["title"] for i in items if i["entity_type"] == "relationship"]
        self.assertIn("OPERATED_BY", relations)
        self.assertIn("REGISTERED_ON", relations)

    def test_engine_run_phone_case(self):
        cid = run(self.config, "+6281234567890", kind="phone")
        self.assertTrue(cid)
        case = self.db.case(cid)
        self.assertEqual(case["state"], "DONE")
        evidence = self.db.evidence(cid)
        self.assertTrue(len(evidence) > 0)
        categories = {e["entity_type"] for e in evidence}
        self.assertIn("phone_hlr", categories)
        self.assertIn("messaging_wa", categories)


if __name__ == "__main__":
    unittest.main()
