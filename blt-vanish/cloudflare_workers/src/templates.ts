/**
 * Opt-out template endpoint
 * Serves template text for generating opt-out requests - NO PII
 */

export async function handleTemplatesRequest(
  request: Request,
  path: string
): Promise<Response> {
  const templateId = path.split('/api/templates/')[1];

  if (!templateId) {
    return new Response(
      JSON.stringify({ error: 'Template ID required' }),
      {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  const template = getTemplate(templateId);

  if (template) {
    return new Response(template, {
      headers: { 'Content-Type': 'text/plain' },
    });
  } else {
    return new Response(
      JSON.stringify({ error: 'Template not found' }),
      {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

function getTemplate(templateId: string): string | null {
  const templates: Record<string, string> = {
    'default-gdpr': `Subject: GDPR Data Deletion Request

Dear [Broker Name],

I am writing to request the immediate deletion of my personal data from your database under Article 17 of the General Data Protection Regulation (GDPR).

Personal Information to be Deleted:
- Full Name: [Full Name]
- Email Address: [Email Address]
- Phone Number: [Phone Number]
- Current Address: [Street Address], [City], [State] [Zip Code]
- Previous Addresses: [Previous Addresses if applicable]

Please confirm:
1. Receipt of this request
2. When my data will be deleted
3. That my data will not be shared with third parties
4. That my data will be removed from all databases and backups

I expect this request to be completed within 30 days as required by GDPR.

Thank you,
[Full Name]
[Date]`,

    'default-ccpa': `Subject: CCPA Data Deletion Request

Dear [Broker Name],

Pursuant to the California Consumer Privacy Act (CCPA), I am requesting that you delete all of my personal information that you have collected and stored.

Personal Information to be Deleted:
- Full Name: [Full Name]
- Email Address: [Email Address]
- Phone Number: [Phone Number]
- Address: [Street Address], [City], [State] [Zip Code]

Under CCPA Section 1798.105, I have the right to request deletion of my personal information. Please confirm:
1. Receipt of this deletion request
2. Timeline for completion
3. That my data will not be sold or shared

I request that you respond to this request within 45 days as required by law.

Sincerely,
[Full Name]
[Date]`,

    'truthfinder-optout': `Subject: Opt-Out Request

Dear TruthFinder Opt-Out Team,

I am requesting that my personal information be removed from TruthFinder.com.

My Information:
- Full Name: [Full Name]
- Current Address: [Street Address], [City], [State] [Zip Code]
- Email: [Email Address]
- Profile URL: [Profile URL found on TruthFinder]

Please remove all records associated with my name and address, and confirm when this has been completed.

Thank you,
[Full Name]`,

    'email-generic': `Subject: Request to Remove Personal Information

Dear [Broker Name],

I am writing to request the removal of my personal information from your database.

Personal Information:
- Name: [Full Name]
- Email: [Email Address]
- Phone: [Phone Number]
- Address: [Street Address], [City], [State] [Zip Code]

Under applicable privacy laws (GDPR, CCPA, etc.), I request that you:
1. Delete all my personal information from your records
2. Do not sell or share my information
3. Confirm completion of this request
4. Provide a reference number for this request

Please process this request within 30 days and send confirmation to [Email Address].

Regards,
[Full Name]
[Date]`,

    'phone-script': `Hello, I'm calling to request removal of my personal information from your database.

My name is [Full Name], and I'd like to opt out of your services.

The information I'd like removed includes:
- My name: [Full Name]
- My address: [Address]
- My phone number: [Phone Number]
- My email: [Email Address]

Can you please confirm:
1. You've received my opt-out request
2. How long it will take to process
3. A reference number for my request

Thank you for your assistance.`,

    'mail-letter': `[Your Name]
[Your Address]
[City, State ZIP]
[Email Address]
[Phone Number]

[Date]

[Broker Name]
[Broker Address]
[City, State ZIP]

Re: Request to Remove Personal Information

Dear Sir or Madam,

I am writing to formally request the removal of all my personal information from your database and any affiliated services.

Personal Information to be Removed:
- Full Name: [Full Name]
- Date of Birth: [DOB if required]
- Current Address: [Street Address], [City], [State] [Zip Code]
- Previous Addresses: [List if applicable]
- Email Address: [Email Address]
- Phone Number: [Phone Number]

Under the Fair Credit Reporting Act and applicable state privacy laws, I request that you:

1. Delete all personal information associated with my name and addresses
2. Cease any further collection of my information
3. Do not sell or share my information with third parties
4. Provide written confirmation of deletion to the address above

Please confirm receipt of this request and provide a timeline for completion.

Sincerely,

[Signature]
[Printed Name]`,
  };

  return templates[templateId] || null;
}
