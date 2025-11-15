# Adding Data Brokers to SelfErase

Thank you for helping expand the SelfErase broker database! This guide will help you add new data brokers to the system.

## Before You Start

1. **Verify the broker** has a legitimate opt-out process
2. **Test the opt-out process** yourself if possible
3. **Document all required information**
4. **Check for existing entries** to avoid duplicates

## Broker Information Required

### Essential Information
- ✅ Broker name (official company name)
- ✅ Description (what they do)
- ✅ Website URL
- ✅ Opt-out URL (if available online)
- ✅ Category (People Search, Background Check, etc.)
- ✅ Data types collected
- ✅ Opt-out method (form, email, mail, phone)
- ✅ Required fields for opt-out

### Optional Information
- Contact email
- Contact phone number
- Mailing address
- Estimated response time
- Special notes or instructions

## Step-by-Step Guide

### 1. Create a Broker JSON File

Create a new file in `data/brokers/` with a descriptive name:
```
data/brokers/[broker-name].json
```

For example: `data/brokers/infotracer.json`

### 2. Fill Out Broker Information

Use this template:

```json
{
  "id": "broker-name",
  "name": "Broker Display Name",
  "description": "Brief description of what the broker does",
  "website": "https://www.broker.com",
  "optOutUrl": "https://www.broker.com/opt-out",
  "category": "People Search",
  "dataTypes": [
    "name",
    "address",
    "phone",
    "email"
  ],
  "optOutMethod": {
    "type": "online_form",
    "instructions": "Brief description of the opt-out process",
    "steps": [
      "Step 1: Visit the opt-out page",
      "Step 2: Enter your information",
      "Step 3: Submit the form",
      "Step 4: Verify via email"
    ]
  },
  "requiredFields": [
    "firstName",
    "lastName",
    "email",
    "state"
  ],
  "estimatedResponseDays": 7,
  "notes": "Any special notes about this broker",
  "isActive": true
}
```

### 3. Field Descriptions

#### `id` (required)
- Unique identifier
- Lowercase, hyphenated
- Example: `"whitepages"`, `"been-verified"`

#### `name` (required)
- Official company name
- Proper capitalization
- Example: `"Whitepages"`, `"BeenVerified"`

#### `description` (required)
- 1-2 sentence description
- What service they provide
- Example: `"People search engine aggregating public records"`

#### `website` (required)
- Main company website
- Full URL with https://
- Example: `"https://www.whitepages.com"`

#### `optOutUrl` (optional but recommended)
- Direct link to opt-out page
- If no online opt-out, omit this field
- Example: `"https://www.whitepages.com/opt-out"`

#### `category` (required)
Choose one:
- `"People Search"`
- `"Data Broker"`
- `"Background Check"`
- `"Public Records"`
- `"Social Media"`
- `"Marketing"`
- `"Other"`

#### `dataTypes` (required)
List all data types collected (choose from):
- `"name"`
- `"address"`
- `"phone"`
- `"email"`
- `"age"`
- `"dob"`
- `"ssn"`
- `"relatives"`
- `"neighbors"`
- `"property_records"`
- `"criminal_records"`
- `"financial_records"`
- `"employment"`
- `"education"`
- `"social_media"`
- `"photos"`
- `"vehicle_records"`
- `"other"`

#### `optOutMethod` (required)

**type** - Choose one:
- `"online_form"` - Web form submission
- `"email"` - Email request
- `"mail"` - Physical mail
- `"phone"` - Phone call
- `"multiple"` - More than one method

**instructions** - Brief summary of the process

**templateId** (optional) - ID of template to use

**steps** - Array of step-by-step instructions

#### `contactEmail` (optional)
Email address for opt-out requests

#### `contactPhone` (optional)
Phone number for opt-out requests

#### `mailingAddress` (optional)
Physical mailing address for written requests

#### `requiredFields` (required)
Fields needed for opt-out (choose from):
- `"firstName"`
- `"middleName"`
- `"lastName"`
- `"email"`
- `"phone"`
- `"address"`
- `"city"`
- `"state"`
- `"zipCode"`
- `"dob"`
- `"age"`
- `"profileUrl"`

#### `estimatedResponseDays` (optional)
- Number of days for typical response
- Based on testing or broker policy
- Example: `7`, `30`, `90`

#### `notes` (optional)
- Any special instructions
- Known issues or quirks
- Tips for successful opt-out

#### `isActive` (required)
- `true` - Broker is active and tracked
- `false` - Broker is defunct or inactive

### 4. Add to Master List

Add your broker to `data/brokers/brokers.json`:

```json
[
  {
    "id": "existing-broker",
    ...
  },
  {
    "id": "your-new-broker",
    ...
  }
]
```

### 5. Validate Your JSON

Use a JSON validator:
```bash
# Check syntax
cat data/brokers/your-broker.json | python -m json.tool

# Validate against schema
# (requires ajv-cli: npm install -g ajv-cli)
ajv validate -s data/schema.json -d data/brokers/your-broker.json
```

### 6. Test the Entry

If you can run the app locally:
1. Search for your broker
2. Verify all information displays correctly
3. Check that steps are clear and accurate

### 7. Submit a Pull Request

1. Fork the repository
2. Create a branch: `git checkout -b add-broker-[name]`
3. Commit your changes: `git commit -m "Add [Broker Name] to database"`
4. Push: `git push origin add-broker-[name]`
5. Create a Pull Request on GitHub

## Pull Request Template

```markdown
## Adding New Broker: [Broker Name]

### Checklist
- [ ] Tested the opt-out process myself
- [ ] Validated JSON syntax
- [ ] Added to brokers.json
- [ ] Included all required fields
- [ ] Verified information is current
- [ ] No duplicate entry exists

### Additional Information
- Broker website: [URL]
- Opt-out tested: Yes/No
- Response time observed: [X days]
- Special notes: [Any notes]
```

## Tips for Good Broker Entries

### ✅ Do
- Test the opt-out process yourself
- Provide clear, step-by-step instructions
- Include estimated response times from experience
- Note any special requirements or quirks
- Keep information current and accurate

### ❌ Don't
- Copy information you haven't verified
- Include personal opinions or bias
- Add defunct or inactive brokers
- Duplicate existing entries
- Include affiliate links

## Common Opt-Out Methods

### Online Form
Most common. User visits website and fills out form.

Example steps:
1. Visit opt-out page
2. Search for your listing
3. Select record to remove
4. Enter verification email
5. Confirm via email link

### Email
User sends formatted email to broker.

Required info:
- Email address
- Often need profile URL
- Template helpful

### Phone
User calls broker directly.

Required info:
- Phone number
- Script/talking points helpful
- Business hours

### Mail
User sends physical letter.

Required info:
- Mailing address
- Specific format requirements
- Return address for confirmation

## Quality Standards

Good broker entries have:
- ✅ Accurate, current information
- ✅ Clear, tested instructions
- ✅ Helpful notes and tips
- ✅ Realistic time estimates
- ✅ All required fields documented

## Getting Help

Need help adding a broker?
- Open a [Discussion](https://github.com/OWASP-BLT/SelfErase/discussions)
- Ask in the Pull Request
- Check existing brokers for examples

## Thank You!

Every broker you add helps people take back control of their privacy. Your contribution makes a real difference!
