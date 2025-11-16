/**
 * Broker data endpoint handlers
 * Serves public broker information - NO PII
 */

export async function handleBrokersRequest(
  request: Request,
  path: string
): Promise<Response> {
  // Extract broker ID if present
  const brokerId = path.split('/api/brokers/')[1];

  if (brokerId) {
    return await getBrokerById(brokerId);
  } else {
    return await getAllBrokers();
  }
}

async function getAllBrokers(): Promise<Response> {
  // In production, this would fetch from:
  // - Cloudflare KV
  // - External API (GitHub raw content)
  // - D1 database
  
  // For now, return sample data
  const brokers = [
    {
      id: 'whitepages',
      name: 'Whitepages',
      description: 'Online directory providing contact information and background data',
      website: 'https://www.whitepages.com',
      optOutUrl: 'https://www.whitepages.com/suppression-requests',
      category: 'People Search',
      dataTypes: ['name', 'address', 'phone', 'age', 'relatives'],
      optOutMethod: {
        type: 'online_form',
        instructions: 'Fill out the opt-out form on their suppression page',
        steps: [
          'Visit the opt-out page',
          'Search for your listing',
          'Click "Remove this listing"',
          'Enter your email for confirmation',
          'Verify via email link',
        ],
      },
      requiredFields: ['firstName', 'lastName', 'state'],
      estimatedResponseDays: 7,
      isActive: true,
    },
    {
      id: 'spokeo',
      name: 'Spokeo',
      description: 'People search engine aggregating public records and social media',
      website: 'https://www.spokeo.com',
      optOutUrl: 'https://www.spokeo.com/optout',
      category: 'People Search',
      dataTypes: ['name', 'address', 'phone', 'email', 'social_media', 'photos'],
      optOutMethod: {
        type: 'online_form',
        instructions: 'Submit opt-out request through their form',
        steps: [
          'Go to opt-out page',
          'Search for your profile',
          'Select listings to remove',
          'Enter email address',
          'Confirm via email',
        ],
      },
      requiredFields: ['firstName', 'lastName', 'state', 'email'],
      estimatedResponseDays: 5,
      isActive: true,
    },
    {
      id: 'beenverified',
      name: 'BeenVerified',
      description: 'Background check and people search service',
      website: 'https://www.beenverified.com',
      optOutUrl: 'https://www.beenverified.com/app/optout/search',
      category: 'Background Check',
      dataTypes: ['name', 'address', 'phone', 'criminal_records', 'property_records'],
      optOutMethod: {
        type: 'online_form',
        instructions: 'Use their opt-out search tool',
        steps: [
          'Visit opt-out page',
          'Enter your information',
          'Find your record',
          'Request removal',
          'Verify email',
        ],
      },
      requiredFields: ['firstName', 'lastName', 'city', 'state', 'email'],
      estimatedResponseDays: 14,
      isActive: true,
    },
    {
      id: 'truthfinder',
      name: 'TruthFinder',
      description: 'Public records search and background check service',
      website: 'https://www.truthfinder.com',
      optOutUrl: 'https://www.truthfinder.com/opt-out/',
      category: 'Background Check',
      dataTypes: ['name', 'address', 'phone', 'criminal_records', 'social_media'],
      optOutMethod: {
        type: 'email',
        templateId: 'truthfinder-optout',
        instructions: 'Email their opt-out team with required information',
        steps: [
          'Find your profile URL',
          'Send email to opt-out address',
          'Include profile URL and personal info',
          'Wait for confirmation',
        ],
      },
      contactEmail: 'optout@truthfinder.com',
      requiredFields: ['firstName', 'lastName', 'address', 'email'],
      estimatedResponseDays: 30,
      isActive: true,
    },
    {
      id: 'intelius',
      name: 'Intelius',
      description: 'People search and background check provider',
      website: 'https://www.intelius.com',
      optOutUrl: 'https://www.intelius.com/opt-out/',
      category: 'People Search',
      dataTypes: ['name', 'address', 'phone', 'relatives', 'property_records'],
      optOutMethod: {
        type: 'online_form',
        instructions: 'Complete the opt-out form',
        steps: [
          'Go to opt-out page',
          'Search for your record',
          'Verify your identity',
          'Submit opt-out request',
          'Receive confirmation',
        ],
      },
      requiredFields: ['firstName', 'lastName', 'age', 'state', 'email'],
      estimatedResponseDays: 10,
      isActive: true,
    },
  ];

  return new Response(JSON.stringify(brokers), {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function getBrokerById(id: string): Promise<Response> {
  // In production, fetch specific broker from storage
  const brokers = await getAllBrokers();
  const brokersData = await brokers.json();
  
  const broker = brokersData.find((b: any) => b.id === id);
  
  if (broker) {
    return new Response(JSON.stringify(broker), {
      headers: { 'Content-Type': 'application/json' },
    });
  } else {
    return new Response(
      JSON.stringify({ error: 'Broker not found' }),
      {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
