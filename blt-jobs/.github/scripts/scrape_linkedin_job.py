#!/usr/bin/env python3
"""
LinkedIn Job Scraper
Scrapes job details from LinkedIn job posting URLs
"""

import sys
import re
import json
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def extract_linkedin_job_id(url):
    """Extract job ID from LinkedIn URL"""
    # LinkedIn job URLs typically have the format:
    # https://www.linkedin.com/jobs/view/1234567890
    # https://www.linkedin.com/jobs/view/1234567890/
    match = re.search(r'/jobs/view/(\d+)', url)
    if match:
        return match.group(1)
    return None


def scrape_linkedin_job(url):
    """
    Scrape job details from LinkedIn
    
    Returns a dictionary with job details or None if scraping fails
    """
    try:
        # Set up headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Make request to LinkedIn
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract job details
        job_data = {}
        
        # Try to find job title
        title_elem = soup.find('h1', class_='top-card-layout__title') or \
                     soup.find('h1', class_='topcard__title') or \
                     soup.find('h2', class_='topcard__title')
        if title_elem:
            job_data['title'] = title_elem.get_text(strip=True)
        
        # Try to find company name
        company_elem = soup.find('a', class_='topcard__org-name-link') or \
                       soup.find('span', class_='topcard__flavor') or \
                       soup.find('a', class_='top-card-layout__company-info')
        if company_elem:
            job_data['company'] = company_elem.get_text(strip=True)
        
        # Try to find location
        location_elem = soup.find('span', class_='topcard__flavor topcard__flavor--bullet') or \
                        soup.find('span', class_='top-card-layout__location')
        if location_elem:
            job_data['location'] = location_elem.get_text(strip=True)
        
        # Try to find job type (Full-time, Part-time, etc.)
        job_type_elem = soup.find('span', class_='description__job-criteria-text')
        if job_type_elem:
            job_data['job_type'] = job_type_elem.get_text(strip=True)
        
        # Try to find job description
        description_elem = soup.find('div', class_='description__text') or \
                          soup.find('div', class_='show-more-less-html__markup')
        if description_elem:
            # Clean up the description
            job_data['description'] = description_elem.get_text(separator='\n', strip=True)
        
        # Try to find company website from LinkedIn company page link
        company_link = soup.find('a', class_='topcard__org-name-link')
        if company_link and company_link.get('href'):
            job_data['company_linkedin'] = company_link.get('href')
        
        # If we got at least a title, consider it successful
        if 'title' in job_data:
            return job_data
        
        return None
        
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error parsing job data: {e}", file=sys.stderr)
        return None


def format_job_data_as_issue_body(job_data):
    """Format scraped job data to match the issue template format"""
    output = []
    
    # Add company information
    output.append("## Company Information")
    output.append(f"**Company Name:** {job_data.get('company', 'N/A')}")
    output.append(f"**Website:** {job_data.get('website', job_data.get('company_linkedin', 'N/A'))}")
    output.append("")
    
    # Add job details
    output.append("## Job Details")
    output.append(f"**Job Title:** {job_data.get('title', 'N/A')}")
    output.append(f"**Location:** {job_data.get('location', 'Remote')}")
    output.append(f"**Job Type:** {job_data.get('job_type', 'Full-time')}")
    output.append(f"**Salary Range:** {job_data.get('salary', 'Not specified')}")
    output.append("")
    
    # Add description
    output.append("## Description")
    output.append(job_data.get('description', 'Please see the original job posting for details.'))
    output.append("")
    
    # Add requirements (if available)
    output.append("## Requirements")
    output.append(job_data.get('requirements', 'Please see the original job posting for requirements.'))
    output.append("")
    
    # Add how to apply
    output.append("## How to Apply")
    output.append(job_data.get('how_to_apply', f"Apply via LinkedIn: {job_data.get('original_url', '')}"))
    output.append("")
    
    # Add additional information
    output.append("## Additional Information")
    output.append(job_data.get('additional_info', 'Job scraped from LinkedIn'))
    
    return '\n'.join(output)


def main():
    if len(sys.argv) < 2:
        print("Usage: scrape_linkedin_job.py <linkedin_job_url>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Validate URL
    if 'linkedin.com/jobs' not in url:
        print("Error: Not a valid LinkedIn job URL", file=sys.stderr)
        sys.exit(1)
    
    print(f"Scraping LinkedIn job: {url}", file=sys.stderr)
    
    job_data = scrape_linkedin_job(url)
    
    if job_data:
        job_data['original_url'] = url
        # Output as JSON
        print(json.dumps(job_data, indent=2))
    else:
        print("Error: Failed to scrape job data", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
