#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

async def test_baselines():
    try:
        from data.loader import NISTDataLoader
        from nist_mcp.control_tools import ControlTools

        print("Starting baseline test...")
        loader = NISTDataLoader(Path('data'))
        await loader.initialize()
        tools = ControlTools(loader)

        print("Testing moderate baseline...")

        # First, let's check what's in the baseline profiles
        baseline_profiles = await loader.load_baseline_profiles()
        if 'moderate' in baseline_profiles:
            baseline_profile = baseline_profiles['moderate']
            baseline_control_ids = tools._extract_baseline_control_ids(baseline_profile)
            print(f"   Raw baseline has {len(baseline_control_ids)} control IDs")
            if baseline_control_ids:
                sample_ids = list(baseline_control_ids)[:5]
                print(f"   Sample baseline IDs: {sample_ids}")

        result = await tools.get_control_baselines('moderate')
        print(f"✅ Moderate baseline: {result.get('total_controls', 0)} controls")

        if result.get('controls'):
            print(f"   First 3: {[c['id'] for c in result['controls'][:3]]}")
            enhancements = [c for c in result['controls'] if '.' in c['id']]
            print(f"   Includes {len(enhancements)} control enhancements")

        # Check for missing controls
        if 'missing_controls' in result:
            print(f"   Missing {result['missing_count']} controls")
            if result['missing_count'] <= 5:
                print(f"   Missing controls: {result['missing_controls']}")

        # Now let's check what controls are actually in the database
        print("   Loading controls data...")
        controls_data = await loader.load_controls()
        print(f"   Controls data keys: {list(controls_data.keys())}")

        controls_db = controls_data.get("catalog", {}).get("controls", [])
        print(f"   Control database has {len(controls_db)} controls")

        # Also check if there are direct controls at top level
        top_level_controls = controls_data.get("controls", [])
        print(f"   Top-level controls: {len(top_level_controls)} controls")

        if controls_db:
            db_sample_ids = [c.get('id', '') for c in controls_db[:5]]
            print(f"   Database control sample IDs: {db_sample_ids}")
        elif top_level_controls:
            db_sample_ids = [c.get('id', '') for c in top_level_controls[:5]]
            print(f"   Top-level control sample IDs: {db_sample_ids}")

        # Let's also check if the lookup is working
        test_baseline_ids = list(baseline_control_ids)[:3]  # First 3 from baseline
        print(f"   Testing lookup for: {test_baseline_ids}")
        for test_id in test_baseline_ids:
            found = tools.data_loader.get_control_by_id(controls_data, test_id.upper())
            print(f"     {test_id.upper()}: {'✅ Found' if found else '❌ Not found'}")

        print("\nTesting low baseline...")
        result_low = await tools.get_control_baselines('low')
        print(f"✅ Low baseline: {result_low.get('total_controls', 0)} controls")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_baselines())
