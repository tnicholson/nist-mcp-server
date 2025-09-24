#!/usr/bin/env python3
"""
URL Validation Script for NIST MCP Server

Validates all URLs in the download script to ensure they're accessible.
"""

import urllib.request
import urllib.error
import json
import sys
from pathlib import Path

# Import the data sources from the download script
sys.path.append(str(Path(__file__).parent))
from download_nist_data import NISTDataDownloader


def validate_url(url, description):
    """Validate a single URL"""
    try:
        print(f"🔍 Testing: {description}")
        print(f"   URL: {url}")
        
        # Create request with proper headers
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'NIST-MCP-Server/1.0 (URL Validation Script)'
            }
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            status_code = response.getcode()
            content_type = response.headers.get('Content-Type', '')
            content_length = response.headers.get('Content-Length', 'Unknown')
            
            if status_code == 200:
                # Read a small sample to verify content
                sample = response.read(1024).decode('utf-8', errors='ignore')
                
                # Basic content validation
                is_json = url.endswith('.json') and (sample.strip().startswith('{') or sample.strip().startswith('['))
                is_xml = url.endswith('.xml') and sample.strip().startswith('<?xml')
                
                if url.endswith('.json') and not is_json:
                    print(f"   ⚠️  WARNING: Expected JSON but content doesn't look like JSON")
                elif url.endswith('.xml') and not is_xml:
                    print(f"   ⚠️  WARNING: Expected XML but content doesn't look like XML")
                
                print(f"   ✅ SUCCESS: HTTP {status_code}")
                print(f"   📄 Content-Type: {content_type}")
                print(f"   📏 Content-Length: {content_length}")
                print(f"   📝 Sample: {sample[:100]}...")
                return True
            else:
                print(f"   ❌ FAILED: HTTP {status_code}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP ERROR: {e.code} - {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"   ❌ URL ERROR: {e.reason}")
        return False
    except Exception as e:
        print(f"   ❌ UNEXPECTED ERROR: {e}")
        return False
    finally:
        print()


def main():
    """Main validation function"""
    print("🚀 NIST MCP Server URL Validation")
    print("=" * 50)
    print()
    
    downloader = NISTDataDownloader(Path("/tmp"))
    
    total_urls = len(downloader.DATA_SOURCES)
    successful = 0
    failed = 0
    
    for source_id, source_info in downloader.DATA_SOURCES.items():
        url = source_info["url"]
        description = source_info["description"]
        
        if validate_url(url, description):
            successful += 1
        else:
            failed += 1
    
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Total URLs tested: {total_urls}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success rate: {(successful/total_urls)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All URLs are valid and accessible!")
        return True
    else:
        print(f"\n⚠️  {failed} URLs failed validation. Please check the failed URLs.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)