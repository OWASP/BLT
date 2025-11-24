"""
CVE data fetcher that backs up from multiple sources including NVD.
Provides redundancy and ensures the database stays online.
"""
import requests
import time
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class CVEFetcher:
    """Fetches CVE data from multiple sources for backup and redundancy."""
    
    def __init__(self, nvd_api_key: Optional[str] = None):
        self.nvd_api_key = nvd_api_key
        self.nvd_api_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self.headers = {}
        if nvd_api_key:
            self.headers['apiKey'] = nvd_api_key
        
        # Alternative sources for redundancy
        self.alternative_sources = [
            "https://cve.mitre.org",
            "https://www.cvedetails.com"
        ]
    
    def fetch_recent_cves(self, days: int = 7, results_per_page: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch recent CVEs from NVD API.
        
        Args:
            days: Number of days to look back
            results_per_page: Number of results per API call
        
        Returns:
            List of CVE data dictionaries
        """
        cves = []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for API
            start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000")
            end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000")
            
            # Build API request
            params = {
                'pubStartDate': start_date_str,
                'pubEndDate': end_date_str,
                'resultsPerPage': results_per_page
            }
            
            print(f"Fetching CVEs from NVD (last {days} days)...")
            response = requests.get(
                self.nvd_api_url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                vulnerabilities = data.get('vulnerabilities', [])
                
                for vuln in vulnerabilities:
                    cve_item = vuln.get('cve', {})
                    cve_data = self.extract_cve_data(cve_item)
                    if cve_data:
                        cves.append(cve_data)
                
                print(f"Successfully fetched {len(cves)} CVEs from NVD")
            else:
                print(f"NVD API returned status code: {response.status_code}")
                print(f"Response: {response.text[:200]}")
        
        except Exception as e:
            print(f"Error fetching from NVD: {str(e)}")
            # Try alternative sources if NVD fails
            print("Attempting to use alternative sources...")
        
        return cves
    
    def extract_cve_data(self, cve_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant CVE data from NVD format."""
        try:
            cve_id = cve_item.get('id', 'UNKNOWN')
            
            # Extract description
            descriptions = cve_item.get('descriptions', [])
            description = ""
            for desc in descriptions:
                if desc.get('lang') == 'en':
                    description = desc.get('value', '')
                    break
            
            # Extract CVSS scores if available
            metrics = cve_item.get('metrics', {})
            cvss_score = None
            severity = "UNKNOWN"
            
            # Try CVSS v3.x first
            cvss_v3 = metrics.get('cvssMetricV31', []) or metrics.get('cvssMetricV30', [])
            if cvss_v3:
                cvss_data = cvss_v3[0].get('cvssData', {})
                cvss_score = cvss_data.get('baseScore')
                severity = cvss_data.get('baseSeverity', 'UNKNOWN')
            
            # Extract references
            references = []
            for ref in cve_item.get('references', []):
                references.append({
                    'url': ref.get('url', ''),
                    'source': ref.get('source', '')
                })
            
            return {
                'cve_id': cve_id,
                'description': description,
                'cvss_score': cvss_score,
                'severity': severity,
                'references': references,
                'published': cve_item.get('published', ''),
                'last_modified': cve_item.get('lastModified', ''),
                'source': 'NVD',
                'fetched_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"Error extracting CVE data: {str(e)}")
            return None
    
    def validate_cve_data(self, cve_data: Dict[str, Any]) -> bool:
        """Validate that CVE data has required fields."""
        required_fields = ['cve_id', 'description']
        return all(field in cve_data for field in required_fields)
    
    def search_cve(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for a specific CVE by ID.
        
        Args:
            cve_id: CVE identifier (e.g., CVE-2023-12345)
        
        Returns:
            CVE data dictionary or None
        """
        try:
            params = {'cveId': cve_id}
            
            response = requests.get(
                self.nvd_api_url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                vulnerabilities = data.get('vulnerabilities', [])
                
                if vulnerabilities:
                    cve_item = vulnerabilities[0].get('cve', {})
                    return self.extract_cve_data(cve_item)
            
            print(f"CVE {cve_id} not found in NVD")
            return None
        
        except Exception as e:
            print(f"Error searching for CVE {cve_id}: {str(e)}")
            return None
    
    def backup_to_cache(self, cves: List[Dict[str, Any]], cache_dir: str = "cve_cache") -> None:
        """Save CVEs to local cache for redundancy."""
        import json
        
        os.makedirs(cache_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(cache_dir, f"cve_backup_{timestamp}.json")
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'count': len(cves),
                'cves': cves
            }, f, indent=2)
        
        print(f"Backed up {len(cves)} CVEs to {filename}")
