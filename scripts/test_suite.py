from __future__ import annotations

import unittest

import httpx

API_URL = "http://localhost:8000"

class TestInfluenceIQBackend(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """Setup client and ensure database is freshly seeded before tests run."""
        self.client = httpx.AsyncClient(base_url=API_URL, timeout=10.0)

        # Fresh seed for predictable test data
        try:
            resp = await self.client.post("/api/demo/seed")
            self.assertEqual(resp.status_code, 200)
            self.seed_data = resp.json()
            self.campaign_id = self.seed_data["campaigns"]["BioGlow Collagen Peptide"]
            self.crypto_campaign_id = self.seed_data["campaigns"]["Apex DeFi Protocol"]
            self.dr_cho_id = self.seed_data["influencers"]["Dr. Jessica Cho"]
            self.crypto_king_id = self.seed_data["influencers"]["Crypto King"]
        except Exception as e:
            self.fail(f"Setup database seeding failed: {e}")

    async def asyncTearDown(self):
        """Close HTTPX client."""
        await self.client.aclose()

    async def test_1_system_health(self):
        """Verify GET /health returns complete telemetry diagnostic details."""
        resp = await self.client.get("/health")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["db"], "connected")
        self.assertEqual(data["redis"], "connected")
        self.assertIn("queues", data)
        self.assertIn("workers", data)

    async def test_2_campaign_metadata(self):
        """Verify GET /api/campaigns/{id} returns campaign models and Redis pipeline states."""
        resp = await self.client.get(f"/api/campaigns/{self.campaign_id}")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertIn("campaign", data)
        self.assertIn("pipeline_state", data)

        campaign = data["campaign"]
        self.assertEqual(campaign["id"], self.campaign_id)
        self.assertEqual(campaign["product"], "BioGlow Collagen Peptide")
        self.assertEqual(campaign["niche"], "beauty_health")
        self.assertListEqual(campaign["preferred_platforms"], ["instagram", "youtube"])
        self.assertEqual(campaign["weights"]["relevance"], 0.3)

    async def test_3_campaign_metadata_not_found(self):
        """Verify GET /api/campaigns/{id} returns a 404 error for non-existent UUIDs."""
        fake_uuid = "99999999-9999-9999-9999-999999999999"
        resp = await self.client.get(f"/api/campaigns/{fake_uuid}")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Campaign not found")

    async def test_4_campaign_influencers_list(self):
        """Verify GET /api/campaigns/{id}/influencers lists seeded ranked results with crawl sources."""
        resp = await self.client.get(f"/api/campaigns/{self.campaign_id}/influencers")
        self.assertEqual(resp.status_code, 200)

        influencers = resp.json()
        self.assertGreater(len(influencers), 0)

        # Verify first element is highest scored (Dr. Jessica Cho)
        top = influencers[0]
        self.assertEqual(top["canonical_name"], "Dr. Jessica Cho")
        self.assertEqual(top["final_score"], 92.5)
        self.assertIn("youtube", top["platforms"])

        # Verify provenance joins (sources array)
        self.assertGreater(len(top["sources"]), 0)
        source = top["sources"][0]
        self.assertEqual(source["status"], "scraped")
        self.assertEqual(source["url"], "https://dermatologytoday.com/articles/jessica-cho")

    async def test_5_campaign_influencers_grade_filter(self):
        """Verify GET /api/campaigns/{id}/influencers score filtering via Trust Grades."""
        # Querying Grade A+ should isolate Dr. Jessica Cho (score 92.5)
        resp_aplus = await self.client.get(f"/api/campaigns/{self.campaign_id}/influencers?grade=A%2B")
        self.assertEqual(resp_aplus.status_code, 200)
        data_aplus = resp_aplus.json()
        self.assertEqual(len(data_aplus), 1)
        self.assertEqual(data_aplus[0]["canonical_name"], "Dr. Jessica Cho")

        # Querying Grade A should isolate Elena Rostova (score 83.2)
        resp_a = await self.client.get(f"/api/campaigns/{self.campaign_id}/influencers?grade=A")
        self.assertEqual(resp_a.status_code, 200)
        data_a = resp_a.json()
        self.assertEqual(len(data_a), 1)
        self.assertEqual(data_a[0]["canonical_name"], "Elena Rostova")

    async def test_6_campaign_influencers_platform_filter(self):
        """Verify GET /api/campaigns/{id}/influencers platform existence filtering."""
        resp = await self.client.get(f"/api/campaigns/{self.campaign_id}/influencers?platform=tiktok")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Only Elena Rostova has TikTok, Dr. Cho does not
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["canonical_name"], "Elena Rostova")

    async def test_7_influencer_profile_details(self):
        """Verify GET /api/influencers/{id} returns correct canonical profile information."""
        resp = await self.client.get(f"/api/influencers/{self.dr_cho_id}")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["id"], self.dr_cho_id)
        self.assertEqual(data["canonical_name"], "Dr. Jessica Cho")
        self.assertListEqual(data["credentials"], ["MD, Dermatology", "Board Certified Dermatologist"])

    async def test_8_influencer_verifications(self):
        """Verify GET /api/influencers/{id}/verifications returns credentials verified status."""
        resp = await self.client.get(f"/api/influencers/{self.dr_cho_id}/verifications")
        self.assertEqual(resp.status_code, 200)

        verifications = resp.json()
        self.assertEqual(len(verifications), 2)

        # Both seeded credentials for Dr. Cho are verified
        for v in verifications:
            self.assertTrue(v["verified"])
            self.assertIn(v["credential_type"], ["license", "education"])

    async def test_9_influencer_brand_safety_violations(self):
        """Verify GET /api/influencers/{id}/safety returns brand risk flags."""
        resp = await self.client.get(f"/api/influencers/{self.crypto_king_id}/safety")
        self.assertEqual(resp.status_code, 200)

        flags = resp.json()
        self.assertEqual(len(flags), 1)

        flag = flags[0]
        self.assertEqual(flag["risk_type"], "scam")
        self.assertEqual(flag["campaign_id"], self.crypto_campaign_id)
        self.assertIn("pump and dump", flag["reason"])

if __name__ == "__main__":
    unittest.main()
