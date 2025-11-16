#!/usr/bin/env python3
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strandkit.tools.s3_advanced import *

def test_all():
    print("="*80)
    print("StrandKit S3 Advanced - Live AWS Testing")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    tests = [
        ("Storage Classes", analyze_s3_storage_classes),
        ("Lifecycle Policies", analyze_s3_lifecycle_policies),
        ("Versioning Waste", find_s3_versioning_waste),
        ("Incomplete Multipart", find_incomplete_multipart_uploads),
        ("Replication", analyze_s3_replication),
        ("Request Costs", analyze_s3_request_costs),
        ("Large Objects", analyze_large_s3_objects)
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
