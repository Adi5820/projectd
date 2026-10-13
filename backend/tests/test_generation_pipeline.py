"""Direct verification test for AI generation pipeline."""

import asyncio
import os
from backend.api.dependencies import get_orchestrator

async def main():
    print("Initializing orchestrator...")
    orchestrator = get_orchestrator()

    test_campaign = {
        "brand_name": "NovaPulse",
        "product_name": "ActiveWatch Ultra",
        "product_description": "Next-gen titanium smartwatch with real-time biometric tracking, 14-day battery, and offline topographic maps.",
        "target_audience": "Athletes, hikers, and tech enthusiasts aged 24-45",
        "tone": "inspirational",
        "platforms": ["instagram", "tiktok"],
        "campaign_goal": "sales_conversion",
    }

    # 1. Test Copywriting
    print("\n--- Testing Ad Copy Generation ---")
    copy_result = await orchestrator.run_copy_only(
        campaign_data=test_campaign,
        num_variations=3,
    )
    variations = copy_result.get("ad_copy", {}).get("variations", [])
    print(f"Generated {len(variations)} ad copy variations:")
    for i, v in enumerate(variations):
        h = v.get("headline") if isinstance(v, dict) else v.headline
        cta = v.get("call_to_action") if isinstance(v, dict) else v.call_to_action
        print(f"  [{i+1}] {h} | CTA: {cta}")

    assert len(variations) > 0, "No ad variations produced!"

    # 2. Test Poster Generation
    print("\n--- Testing Poster Image Generation ---")
    poster_result = await orchestrator.run_poster_only(
        campaign_data=test_campaign,
        poster_request={"aspect_ratio": "1:1", "platform": "instagram"},
    )
    poster_data = poster_result.get("poster", {})
    image_bytes = poster_data.get("image_bytes")
    assert image_bytes and len(image_bytes) > 1000, "Poster image bytes empty!"
    print(f"Poster successfully generated: {len(image_bytes)} bytes, provider={poster_data.get('provider')}")

    # Save to disk to inspect
    os.makedirs(r"d:\projectd\media\posters", exist_ok=True)
    test_poster_path = r"d:\projectd\media\posters\test_poster.jpg"
    with open(test_poster_path, "wb") as f:
        f.write(image_bytes)
    print(f"Saved test poster to: {test_poster_path} (size: {os.path.getsize(test_poster_path)} bytes)")

    # 3. Test Video Generation
    print("\n--- Testing Video Commercial Generation ---")
    video_result = await orchestrator.run_video_only(
        campaign_data=test_campaign,
        video_request={"duration": 15, "platform": "tiktok"},
    )
    video_data = video_result.get("video", {})
    video_path = video_data.get("video_path")
    print(f"Video path returned: {video_path}")
    assert video_path and os.path.exists(video_path), "Video file does not exist!"
    video_size = os.path.getsize(video_path)
    print(f"Video file verified on disk: {video_size} bytes")
    assert video_size > 5000, f"Video file is suspiciously small ({video_size} bytes)!"

    print("\n=== ALL THREE GENERATION ENGINES VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(main())
