const { loadLabHelpers } = require('./helpers');

describe('AST-backed SQL injection validation', () => {
  it('parses valid JavaScript and rejects invalid JavaScript for fallback handling', () => {
    const { parseJavaScript } = loadLabHelpers().helpers;

    expect(parseJavaScript('const answer = 42;')).toMatchObject({ type: 'Program' });
    expect(parseJavaScript('const = ;')).toBeNull();
  });

  it('accepts a parameterized query when local variable names differ from the field names', () => {
    const { validateSqliFix } = loadLabHelpers().helpers;
    const result = validateSqliFix(`
      const suppliedName = request.body.username;
      const suppliedPassword = request.body.password;
      const statement = 'SELECT * FROM users WHERE username = ? AND password = ?';
      db.execute(statement, [suppliedName, suppliedPassword]);
    `, { vulnerable_parameters: ['username', 'password'] });

    expect(result.passed).toBe(true);
  });

  it('rejects a dynamic SQL template even when values are also passed separately', () => {
    const { validateSqliFix } = loadLabHelpers().helpers;
    const result = validateSqliFix(`
      const statement = \`SELECT * FROM users WHERE username = '\${username}'\`;
      db.execute(statement, [username]);
    `, { vulnerable_parameters: ['username'] });

    expect(result.passed).toBe(false);
    expect(result.checks.find((check) => check.label === 'User input is not concatenated into the SQL string').passed).toBe(false);
  });

  it('rejects valid but irrelevant JavaScript', () => {
    const { validateSqliFix } = loadLabHelpers().helpers;
    const result = validateSqliFix('const greeting = "hello";');

    expect(result.passed).toBe(false);
  });
});

describe('AST-backed XSS validation', () => {
  it('recognizes textContent as a safe sink', () => {
    const { analyzers } = loadLabHelpers();
    const result = analyzers.analyzeXssFix(`
      const comment = request.query.comment;
      preview.textContent = comment;
    `);

    expect(result).toEqual({
      plausible: true,
      unsafe: false,
      safe: true,
      encoded: false
    });
  });

  it('recognizes an unencoded innerHTML assignment as unsafe', () => {
    const { analyzers } = loadLabHelpers();
    const result = analyzers.analyzeXssFix('preview.innerHTML = request.query.comment;');

    expect(result.unsafe).toBe(true);
    expect(result.safe).toBe(false);
    expect(result.encoded).toBe(false);
  });

  it('rejects valid but irrelevant JavaScript', () => {
    const { validateXssFix } = loadLabHelpers().helpers;
    const result = validateXssFix('const greeting = "hello";');

    expect(result.passed).toBe(false);
  });
});
