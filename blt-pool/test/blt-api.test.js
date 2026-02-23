'use strict';

jest.mock('axios');

const axios = require('axios');
const { reportBugToBLT, fetchBugsFromBLT, searchBugsInBLT } = require('../src/blt-api');

describe('reportBugToBLT', () => {
  beforeEach(() => jest.clearAllMocks());

  test('returns bug data on success', async () => {
    axios.post.mockResolvedValue({
      data: { success: true, data: { id: 10, url: 'https://example.com' } },
    });

    const result = await reportBugToBLT({
      url: 'https://example.com',
      description: 'Test bug',
      githubUrl: 'https://github.com/org/repo/issues/1',
      label: 'bug',
    });

    expect(result).toEqual({ id: 10, url: 'https://example.com' });
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/bugs'),
      expect.objectContaining({ description: 'Test bug' }),
      expect.any(Object)
    );
  });

  test('returns null when API returns success=false', async () => {
    axios.post.mockResolvedValue({ data: { success: false } });
    const result = await reportBugToBLT({ url: 'https://example.com', description: 'test' });
    expect(result).toBeNull();
  });

  test('returns null on network error', async () => {
    axios.post.mockRejectedValue(new Error('Network error'));
    const result = await reportBugToBLT({ url: 'https://example.com', description: 'test' });
    expect(result).toBeNull();
  });

  test('uses githubUrl as url when url is not provided', async () => {
    axios.post.mockResolvedValue({ data: { success: true, data: { id: 5 } } });
    await reportBugToBLT({ githubUrl: 'https://github.com/org/repo/issues/1', description: 'test' });
    expect(axios.post).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ url: 'https://github.com/org/repo/issues/1' }),
      expect.any(Object)
    );
  });
});

describe('fetchBugsFromBLT', () => {
  beforeEach(() => jest.clearAllMocks());

  test('returns bugs array on success', async () => {
    const bugs = [{ id: 1 }, { id: 2 }];
    axios.get.mockResolvedValue({ data: { success: true, data: bugs } });
    const result = await fetchBugsFromBLT({ page: 1, perPage: 10 });
    expect(result).toEqual(bugs);
  });

  test('returns empty array on failure', async () => {
    axios.get.mockRejectedValue(new Error('Network error'));
    const result = await fetchBugsFromBLT();
    expect(result).toEqual([]);
  });

  test('passes status and domain filters', async () => {
    axios.get.mockResolvedValue({ data: { success: true, data: [] } });
    await fetchBugsFromBLT({ status: 'open', domain: 1 });
    expect(axios.get).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ params: expect.objectContaining({ status: 'open', domain: 1 }) })
    );
  });
});

describe('searchBugsInBLT', () => {
  beforeEach(() => jest.clearAllMocks());

  test('returns search results on success', async () => {
    const bugs = [{ id: 3 }];
    axios.get.mockResolvedValue({ data: { success: true, data: bugs } });
    const result = await searchBugsInBLT('sql injection');
    expect(result).toEqual(bugs);
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('/bugs/search'),
      expect.objectContaining({ params: expect.objectContaining({ q: 'sql injection' }) })
    );
  });

  test('returns empty array on error', async () => {
    axios.get.mockRejectedValue(new Error('Network error'));
    const result = await searchBugsInBLT('test');
    expect(result).toEqual([]);
  });
});
