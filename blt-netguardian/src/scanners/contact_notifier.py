"""
Contact notification module for BLT-NetGuardian.
Automatically contacts stakeholders when vulnerabilities are found.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class ContactNotifier:
    """Handles automatic contact and notification for discovered vulnerabilities."""
    
    def __init__(self):
        self.name = "Contact Notifier"
        self.version = "1.0.0"
        self.notification_methods = [
            'email',
            'whois_contact',
            'security_txt',
            'github_security_advisory',
            'twitter_dm',
            'responsible_disclosure'
        ]
    
    async def notify_vulnerability(self, target: str, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Notify target stakeholders about discovered vulnerabilities.
        
        Args:
            target: The target (domain, repo, contract)
            vulnerabilities: List of vulnerabilities found
        
        Returns:
            Notification result with contact attempts
        """
        # Find contact information
        contacts = await self.find_contacts(target)
        
        if not contacts:
            return {
                'success': False,
                'message': 'No contact information found',
                'attempts': []
            }
        
        # Prepare vulnerability report
        report = self.prepare_vulnerability_report(target, vulnerabilities)
        
        # Attempt contact through available channels
        attempts = []
        
        for contact_method, contact_info in contacts.items():
            attempt = await self.send_notification(
                method=contact_method,
                contact_info=contact_info,
                report=report
            )
            attempts.append(attempt)
        
        # Record contact attempt
        contact_log = {
            'target': target,
            'vulnerability_count': len(vulnerabilities),
            'contact_attempts': len(attempts),
            'successful_contacts': len([a for a in attempts if a.get('success')]),
            'timestamp': datetime.utcnow().isoformat(),
            'attempts': attempts
        }
        
        return contact_log
    
    async def find_contacts(self, target: str) -> Dict[str, Any]:
        """
        Find contact information for a target.
        
        Methods:
        1. Check for security.txt (RFC 9116)
        2. WHOIS lookup for domain contacts
        3. GitHub security email for repositories
        4. Look for security@ or abuse@ emails
        5. Check social media profiles
        """
        contacts = {}
        
        # Security.txt check
        security_txt = await self.check_security_txt(target)
        if security_txt:
            contacts['security_txt'] = security_txt
        
        # WHOIS lookup
        whois_info = await self.whois_lookup(target)
        if whois_info and whois_info.get('email'):
            contacts['whois'] = whois_info
        
        # GitHub specific
        if 'github.com' in target:
            github_contact = await self.get_github_security_contact(target)
            if github_contact:
                contacts['github'] = github_contact
        
        # Default security emails
        domain = self.extract_domain(target)
        if domain:
            contacts['default_emails'] = {
                'security': f'security@{domain}',
                'abuse': f'abuse@{domain}',
                'admin': f'admin@{domain}'
            }
        
        return contacts
    
    async def check_security_txt(self, target: str) -> Optional[Dict[str, Any]]:
        """
        Check for security.txt file (RFC 9116).
        
        In production, fetch:
        - https://example.com/.well-known/security.txt
        - https://example.com/security.txt
        """
        # Demo: Return sample security.txt
        return {
            'contact': 'security@example.com',
            'expires': '2025-12-31T23:59:59Z',
            'preferred_languages': ['en'],
            'canonical': 'https://example.com/.well-known/security.txt'
        }
    
    async def whois_lookup(self, target: str) -> Optional[Dict[str, Any]]:
        """
        Perform WHOIS lookup for contact information.
        
        In production, query WHOIS servers for:
        - Registrant email
        - Administrative contact
        - Technical contact
        """
        # Demo: Return sample WHOIS data
        domain = self.extract_domain(target)
        if domain:
            return {
                'email': f'admin@{domain}',
                'registrar': 'Example Registrar',
                'creation_date': '2020-01-01',
                'expiration_date': '2025-01-01'
            }
        return None
    
    async def get_github_security_contact(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """
        Get GitHub repository security contact.
        
        In production, check:
        - SECURITY.md file
        - GitHub Security Advisories email
        - Repository owner email
        """
        # Demo: Return sample GitHub contact
        return {
            'type': 'github_security',
            'repo': repo_url,
            'contact_url': f'{repo_url}/security/advisories/new',
            'has_security_policy': True
        }
    
    def prepare_vulnerability_report(self, target: str, vulnerabilities: List[Dict[str, Any]]) -> str:
        """
        Prepare a professional vulnerability disclosure report.
        
        Follows responsible disclosure guidelines.
        """
        report_lines = [
            "Subject: Security Vulnerability Disclosure",
            "",
            f"Dear {target} Security Team,",
            "",
            "Our autonomous security scanner (BLT-NetGuardian) has identified potential",
            f"security vulnerabilities in {target}. We are reporting these findings in",
            "accordance with responsible disclosure practices.",
            "",
            "VULNERABILITY SUMMARY:",
            f"- Total vulnerabilities found: {len(vulnerabilities)}",
            f"- Critical: {len([v for v in vulnerabilities if v.get('severity') == 'critical'])}",
            f"- High: {len([v for v in vulnerabilities if v.get('severity') == 'high'])}",
            f"- Medium: {len([v for v in vulnerabilities if v.get('severity') == 'medium'])}",
            "",
            "DETAILED FINDINGS:",
            ""
        ]
        
        for i, vuln in enumerate(vulnerabilities, 1):
            report_lines.extend([
                f"{i}. {vuln.get('title', 'Unnamed vulnerability')}",
                f"   Severity: {vuln.get('severity', 'Unknown').upper()}",
                f"   Type: {vuln.get('type', 'Unknown')}",
                f"   Component: {vuln.get('affected_component', 'N/A')}",
                ""
            ])
            
            if vuln.get('description'):
                report_lines.append(f"   Description: {vuln['description']}")
                report_lines.append("")
            
            if vuln.get('remediation'):
                report_lines.append(f"   Remediation: {vuln['remediation']}")
                report_lines.append("")
        
        report_lines.extend([
            "",
            "RESPONSE TIMELINE:",
            "We follow a 90-day disclosure timeline. We request acknowledgment within 7 days",
            "and appreciate regular updates on remediation progress.",
            "",
            "CONTACT:",
            "For questions or to provide updates, please respond to this email or contact:",
            "security@blt-netguardian.io",
            "",
            "Thank you for your attention to these security matters.",
            "",
            "Best regards,",
            "BLT-NetGuardian Autonomous Security Team",
            f"Report ID: {datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            f"Scan Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        ])
        
        return "\n".join(report_lines)
    
    async def send_notification(self, method: str, contact_info: Any, report: str) -> Dict[str, Any]:
        """
        Send notification through specified method.
        
        In production, actually sends:
        - Email via SMTP/SendGrid
        - GitHub Security Advisory
        - Twitter DM
        - Etc.
        """
        # Demo: Simulate sending notification
        return {
            'method': method,
            'contact_info': contact_info,
            'success': True,
            'sent_at': datetime.utcnow().isoformat(),
            'message': f'Notification sent via {method}'
        }
    
    def extract_domain(self, target: str) -> Optional[str]:
        """Extract domain from target string."""
        target = target.replace('https://', '').replace('http://', '')
        target = target.split('/')[0]
        
        # Handle GitHub repos
        if 'github.com' in target:
            parts = target.split('/')
            if len(parts) >= 3:
                return parts[1] + '.github.io'  # User's GitHub pages domain
        
        return target if '.' in target else None
    
    async def get_contact_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent contact attempts."""
        # In production, query from KV store
        # Demo: Return sample log
        return [
            {
                'target': 'oldcompany.com',
                'vulnerability_count': 7,
                'contact_attempts': 3,
                'successful_contacts': 2,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'contacted'
            }
        ]
