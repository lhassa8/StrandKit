#!/usr/bin/env python3
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strandkit.tools.ec2_advanced import *

def test_all():
    print("="*80)
    print("StrandKit EC2 Advanced - Live AWS Testing")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    tests = [
        ("Auto Scaling Groups", lambda: analyze_auto_scaling_groups()),
        ("Load Balancers", lambda: analyze_load_balancers()),
        ("Spot Recommendations", lambda: get_ec2_spot_recommendations())
    ]

    results = []
    for name, func in tests:
        print(f"\n{'='*80}\nTest: {name}\n{'='*80}")
        try:
            result = func()
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                results.append(False)
            else:
                print(f"✅ {name} Complete")
                if 'summary' in result:
                    for k, v in result['summary'].items():
                        print(f"  {k}: {v}")
                results.append(True)
        except Exception as e:
            print(f"❌ Exception: {e}")
            results.append(False)

    print(f"\n{'='*80}\nTesting Complete\n{'='*80}")
    print(f"✅ Success: {sum(results)}/{len(results)} tools working")
    return all(results)

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
