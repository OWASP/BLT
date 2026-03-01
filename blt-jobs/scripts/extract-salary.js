#!/usr/bin/env node

/**
 * Salary extraction utility for job descriptions
 * Extracts and normalizes salary information from job description text
 */

/**
 * Extract salary information from text
 * @param {string} text - Job description text
 * @returns {string|null} - Normalized salary range or null
 */
function extractSalary(text) {
  if (!text) return null;

  // Common salary patterns
  const patterns = [
    // $100,000 - $150,000 or $100k - $150k
    /\$\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s*[-–—]\s*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s*(USD|CAD|EUR|GBP|per year|\/year|annually)?/gi,
    
    // $100,000 to $150,000
    /\$\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s+to\s+\$?\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s*(USD|CAD|EUR|GBP|per year|\/year|annually)?/gi,
    
    // Annual Salary: $100,000 — $150,000
    /(?:annual|base|total)?\s*(?:salary|compensation|pay):\s*\$\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s*[-–—]\s*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s*(USD|CAD|EUR|GBP)?/gi,
    
    // Hiring Ranges: $100,000 — $150,000
    /hiring\s+ranges?:\s*[^\$]*\$\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s*[-–—]\s*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s*(USD|CAD|EUR|GBP)?/gi,
    
    // £50,000 - £70,000 or €60,000 - €80,000
    /([£€])\s*(\d{1,3}(?:,\d{3})*|\d+)k?\s*[-–—]\s*\1?\s*(\d{1,3}(?:,\d{3})*|\d+)k?/gi,
  ];

  const matches = [];
  
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      matches.push(match);
    }
  }

  if (matches.length === 0) return null;

  // Process the first match (usually the most relevant)
  const match = matches[0];
  
  let min, max, currency;
  
  if (match[0].includes('£')) {
    currency = 'GBP';
    min = match[2];
    max = match[3];
  } else if (match[0].includes('€')) {
    currency = 'EUR';
    min = match[2];
    max = match[3];
  } else {
    min = match[1];
    max = match[2];
    currency = match[3] || 'USD';
  }

  // Normalize currency
  currency = currency.toUpperCase().replace(/[^A-Z]/g, '');
  if (!['USD', 'CAD', 'EUR', 'GBP'].includes(currency)) {
    currency = 'USD';
  }

  // Normalize numbers (handle k notation)
  const normalizeNumber = (num) => {
    num = num.replace(/,/g, '');
    if (match[0].toLowerCase().includes('k') && parseInt(num) < 1000) {
      return parseInt(num) * 1000;
    }
    return parseInt(num);
  };

  const minSalary = normalizeNumber(min);
  const maxSalary = normalizeNumber(max);

  // Format with commas
  const formatNumber = (num) => num.toLocaleString('en-US');

  const currencySymbol = {
    'USD': '$',
    'CAD': 'CAD $',
    'EUR': '€',
    'GBP': '£'
  }[currency] || '$';

  return `${currencySymbol}${formatNumber(minSalary)} - ${currencySymbol}${formatNumber(maxSalary)}`;
}

module.exports = { extractSalary };

// CLI usage
if (require.main === module) {
  const text = process.argv[2];
  if (!text) {
    console.error('Usage: node extract-salary.js "<job description text>"');
    process.exit(1);
  }
  const salary = extractSalary(text);
  console.log(salary || 'No salary found');
}
